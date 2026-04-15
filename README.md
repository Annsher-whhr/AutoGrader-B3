# AutoGrader B3

`AutoGrader B3` 是课程项目 `AutoGrader` 中负责“题库管理、判题规则和评测执行”的后端服务。  
它的职责不是接收学生提交或展示成绩，而是为上层模块提供一套可调用的判题能力：导入题目、读取题库、校验提交内容、在受控环境中执行答案，并返回结构化评测结果。

当前仓库已经完成从“静态规则演示版”到“可执行代码判题版”的升级，能够对 shell 命令题、文件题、脚本题和 API 调用题进行动态评测。

## 项目能力

当前版本已经具备以下核心能力：

- 题库导入、题目查询、题目更新、测试用例查询
- `problem.txt` 题面解析与结构化题库配置合并
- shell / script 提交的静态安全检查
- `command`、`file`、`script`、`api` 四类题目的统一评测入口
- Docker 沙箱和本地受限执行双后端
- 评测结果落库与结构化返回
- 自动化测试覆盖主要功能链路

当前覆盖的题目包括：

- `Q02` 到 `Q10`
- `API_DEMO`

其中：

- `Q02-Q04` 主要体现命令题 / 基础文件环境题
- `Q05-Q09` 体现文件题和文本处理题
- `Q10` 为 shell 脚本题
- `API_DEMO` 用于演示 Python 接口调用型判题流程

## 技术栈

- `FastAPI`
- `SQLAlchemy 2`
- `Alembic`
- `Pydantic v2`
- `PyMySQL`
- `pytest`
- `Docker`（可选，用于更强隔离的沙箱执行）

## 项目结构

```text
b3/
├─ app/
│  ├─ core/
│  │  └─ config.py
│  ├─ judge/
│  │  ├─ api_runner.py
│  │  ├─ dynamic_runner.py
│  │  ├─ sandbox.py
│  │  └─ security_checks.py
│  ├─ services/
│  │  ├─ evaluation_service.py
│  │  └─ question_service.py
│  ├─ db.py
│  ├─ main.py
│  ├─ models.py
│  ├─ problem_parser.py
│  ├─ schemas.py
│  └─ seed_data.py
├─ alembic/
├─ docker/
│  └─ judge.Dockerfile
├─ docs/
├─ tests/
├─ problem.txt
├─ requirements.txt
└─ README.md
```

关键文件说明：

- [app/main.py](/home/lenovo/b3/app/main.py)：FastAPI 服务入口与路由定义
- [app/services/question_service.py](/home/lenovo/b3/app/services/question_service.py)：题库导入、查询逻辑
- [app/services/evaluation_service.py](/home/lenovo/b3/app/services/evaluation_service.py)：评测主流程入口
- [app/judge/security_checks.py](/home/lenovo/b3/app/judge/security_checks.py)：shell / script 静态安全检查
- [app/judge/dynamic_runner.py](/home/lenovo/b3/app/judge/dynamic_runner.py)：动态执行判题、文件环境准备、输出与文件结果比对
- [app/judge/api_runner.py](/home/lenovo/b3/app/judge/api_runner.py)：API 题执行与 AST 安全检查
- [app/judge/sandbox.py](/home/lenovo/b3/app/judge/sandbox.py)：本地 / Docker 沙箱抽象
- [app/models.py](/home/lenovo/b3/app/models.py)：数据库模型
- [app/seed_data.py](/home/lenovo/b3/app/seed_data.py)：结构化题库蓝图与测试数据

## 支持的题目类型

### 1. `command`

适用于命令行题目。  
系统会在受控工作目录中执行提交内容，并校验标准输出、命令副作用或特定题目要求。

典型题目：

- `Q02`
- `Q03`
- `Q04`

### 2. `file`

适用于文件读取、复制、改名、权限修改和文本处理类题目。  
系统会在执行前构造输入文件环境，并在执行后比对：

- 标准输出
- 目标文件内容
- 只读文件是否被修改
- 某些路径是否应被删除或保留

典型题目：

- `Q05`
- `Q06`
- `Q07`
- `Q08`
- `Q09`

### 3. `script`

适用于需要提交一整段 shell 脚本的题目。  
系统会先做静态安全检查，再在沙箱中执行，并校验最终输出。

典型题目：

- `Q10`

### 4. `api`

适用于提交函数实现并由系统调用入口函数测试的题目。  
系统会在执行前做 Python `AST` 安全检查，再在受控环境中执行用户代码。

典型题目：

- `API_DEMO`

## 安全设计

当前版本采用“静态检查 + 受控执行”两层策略。

### 静态检查

对 shell / script 题目，系统会检查：

- 危险命令
- 不允许的 shell 拼接语法
- 路径穿越
- 疑似无限循环
- 某些题目的硬编码答案
- 是否使用了题目白名单之外的命令

对 API 题目，系统会检查：

- 危险模块导入
- 高风险函数调用

