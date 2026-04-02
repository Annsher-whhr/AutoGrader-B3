# AutoGrader B3

`B3` 是 `AutoGrader` 的独立后端判题服务，当前覆盖 `problem.txt` 中第 2 题到第 10 题，并额外保留了一个 `API_DEMO` 用于演示 API 调用型评测流程。

## 当前状态

目前这版项目已经具备：

- 题库导入、查询、更新
- shell / script 题静态安全检查
- 固定题规则判题
- API 调用型代码执行框架
- 评测记录落库与结果返回
- 自动化测试覆盖 14 条核心路径

这版更适合教学演示和阶段验收，还不是通用 OJ，也还没有接入容器隔离、JWT 鉴权和 B2/B4 联调。

## 启动方式

1. 安装依赖

```powershell
pip install -r requirements.txt
```

2. 配置数据库

复制 `.env.example` 为 `.env` 并填写 `DATABASE_URL`。默认推荐 MySQL：

```env
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/autograder_b3?charset=utf8mb4
```

3. 启动服务

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

4. 初始化数据库结构

```powershell
alembic upgrade head
```

5. 导入预置题目

```http
POST /api/v1/b3/questions/import/problem-txt
```

## 已实现能力

- 预置题库：`Q02` 到 `Q10`，以及 `API_DEMO`
- 基础接口：
  - 题目列表
  - 题目详情
  - 题目更新
  - 测试用例查询
  - 导题
  - 提交评测
  - 参考答案自检
- 安全控制：
  - 危险命令扫描
  - 危险 shell 语法扫描
  - 路径穿越检查
  - 死循环特征检查
- 三类执行框架：
  - `command` / `file`：基于固定题目规则的受控评测
  - `script`：在规则判题前先做额外静态检查
  - `api`：执行 Python 代码并调用指定入口函数
- 结果输出：
  - 总评分
  - 用例通过数
  - 细粒度 case 结果
  - 静态安全问题列表

## 测试

项目当前使用 `pytest`，并且已经关闭缓存目录生成，避免出现 `pytest-cache-files-*` 噪音目录。

直接运行：

```powershell
pytest -q
```

当前测试结果基线是：

```text
14 passed
```
