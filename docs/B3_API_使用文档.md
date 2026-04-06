# AutoGrader B3 接口使用文档

## 1. 文档目的

这份文档是给 `B1`、`B2`、`B4` 或其他协作组使用的，目标是回答 3 个问题：

1. `B3` 服务是干什么的
2. 其他模块应该按什么顺序调用它
3. 每个接口的请求和返回格式是什么

如果你们要把自己的模块接到 `B3`，优先看这份文档。

---

## 2. B3 服务的职责

`B3` 是题库与判题后端，主要负责：

- 提供题库数据
- 提供测试用例数据
- 接收代码或命令答案并评测
- 返回总分、用例通过情况、静态问题和明细结果
- 将评测记录写入数据库

它不是前端系统，也不是学生管理系统。

对其他组来说，最常用的接口只有两类：

- 题库接口
- 判题接口

---

## 3. 服务地址与基础信息

默认本地运行地址：

```text
http://127.0.0.1:8003
```

API 前缀：

```text
/api/v1/b3
```

完整示例：

```text
http://127.0.0.1:8003/api/v1/b3/questions
```

---

## 4. 其他组最常见的接入场景

### 场景 1：B1/B2 需要查询题目信息

调用：

- `GET /api/v1/b3/questions`
- `GET /api/v1/b3/questions/{question_id}`

### 场景 2：B2 接收到学生答案后，转发给 B3 判题

调用：

- `POST /api/v1/b3/evaluate`

### 场景 3：开发联调时，需要快速验证某题判题逻辑是否正常

调用：

- `POST /api/v1/b3/evaluate/answer/{question_id}`

### 场景 4：初始化环境时，需要先把题目导入数据库

调用：

- `POST /api/v1/b3/questions/import/problem-txt`

---

## 5. 推荐调用顺序

如果是第一次部署或第一次联调，推荐顺序如下：

1. 启动 `B3` 服务
2. 调用健康检查接口确认服务在线
3. 调用导题接口初始化题库
4. 查询题目列表确认题库已存在
5. 用参考答案接口跑一遍自检
6. 再由其他组接入正式的评测调用

---

## 6. 健康检查接口

### 接口

```http
GET /health
```

### 作用

确认服务是否已经启动成功。

### 请求示例

```bash
curl http://127.0.0.1:8003/health
```

### 返回示例

```json
{
  "status": "ok"
}
```

### 其他组如何使用

在正式调 B3 接口之前，建议先调一次 `/health`。

如果返回不是 `200` 或不是 `{"status":"ok"}`，说明服务还没准备好。

---

## 7. 导入题库接口

### 接口

```http
POST /api/v1/b3/questions/import/problem-txt
```

### 作用

把 `problem.txt` 中的题面与内置判题蓝图一起导入数据库。

当前会导入：

- `Q02` 到 `Q10`
- `API_DEMO`