### 受控执行

系统提供两种执行后端：

- `local`：本地受限子进程回退方案
- `docker`：容器沙箱方案

默认配置为：

- `SANDBOX_BACKEND=auto`

即 Docker 可用时优先走容器，否则回退到本地执行。

Docker 沙箱当前具备：

- 无网络
- 只读根文件系统
- CPU / 内存 / 进程数限制
- 单独挂载当前评测工作目录

## 数据模型

当前数据库核心表为：

- `questions`
- `test_cases`
- `evaluation_records`
- `evaluation_case_results`

它们分别承担：

- 题目定义
- 测试用例配置
- 一次提交的总体评测记录
- 一次提交中每个测试点的明细结果

## 快速启动

### 1. 安装依赖

建议先创建虚拟环境，再安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

当前仓库没有内置 `.env.example`，请在项目根目录自行创建 `.env`。  
一个最小配置示例如下：

```env
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/autograder_b3?charset=utf8mb4
DEBUG=true
SANDBOX_BACKEND=auto
SANDBOX_DOCKER_IMAGE=autograder-b3-judge:latest
```

如果你只是本地快速验证，也可以改成 SQLite：

```env
DATABASE_URL=sqlite+pysqlite:///./autograder_b3.db
DEBUG=true
SANDBOX_BACKEND=local
```

### 3. 初始化数据库

```bash
alembic upgrade head
```

### 4. 可选：构建 Docker 判题镜像

如果希望使用 Docker 沙箱，需要先构建镜像：

```bash
docker build -t autograder-b3-judge:latest -f docker/judge.Dockerfile .
```

### 5. 启动服务

如果前面没有一直处于激活状态，先进入项目虚拟环境：

```bash
source .venv/bin/activate
```

再启动服务：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

启动后可访问：

- 健康检查：`GET /health`
- Swagger 文档：`http://127.0.0.1:8003/docs`

### 6. 导入题库

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/questions/import/problem-txt
```

### 7. 验证服务

查看题目列表：

```bash
curl http://127.0.0.1:8003/api/v1/b3/questions
```

执行参考答案自测：

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q02
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q05
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q10
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/API_DEMO
```

## 接口概览

当前主要接口如下：

- `GET /health`
- `GET /api/v1/b3/questions`
- `GET /api/v1/b3/questions/{question_id}`
- `GET /api/v1/b3/questions/{question_id}/cases`
- `PUT /api/v1/b3/questions/{question_id}`
- `POST /api/v1/b3/questions/import/problem-txt`
- `POST /api/v1/b3/evaluate`
- `POST /api/v1/b3/evaluate/answer/{question_id}`

### 评测请求示例

```json
{
  "question_id": "Q02",
  "submitted_code": "ssh user01@127.0.0.1\nexit",
  "submission_id": "demo-submission",
  "language": "shell"
}
```

### 评测返回内容

系统会返回：

- `question_id`
- `submission_id`
- `overall_score`
- `passed_count`
- `total_count`
- `overall_comment`
- `static_issues`
- `case_results`

这套结构已经可以直接提供给上层模块做成绩展示或评测详情展示。

## 测试

项目当前使用 `pytest` 做自动化测试，`pytest.ini` 中已经关闭缓存目录提供器，避免生成多余缓存目录。

如果尚未激活虚拟环境，先执行：

```bash
source .venv/bin/activate
```

直接运行：

```bash
pytest -q
```

或者直接指定项目虚拟环境中的解释器与测试命令：

```bash
.venv/bin/pytest -q
```

## 当前实现边界

当前版本已经适合：

- 课程项目阶段验收
- 模块联调演示
- B3 单独功能展示
- 判题流程教学演示

当前还没有完整覆盖的内容包括：

- JWT 鉴权
- 真正的题库后台管理界面
- 更复杂的多语言判题
- 面向生产环境的任务队列与并发调度

## 相关文档

- [FINAL_DELIVERY.md](/home/lenovo/b3/FINAL_DELIVERY.md)：最终交付说明
- [docs/B3_整体详细说明文档.md](/home/lenovo/b3/docs/B3_整体详细说明文档.md)：系统整体设计说明
- [docs/B3_API_使用文档.md](/home/lenovo/b3/docs/B3_API_使用文档.md)：接口使用说明
- [docs/ubuntu_setup.md](/home/lenovo/b3/docs/ubuntu_setup.md)：Ubuntu / Docker / MySQL 启动说明
- [docs/数据库设计.md](/home/lenovo/b3/docs/数据库设计.md)：数据库设计说明
- [docs/模块之间的接口设计.md](/home/lenovo/b3/docs/模块之间的接口设计.md)：模块接口说明

## 一句话总结

`AutoGrader B3` 已经实现了题库管理、静态安全检查、动态执行判题、沙箱隔离和评测结果落库的完整闭环，是当前课程项目中负责“判题规则中心”和“题库中心”的后端模块。
