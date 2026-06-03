from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.judge.api_runner import run_api_case
from app.judge.dynamic_runner import run_shell_case
from app.judge.security_checks import scan_script_code, scan_shell_code
from app.models import Question, Submission
from app.schemas import EvaluateRequest, EvaluationCaseResultRead, EvaluationResponse, StaticIssue


def _outputs_match(actual: str | None, expected: str | None) -> bool:
    actual_normalized = (actual or "").replace("\r\n", "\n")
    expected_normalized = (expected or "").replace("\r\n", "\n")
    return actual_normalized == expected_normalized or actual_normalized.rstrip("\n") == expected_normalized.rstrip("\n")


def evaluate_submission(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    """评测一次提交。

    这是整个评测流程的总入口。
    它会先看题目类型，再决定走哪条评测分支：
    - `api` 题走 Python 函数执行逻辑
    - 其他题走 shell / script 判题逻辑
    """

    if not question.test_cases:
        raise HTTPException(status_code=422, detail=f"Question {question.id} has no test cases configured")
    if question.question_type == "api" or question.language == "python":
        return _evaluate_api(db, question, payload)
    return _evaluate_shell(db, question, payload)


def _evaluate_shell(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    """评测 shell / script 类型题目。

    流程分两步：
    1. 先做静态安全检查，避免危险内容进入后续流程
    2. 再根据题目 ID 找到专门的判题函数进行校验
    """

    static_issues = (
        scan_script_code(payload.submitted_code, _expected_outputs_for_static_scan(question))
        if question.question_type == "script"
        else scan_shell_code(payload.submitted_code, question.allowed_commands)
    )
    if static_issues:
        case_results = []
        for case in question.test_cases:
            case_results.append(
                EvaluationCaseResultRead(
                    case_id=case.case_id,
                    description=case.description,
                    passed=False,
                    score=0.0,
                    actual_output=None,
                    expected_output=case.expected_output,
                    error="; ".join(issue.message for issue in static_issues),
                    execution_time_ms=0.0,
                )
            )
        return _persist_response(
            db,
            question,
            payload,
            0.0,
            0,
            len(question.test_cases),
            "代码安全检查未通过。",
            static_issues,
            case_results,
        )
    case_results: list[EvaluationCaseResultRead] = []
    passed_count = 0
    total_weight = 0.0
    obtained = 0.0
    for case in question.test_cases:
        outcome = run_shell_case(question, case, payload.submitted_code)
        passed = outcome.passed
        if passed:
            passed_count += 1
            obtained += case.score_weight
        total_weight += case.score_weight
        case_results.append(
            EvaluationCaseResultRead(
                case_id=case.case_id,
                description=case.description,
                passed=passed,
                score=100.0 * case.score_weight if passed else 0.0,
                actual_output=outcome.actual_output,
                expected_output=outcome.expected_output,
                error=outcome.error,
                execution_time_ms=outcome.execution_time_ms,
            )
        )
    overall_score = round((obtained / total_weight) * 100, 2) if total_weight else 0.0
    comment = "答案通过。" if passed_count == len(question.test_cases) else f"通过 {passed_count}/{len(question.test_cases)} 个测试用例。"
    return _persist_response(db, question, payload, overall_score, passed_count, len(question.test_cases), comment, [], case_results)


def _expected_outputs_for_static_scan(question: Question) -> list[str]:
    outputs = [case.expected_output for case in question.test_cases if case.expected_output]
    metadata_expected = (question.metadata_json or {}).get("expected_output")
    if metadata_expected:
        outputs.append(metadata_expected)
    return outputs


def _evaluate_api(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    """评测 API 类型题目。

    这类题目的答案通常是一段 Python 函数实现，
    所以这里会把用户代码真正执行起来，
    然后拿每个测试用例去调用入口函数并比对返回值。
    """

    case_results: list[EvaluationCaseResultRead] = []
    passed_count = 0
    total_weight = 0.0
    obtained = 0.0
    for case in question.test_cases:
        result = run_api_case(question, case, payload.submitted_code)
        expected = case.expected_output
        # API 题当前采用“函数返回值转成字符串后比较”的方式判断是否通过。
        passed = result.error is None and _outputs_match(result.actual_output, expected)
        if passed:
            passed_count += 1
            obtained += case.score_weight
        total_weight += case.score_weight
        case_results.append(
            EvaluationCaseResultRead(
                case_id=case.case_id,
                description=case.description,
                passed=passed,
                score=100.0 * case.score_weight if passed else 0.0,
                actual_output=result.actual_output,
                expected_output=expected,
                error=result.error,
                execution_time_ms=result.execution_time_ms,
            )
        )
    overall_score = round((obtained / total_weight) * 100, 2) if total_weight else 0.0
    return _persist_response(
        db, question, payload, overall_score, passed_count, len(question.test_cases), f"通过 {passed_count}/{len(question.test_cases)} 个测试用例。", [], case_results
    )


def _persist_response(
    db: Session,
    question: Question,
    payload: EvaluateRequest,
    overall_score: float,
    passed_count: int,
    total_count: int,
    overall_comment: str,
    static_issues: list[StaticIssue],
    case_results: list[EvaluationCaseResultRead],
) -> EvaluationResponse:
    """把评测结果回填到提交记录，并组装成接口响应返回。

    B-2/B-4 会先创建 `submissions` 记录。
    B-3 只在能按 submission_id 找到记录时回填结果；
    如果找不到，则保持评测接口可用，只返回本次评测结果。
    """

    submission = db.get(Submission, payload.submission_id)
    if submission is not None:
        submission.question_id = question.id
        submission.code = payload.submitted_code
        submission.language = payload.language
        submission.status = "COMPLETED"
        submission.overall_score = overall_score
        submission.passed_count = passed_count
        submission.total_count = total_count
        submission.overall_comment = overall_comment
        submission.static_issues = [issue.model_dump() for issue in static_issues]
        submission.case_results = [case.model_dump() for case in case_results]
        db.add(submission)
        db.commit()
    return EvaluationResponse(
        question_id=question.id,
        submission_id=payload.submission_id,
        overall_score=overall_score,
        passed_count=passed_count,
        total_count=total_count,
        overall_comment=overall_comment,
        static_issues=static_issues,
        case_results=case_results,
    )
