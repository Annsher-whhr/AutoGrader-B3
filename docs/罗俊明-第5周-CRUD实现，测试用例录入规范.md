# 罗俊明-第5周-CRUD实现，测试用例录入规范

## 1. 本周工作目标

按照项目工作计划，第 5 周我的重点任务是：

- 推进 `B3` 题库管理部分的 CRUD 实现
- 明确测试用例录入规范

结合当前项目起步阶段的实际情况，本周优先完成了题库的“读、更新、导入创建”主链路，并同步把测试用例的字段结构、录入方式和约束规则整理出来，保证后续题目扩充时数据格式统一、可维护、可评测。

---

## 2. 本周完成内容

### 2.1 完成题库基础读写接口

本周已经完成以下题库管理接口：

- `GET /api/v1/b3/questions`
- `GET /api/v1/b3/questions/{question_id}`
- `GET /api/v1/b3/questions/{question_id}/cases`
- `PUT /api/v1/b3/questions/{question_id}`
- `POST /api/v1/b3/questions/import/problem-txt`

文件位置：

- `app/main.py`
- `app/services/question_service.py`
- `app/schemas.py`

当前这一版的实现策略是：

- “创建”阶段先通过导入 `problem.txt + seed_data.py` 完成
- “读取”通过列表、详情、用例接口完成
- “更新”通过 `PUT` 接口做部分字段更新
- “删除”暂不做物理删除，保留 `status` 字段用于后续停用 / 软删除扩展

也就是说，本周已经把题库管理的主体链路打通，满足当前开发阶段的使用需求。

### 2.2 完成题目与测试用例的数据模型设计

本周把题目和测试用例的数据结构固定下来，方便后续评测器直接读取。

文件位置：

- `app/models.py`

当前核心模型包括：

- `Question`
- `TestCase`
- `EvaluationRecord`
- `EvaluationCaseResult`

其中和题库维护最相关的是前两张表。

`Question` 负责保存：

- 题目编号
- 标题
- 描述
- 题目类型
- 允许命令
- 时间 / 内存限制
- 扩展元数据
- 状态字段

`TestCase` 负责保存：

- 用例序号
- 用例描述
- 标准输入
- 预期输出
- 输入文件
- 预期结果文件
- 接口型题调用参数
- 权重
- 是否隐藏

### 2.3 完成测试用例录入规范初稿

本周已经结合现有题目落地情况，把测试用例录入规范统一下来，避免后续不同成员录入方式不一致。

文件位置：

- `app/models.py`
- `app/seed_data.py`
- `app/schemas.py`

当前约定如下：

- `case_no`：同一题内按自然数递增，便于展示和追踪
- `description`：必须写清测试点意图，不能只写“测试1”
- `score_weight`：默认 `1.0`，后续支持多测试点加权
- `input_data`：用于命令行输入型题目
- `expected_output`：用于标准输出精确比对
- `input_files_json`：用于文件题的输入文件树
- `expected_files_json`：用于文件题执行后的目标文件比对
- `call_args_json`：用于接口调用型题目的参数配置
- `is_hidden`：用于隐藏测试点控制

### 2.4 完成题面导入与结构化题库合并逻辑

本周还完成了导题逻辑，保证题目描述和判题配置能够同时落库。

文件位置：

- `app/problem_parser.py`
- `app/services/question_service.py`
- `app/seed_data.py`

当前的实现方式是：

1. 先从 `problem.txt` 解析原始题面
2. 再用 `seed_data.py` 提供结构化判题配置
3. 最后把两部分合并后写入数据库

这样做的好处是：

- 保留原始题面来源
- 保留结构化判题数据
- 题面和判题规则分层维护，后续更容易扩展

---

## 3. 本周成果

### 3.1 题库维护已经具备基础可用性

截至本周，`B3` 的题库管理已经能够完成：

- 导入题目
- 查询题目列表
- 查询题目详情
- 查询某题测试用例
- 更新题目基础字段

这意味着后续联调时，`B2` 或教师端已经可以通过接口读取题库和更新部分题目信息。

### 3.2 测试用例录入字段已经统一

本周把不同题型的测试数据统一进一套结构里，基本覆盖了三类题：

- 命令行输入型
- 文件型
- 接口调用型

后续继续补题时，只要遵守统一录入规范，就可以直接复用现有评测链路。

