from sqlalchemy.orm import Session

from app.judge.api_runner import run_api_case
from app.judge.security_checks import scan_script_code, scan_shell_code
from app.judge.shell_checks import CHECKERS
from app.models import EvaluationCaseResult, EvaluationRecord, Question
from app.schemas import EvaluateRequest, EvaluationCaseResultRead, EvaluationResponse, StaticIssue


def evaluate_submission(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    if question.question_type == "api":
        return _evaluate_api(db, question, payload)
    return _evaluate_shell(db, question, payload)


def _evaluate_shell(db: Session, question: Question, payload: EvaluateRequest) -> EvaluationResponse:
    static_issues = scan_script_code(payload.submitted_code) if question.question_type == "script" else scan_shell_code(payload.submitted_code, question.allowed_commands)
    if static_issues:
        return _persist_response(db, question, payload, 0.0, 0, 0, "代码安全检查未通过。", static_issues, [])

    checker = CHECKERS.get(question.id)
    if checker is None:
        return _persist_response(db, question, payload, 0.0, 0, 0, "题目暂未配置判题器。", [], [])

    case = question.test_cases[0]
    outcome = checker(payload.submitted_code)
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
    entry_function = question.metadata_json.get("entry_function", "solve")
    case_results: list[EvaluationCaseResultRead] = []
    passed_count = 0
    total_weight = 0.0
    obtained = 0.0
    for case in question.test_cases:
        args = case.call_args_json or []
        result = run_api_case(payload.submitted_code, entry_function, args)
        expected = case.expected_output
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
