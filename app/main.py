from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.db import Base, engine, get_db
from app.schemas import EvaluateRequest, EvaluationResponse, QuestionDetail, QuestionRead, QuestionUpdate, TestCaseRead
from app.services.evaluation_service import evaluate_submission
from app.services.question_service import get_question, import_seed_questions, list_questions


# 项目启动时自动建表。
# 这是一个教学/演示型项目，所以这里直接在启动时创建数据库表，
# 省去单独跑迁移脚本的步骤。
Base.metadata.create_all(bind=engine)
app = FastAPI(title="AutoGrader B3", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    """健康检查接口。

    一般用来确认服务有没有成功启动。
    """

    return {"status": "ok"}


@app.get("/api/v1/b3/questions", response_model=list[QuestionRead])
def read_questions(db: Session = Depends(get_db)) -> list[QuestionRead]:
    """返回当前数据库里的全部题目。"""

    return list_questions(db)


@app.get("/api/v1/b3/questions/{question_id}", response_model=QuestionDetail)
def read_question(question_id: str, db: Session = Depends(get_db)) -> QuestionDetail:
    """返回单道题的详细信息。

    如果题目不存在，会直接返回 404。
    """

    question = get_question(db, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@app.put("/api/v1/b3/questions/{question_id}", response_model=QuestionRead)
def update_question(question_id: str, payload: QuestionUpdate, db: Session = Depends(get_db)) -> QuestionRead:
    """更新题目。

    这里使用的是“部分更新”思路：
    前端传了哪些字段，就只更新哪些字段。
    """

    question = get_question(db, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(question, key, value)
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@app.get("/api/v1/b3/questions/{question_id}/cases", response_model=list[TestCaseRead])
def read_question_cases(question_id: str, db: Session = Depends(get_db)) -> list[TestCaseRead]:
    """返回某道题的全部测试用例。"""

    question = get_question(db, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question.test_cases


@app.post("/api/v1/b3/questions/import/problem-txt", response_model=list[QuestionRead])
def import_problem_txt(db: Session = Depends(get_db)) -> list[QuestionRead]:
    """把内置示例题导入数据库。"""

    return import_seed_questions(db)


@app.post("/api/v1/b3/evaluate", response_model=EvaluationResponse)
def evaluate(payload: EvaluateRequest, db: Session = Depends(get_db)) -> EvaluationResponse:
    """评测用户提交的答案。"""

    question = get_question(db, payload.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return evaluate_submission(db, question, payload)


@app.post("/api/v1/b3/evaluate/answer/{question_id}", response_model=EvaluationResponse)
def evaluate_reference_answer(question_id: str, db: Session = Depends(get_db)) -> EvaluationResponse:
    """评测系统内置的参考答案。

    这个接口更像是“自测接口”：
    用来验证某道题的判题逻辑本身是否能跑通。
    """

    question = get_question(db, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    reference_answers = {
        # 这里放的是每道题的参考答案，主要用于快速验证判题流程是否正常。
        "Q02": "ssh user01@127.0.0.1",
        "Q03": "who -b\nuname -r\ndate +%Y|%m|%d_%H:%M\ncal 10 1949\ncat week5_5.txt",
        "Q04": "cd week5_6\npwd\ncd ..\npwd\ncat week5_10_1.txt week5_10_2.txt week5_10_3.txt",
        "Q05": "head -5 week5_11.txt\ntail -5 week5_12.txt\nls -ali\ncp week5_14.log week5_14_dest\nmv week5_15.log week5_15.txt",
        "Q06": "vi +$'e week6_1.txt' +$':2' +$'i\\n[line22222222]' +$':5d' +x\nchmod u+x,g-w,o=r week6_2.dat",
        "Q07": "grep -i -c 'linux' week7.txt\ngrep -c '^$' week7.txt\ngrep -vn ' ' week7.txt | grep -v '^$'\ngrep -E '^[0-9]+$' week7.txt | sort -nr\ngrep -E '^(The|You|One)' week7.txt | sort -r",
        "Q08": "sed -n '/[Aa]rgument/=' week8.txt\nsed -n '/[Aa]rgument/{=;p;}' week8.txt",
        "Q09": "awk '$4==\"sales\"{sum+=$5;count++} END{print sum/count}' employee.txt\nawk '$2==\"varun\"{print}' employee.txt",
        "Q10": "for i in $(seq 2 100); do\n  c=0\n  for j in $(seq 2 $((i-1))); do\n    if [ $((i%j)) -eq 0 ]; then c=1; fi\n  done\n  if [ $c -eq 1 ]; then printf '%s,' \"$i\"; fi\ndone\n",
        "API_DEMO": "def add(a, b):\n    return a + b\n",
    }
    payload = EvaluateRequest(question_id=question_id, submitted_code=reference_answers[question_id], submission_id=f"answer-{question_id}", language=question.language)
    return evaluate_submission(db, question, payload)