### 3.3 为后续真正完整 CRUD 留好了扩展口

虽然当前阶段还没有单独开放“新增题目页面接口”和“删除题目接口”，但本周已经把后续扩展所需的基础打好了：

- `QuestionUpdate` 采用部分更新模型
- `status` 字段已经预留停用能力
- `Question` 与 `TestCase` 关系已经明确
- 题面导入与种子数据结构已经稳定

这为后续继续补齐更完整的后台管理能力提供了基础。

---

## 4. 本周是如何完成的

### 4.1 先固定模型，再做接口

为了避免接口和数据库字段反复返工，本周先把 `Question`、`TestCase` 的字段结构定下来，再基于这些结构去定义返回模型和接口。

例如当前 `TestCase` 里已经包含了文件题和 API 题需要的关键字段：

```python
class TestCase(Base):
    case_no = mapped_column(Integer, nullable=False)
    description = mapped_column(String(255), nullable=False)
    input_data = mapped_column(Text)
    expected_output = mapped_column(Text)
    input_files_json = mapped_column(JSON)
    expected_files_json = mapped_column(JSON)
    call_args_json = mapped_column(JSON)
    is_hidden = mapped_column(Boolean, default=False)
```

### 4.2 用部分更新接口控制修改范围

题库修改接口本周采用了“部分更新”设计，避免前端每次都提交完整对象。

文件位置：

- `app/schemas.py`
- `app/main.py`

当前请求体模型如下：

```python
class QuestionUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    difficulty: str | None = None
    time_limit_ms: int | None = None
    memory_limit_mb: int | None = None
    allowed_commands: list[str] | None = None
    metadata_json: dict | None = None
    status: str | None = None
```

这样后续维护题目时，只需要提交变动字段即可。

### 4.3 用自动化测试验证 CRUD 主链路

本周已经补充了对应接口测试，确保题库读写链路可用。

文件位置：

- `tests/test_app_extra.py`

已验证的测试包括：

- `test_question_list_detail_and_cases`
- `test_import_uses_problem_txt_description`
- `test_question_update`
- `test_missing_question_endpoints_return_404`

这些测试说明当前题库导入、查询、更新等操作已经具备基本稳定性。

---

## 5. 测试用例录入规范

为了方便后续题库继续扩展，本周把录入规范整理如下：

### 5.1 通用规范

- 每道题至少有 1 个测试用例
- `case_no` 在同一题内必须唯一，且建议按执行顺序递增
- `description` 必须说明测试目标
- `expected_output` 一律按精确文本比对，默认保留换行
- `score_weight` 必须为正数，当前默认 `1.0`

### 5.2 命令题录入规范

- 主要使用 `expected_output`
- 如果需要辅助文件，也可补 `input_files_json`
- 命令白名单统一写在 `Question.allowed_commands`

### 5.3 文件题录入规范

- 输入文件必须写入 `input_files_json`
- 目标文件结果必须写入 `expected_files_json`
- 只读 / 可写权限控制不写在用例里，统一写在 `Question.metadata_json`
- 如果需要校验“旧文件应消失”，放在题目元数据中维护

### 5.4 接口型题录入规范

- 调用参数统一写入 `call_args_json`
- 预期返回值写入 `expected_output`
- 入口函数名统一由题目元数据 `entry_function` 指定

---

## 6. 本周涉及文件位置

- `app/main.py`：题库相关接口定义
- `app/services/question_service.py`：题库导入、查询逻辑
- `app/models.py`：题目与测试用例数据模型
- `app/schemas.py`：接口请求 / 返回结构
- `app/seed_data.py`：结构化题目与测试用例录入数据
- `app/problem_parser.py`：原始题面解析
- `tests/test_app_extra.py`：CRUD 与题库接口测试
- `docs/B3_API_使用文档.md`：接口用法说明

---

## 7. 本周总结

本周已经完成 `B3` 题库管理的基础 CRUD 主链路，并同步形成了测试用例录入规范初稿。  
当前系统已经具备“导题、查题、查用例、改题”的基本能力，也把后续新增题目、补测试点、接教师端管理功能所需要的数据结构先稳定了下来。

从第 5 周目标来看，本周的工作已经完成了题库管理部分的关键基础建设，为后续数据补全、答案预评和评测结果存储打下了接口和模型基础。
