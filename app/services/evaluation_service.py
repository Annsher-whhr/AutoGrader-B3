from sqlalchemy.orm import Session

from app.judge.api_runner import run_api_case
from app.judge.security_checks import scan_script_code, scan_shell_code
from app.judge.shell_checks import CHECKERS
from app.models import EvaluationCaseResult, EvaluationRecord, Question
from app.schemas import EvaluateRequest, EvaluationCaseResultRead, EvaluationResponse, StaticIssue


def evaluate_submission(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    """评测一次提交。

    这是整个评测流程的总入口。
    它会先看题目类型，再决定走哪条评测分支：
    - `api` 题走 Python 函数执行逻辑
    - 其他题走 shell / script 判题逻辑
    """

    if question.question_type == "api":
        return _evaluate_api(db, question, payload)
    return _evaluate_shell(db, question, payload)


def _evaluate_shell(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    """评测 shell / script 类型题目。

    流程分两步：
    1. 先做静态安全检查，避免危险内容进入后续流程
    2. 再根据题目 ID 找到专门的判题函数进行校验
    """

    static_issues = scan_script_code(payload.submitted_code) if question.question_type == "script" else scan_shell_code(payload.submitted_code, question.allowed_commands)
    if static_issues:
        return _persist_response(db, question, payload, 0.0, 0, 0, "代码安全检查未通过。", static_issues, [])

    checker = CHECKERS.get(question.id)
    if checker is None:
        return _persist_response(db, question, payload, 0.0, 0, 0, "题目暂未配置判题器。", [], [])

    case = question.test_cases[0]
    outcome = checker(payload.submitted_code)
    # 当前 shell 类题目采用“单题单大用例”的模式：
    # 只要整体通过，就给 100 分；否则给 0 分。
    score = 100.0 if outcome.passed else 0.0
    case_results = [
        EvaluationCaseResultRead(
            case_id=f"{question.id}_case_{case.case_no:02d}",
            description=case.description,
            passed=outcome.passed,
            score=score,
            actual_output=outcome.actual_output,
            expected_output=outcome.expected_output,
            error=outcome.error,
            execution_time_ms=1.0,
        )
    ]
    comment = "答案通过。" if outcome.passed else f"答案未通过：{outcome.error}"
    return _persist_response(db, question, payload, score, 1 if outcome.passed else 0, 1, comment, [], case_results)


def _evaluate_api(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    """评测 API 类型题目。

    这类题目的答案通常是一段 Python 函数实现，
    所以这里会把用户代码真正执行起来，
    然后拿每个测试用例去调用入口函数并比对返回值。
    """

    entry_function = question.metadata_json.get("entry_function", "solve")
    case_results: list[EvaluationCaseResultRead] = []
    passed_count = 0
    total_weight = 0.0
    obtained = 0.0
    for case in question.test_cases:
        args = case.call_args_json or []
        result = run_api_case(payload.submitted_code, entry_function, args)
        expected = case.expected_output
        # API 题当前采用“函数返回值转成字符串后比较”的方式判断是否通过。
        passed = result.error is None and result.actual_output == expected
        if passed:
            passed_count += 1
            obtained += case.score_weight
        total_weight += case.score_weight
        case_results.append(
            EvaluationCaseResultRead(
                case_id=f"{question.id}_case_{case.case_no:02d}",
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
    """把评测结果写入数据库，并组装成接口响应返回。

    这样做的好处是：
    - 前端能立刻拿到评测结果
    - 后端也保留了完整的历史提交记录，方便后续追踪
    """

    record = EvaluationRecord(
        submission_id=payload.submission_id,
        question_id=question.id,
        submitted_code=payload.submitted_code,
        language=payload.language,
        overall_score=overall_score,
        passed_count=passed_count,
        total_count=total_count,
        overall_comment=overall_comment,
        static_issues=[issue.model_dump() for issue in static_issues],
    )
    for case in case_results:
        record.case_results.append(
            EvaluationCaseResult(
                case_id=case.case_id,
                description=case.description,
                passed=case.passed,
                score=case.score,
                actual_output=case.actual_output,
                expected_output=case.expected_output,
                error=case.error,
                execution_time_ms=case.execution_time_ms,
            )
        )
    db.add(record)
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