### 请求示例

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/questions/import/problem-txt
```

### 返回示例

返回值是题目数组，每个元素是一个题目的基础信息。

```json
[
  {
    "id": "Q02",
    "title": "SSH 登录题",
    "description": "使用ssh命令登录到127.0.0.1主机......",
    "question_type": "command",
    "difficulty": "EASY",
    "language": "shell",
    "time_limit_ms": 2000,
    "memory_limit_mb": 64,
    "allowed_commands": ["ssh", "exit"],
    "metadata_json": {
      "accepted_invocations": ["user01@127.0.0.1", "-l user01 127.0.0.1"],
      "required_exit_command": "exit"
    },
    "status": "ACTIVE"
  }
]
```

### 说明

- 这个接口是幂等的
- 重复调用不会重复导入同一批题

### 其他组如何使用

部署新环境时建议调用一次。  
正常业务流程里不需要每次都调。

---

## 8. 查询题目列表接口

### 接口

```http
GET /api/v1/b3/questions
```

### 作用

查询当前题库中所有题目的基础信息。

### 请求示例

```bash
curl http://127.0.0.1:8003/api/v1/b3/questions
```

### 返回示例

```json
[
  {
    "id": "Q02",
    "title": "SSH 登录题",
    "description": "使用ssh命令登录到127.0.0.1主机......",
    "question_type": "command",
    "difficulty": "EASY",
    "language": "shell",
    "time_limit_ms": 2000,
    "memory_limit_mb": 64,
    "allowed_commands": ["ssh", "exit"],
    "metadata_json": {
      "accepted_invocations": ["user01@127.0.0.1", "-l user01 127.0.0.1"],
      "required_exit_command": "exit"
    },
    "status": "ACTIVE"
  },
  {
    "id": "Q10",
    "title": "Shell 脚本输出非素数",
    "question_type": "script",
    "difficulty": "HARD",
    "language": "shell",
    "time_limit_ms": 2000,
    "memory_limit_mb": 64,
    "allowed_commands": ["for", "while", "if", "echo", "printf", "test", "expr"],
    "metadata_json": {
      "expected_output": "4,6,8,9,10..."
    },
    "status": "ACTIVE"
  }
]
```

### 其他组如何使用

如果你们需要：

- 展示题目列表
- 让用户选择题号
- 做题目同步

就调这个接口。

---

## 9. 查询题目详情接口

### 接口

```http
GET /api/v1/b3/questions/{question_id}
```

### 作用

查询单道题的完整信息，包括测试用例。

### 路径参数

- `question_id`
  - 例如 `Q02`、`Q05`、`Q10`、`API_DEMO`

### 请求示例

```bash
curl http://127.0.0.1:8003/api/v1/b3/questions/Q02
```

### 返回示例

```json
{
  "id": "Q02",
  "title": "SSH 登录题",
  "description": "使用ssh命令登录到127.0.0.1主机......",
  "question_type": "command",
  "difficulty": "EASY",
  "language": "shell",
  "time_limit_ms": 2000,
  "memory_limit_mb": 64,
  "allowed_commands": ["ssh", "exit"],
  "metadata_json": {
    "accepted_invocations": ["user01@127.0.0.1", "-l user01 127.0.0.1"],
    "required_exit_command": "exit"
  },
  "status": "ACTIVE",
  "test_cases": [
    {
      "id": 1,
      "case_no": 1,
      "description": "基础 SSH 登录并退出",
      "input_data": null,
      "expected_output": "ssh user01@127.0.0.1\nexit",
      "score_weight": 1.0,
      "input_files_json": null,
      "expected_files_json": null,
      "call_args_json": null,
      "is_hidden": false
    }
  ]
}
```

### 其他组如何使用

如果你们要展示题目详情、时间限制、允许命令、测试说明，就用这个接口。

---

## 10. 查询题目测试用例接口

### 接口

```http
GET /api/v1/b3/questions/{question_id}/cases
```

### 作用

只返回测试用例数组，不返回整道题的其余信息。

### 请求示例

```bash
curl http://127.0.0.1:8003/api/v1/b3/questions/Q05/cases
```

### 返回示例

```json
[
  {
    "id": 4,
    "case_no": 1,
    "description": "文件与目录操作",
    "input_data": null,
    "expected_output": "1\n2\n3\n4\n5\n...",
    "score_weight": 1.0,
    "input_files_json": {
      "week5_11.txt": "1\n2\n3\n4\n5\n6\n"
    },
    "expected_files_json": {
      "week5_14_dest/week5_14.log": "copy me\n",
      "week5_15.txt": "rename me\n"
    },
    "call_args_json": null,
    "is_hidden": false
  }
]
```

### 其他组如何使用

一般业务系统不一定要调这个接口。  
更适合：

- 联调
- 调试
- 题库维护

---

## 11. 更新题目接口

### 接口

```http
PUT /api/v1/b3/questions/{question_id}
```

### 作用

对题目信息做部分更新。

### 请求示例

```bash
curl -X PUT http://127.0.0.1:8003/api/v1/b3/questions/Q02 \
  -H "Content-Type: application/json" \
  -d '{
    "title": "新的题目标题",
    "difficulty": "HARD"
  }'
```

### 请求体字段

全部为可选字段：

- `title`
- `description`
- `difficulty`
- `time_limit_ms`
- `memory_limit_mb`
- `allowed_commands`
- `metadata_json`
- `status`

### 返回示例

返回更新后的题目基础信息。

### 其他组如何使用

正常学生端一般不会调这个接口。  
更适合：

- 题库管理端
- 教师维护端

---

## 12. 正式评测接口

这是其他组最重要的接口。

### 接口

```http
POST /api/v1/b3/evaluate
```

### 作用

提交一份答案，让 B3 进行正式评测。

### 请求头

```http
Content-Type: application/json
```

### 请求体字段

```json
{
  "question_id": "Q05",
  "submitted_code": "head -5 week5_11.txt\ntail -5 week5_12.txt\nls -ali\ncp week5_14.log week5_14_dest\nmv week5_15.log week5_15.txt",
  "submission_id": "sub-q05-001",
  "language": "shell"
}
```

字段说明：

- `question_id`
  - 必填
  - 题目编号
- `submitted_code`
  - 必填
  - 提交内容，可以是命令、多行命令、脚本或 Python 代码
- `submission_id`
  - 可选但强烈建议传
  - 由调用方生成，用于追踪本次提交
- `language`
  - 一般 shell 题传 `shell`
  - API 题传 `python`

### shell/file/script 题请求示例

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "question_id":"Q02",
    "submitted_code":"ssh user01@127.0.0.1\nexit",
    "submission_id":"sub-q02-001",
    "language":"shell"
  }'
```

### API 题请求示例

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "question_id":"API_DEMO",
    "submitted_code":"def add(a, b):\n    return a + b\n",
    "submission_id":"sub-api-001",
    "language":"python"
  }'
```

---

## 13. 评测结果返回格式

### 返回结构

```json
{
  "question_id": "Q02",
  "submission_id": "sub-q02-001",
  "overall_score": 100.0,
  "passed_count": 1,
  "total_count": 1,
  "overall_comment": "答案通过。",
  "static_issues": [],
  "case_results": [
    {
      "case_id": "Q02_case_01",
      "description": "基础 SSH 登录并退出",
      "passed": true,
      "score": 100.0,
      "actual_output": "ssh user01@127.0.0.1\nexit",
      "expected_output": "ssh user01@127.0.0.1\nexit",
      "error": null,
      "execution_time_ms": 530.56
    }
  ]
}
```

### 字段说明

- `question_id`
  - 当前评测的是哪道题
- `submission_id`
  - 本次提交的业务 ID
- `overall_score`
  - 总分
- `passed_count`
  - 通过的测试用例数量
- `total_count`
  - 测试用例总数
- `overall_comment`
  - 总体评价
- `static_issues`
  - 静态检查阶段发现的问题
- `case_results`
  - 每个测试用例的详细结果

### `case_results` 字段说明

每个元素包含：

- `case_id`
- `description`
- `passed`
- `score`
- `actual_output`
- `expected_output`
- `error`
- `execution_time_ms`

---

## 14. 静态安全检查失败时会返回什么

如果提交在执行前就被安全规则拦截，仍然会返回完整评测结构。

### 示例

```json
{
  "question_id": "Q10",
  "submission_id": "sub-q10-bad",
  "overall_score": 0.0,
  "passed_count": 0,
  "total_count": 1,
  "overall_comment": "代码安全检查未通过。",
  "static_issues": [
    {
      "code": "HARDCODED_EXPECTED_OUTPUT",
      "message": "hardcoded expected output detected"
    }
  ],
  "case_results": [
    {
      "case_id": "Q10_case_01",
      "description": "输出格式与结果",
      "passed": false,
      "score": 0.0,
      "actual_output": null,
      "expected_output": "4,6,8,9,10,...",
      "error": "hardcoded expected output detected",
      "execution_time_ms": 0.0
    }
  ]
}
```

### 其他组应该怎么处理

建议优先读取：

- `overall_score`
- `overall_comment`
- `static_issues`
- `case_results`

不要只看 HTTP 状态码。  
因为大多数业务级失败仍然会返回 `200`，只是分数是 `0`。

---

## 15. 参考答案自测接口

### 接口

```http
POST /api/v1/b3/evaluate/answer/{question_id}
```

### 作用

使用系统内置参考答案对某题做自测。

### 请求示例

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q02
```

### 返回示例

```json
{
  "question_id": "Q02",
  "submission_id": "answer-Q02",
  "overall_score": 100.0,
  "passed_count": 1,
  "total_count": 1,
  "overall_comment": "答案通过。",
  "static_issues": [],
  "case_results": [
    {
      "case_id": "Q02_case_01",
      "description": "基础 SSH 登录并退出",
      "passed": true,
      "score": 100.0,
      "actual_output": "ssh user01@127.0.0.1\nexit",
      "expected_output": "ssh user01@127.0.0.1\nexit",
      "error": null,
      "execution_time_ms": 530.56
    }
  ]
}
```

### 其他组如何使用

这个接口主要用于：

- 联调前自检
- 演示
- 验证某道题的判题逻辑有没有坏掉

正式业务流一般调用 `/evaluate`，不是这个接口。

---

## 16. 常见错误与状态说明

### 16.1 题目不存在

返回：

- HTTP `404`

示例：

```json
{
  "detail": "Question not found"
}
```

### 16.2 提交内容为空

请求体校验不通过时，FastAPI 会返回 `422`。

### 16.3 代码危险或作弊

接口通常仍返回 `200`，但：

- `overall_score = 0`
- `static_issues` 不为空

### 16.4 运行错误或超时

接口通常仍返回 `200`，但：

- `overall_score = 0`
- `case_results[*].error` 会给出原因

---

## 17. 其他组接入时的推荐处理方式

### 推荐至少保存以下字段

- `question_id`
- `submission_id`
- `overall_score`
- `passed_count`
- `total_count`
- `overall_comment`
- `static_issues`
- `case_results`

### 推荐的调用流程

1. 你们系统生成自己的 `submission_id`
2. 把题号和提交内容发给 `B3`
3. 收到返回后，直接保存整段 JSON
4. 前端只展示你们真正需要的字段

这样做的好处是：

- 后续排错方便
- 不会因为字段遗漏导致信息丢失

---

## 18. B1 / B2 / B4 如何理解与 B3 的关系

### B1

如果 B1 要展示题目或成绩明细，可以调用：

- `/questions`
- `/questions/{question_id}`
- `/evaluate` 的结果数据

### B2

如果 B2 负责接收待测代码，那么 B2 最核心的动作是：

- 把收到的 `question_id + submitted_code + submission_id + language` 转发到 `/evaluate`

### B4

如果 B4 负责数据库与基础后端，B4 需要保证：

- `B3` 的数据库可用
- 表结构已迁移
- 必要时协助统一管理模块间接口文档

---

## 19. 联调建议

联调时建议至少验证这几项：

### 1. 健康检查

```bash
curl http://127.0.0.1:8003/health
```

### 2. 题库是否存在

```bash
curl http://127.0.0.1:8003/api/v1/b3/questions
```

### 3. 参考答案是否通过

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q02
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q10
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/API_DEMO
```

### 4. 人工提交一份错误答案

这样可以确认失败结果结构是否也被正确处理。

---

## 20. 接入时的注意事项

### 注意 1

不要假设只有 HTTP `4xx/5xx` 才代表失败。  
业务失败通常也是 `200`，只是分数为 `0`。

### 注意 2

`submitted_code` 支持多行文本。  
如果是 shell 题，不要把换行丢掉。

### 注意 3

`submission_id` 建议由调用方生成，并确保可追踪。

### 注意 4

当前没有做 JWT 鉴权，所以联调环境默认是内网或开发环境直连。

### 注意 5

当前大多数题目是单主用例评分，所以分数通常是：

- `0`
- `100`

但系统结构本身支持多测试点和部分分。

---

## 21. 一段最简接入说明

如果其他组只想知道“怎么最少步骤接起来”，可以直接照这个流程做：

1. 确认 `B3` 已启动：`GET /health`
2. 确认题库已导入：`GET /api/v1/b3/questions`
3. 提交评测：`POST /api/v1/b3/evaluate`
4. 读取返回：
   - `overall_score`
   - `overall_comment`
   - `static_issues`
   - `case_results`

---

## 22. 当前接口能力总结

当前 `B3` 已经可以稳定提供：

- 题库查询
- 题目详情
- 用例查询
- 题目更新
- 导题
- 正式评测
- 参考答案自测

对其他组来说，真正的核心接口只有两个：

- 题库读取
- 提交评测

如果只接最小闭环，只需要会调：

- `GET /api/v1/b3/questions`
- `POST /api/v1/b3/evaluate`

---

## 23. 推荐文档入口

如果还想进一步理解 B3 的内部实现，可以继续看：

- [docs/B3_整体详细说明文档.md](/home/lenovo/b3/docs/B3_整体详细说明文档.md)
- [docs/ubuntu_setup.md](/home/lenovo/b3/docs/ubuntu_setup.md)
- [FINAL_DELIVERY.md](/home/lenovo/b3/FINAL_DELIVERY.md)
