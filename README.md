# AutoGrader B3

`B3` 是 `AutoGrader` 的独立后端判题服务，当前覆盖 `problem.txt` 中第 2 题到第 10 题，并额外保留了一个 `API_DEMO` 用于演示 API 调用型评测流程。

## 当前状态

目前这版项目已经具备：

- 题库导入、查询、更新
- shell / script 题静态安全检查
- 动态执行式判题
- Docker / 本地双后端沙盒
- 评测记录落库与结果返回
- 自动化测试覆盖核心路径

这版更适合教学演示和阶段验收，还不是通用 OJ，也还没有接入 JWT 鉴权和 B2/B4 联调。

## 启动方式

1. 安装依赖

```bash
pip install -r requirements.txt
```

2. 配置数据库

复制 `.env.example` 为 `.env` 并填写 `DATABASE_URL`。默认推荐 MySQL：

```env
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/autograder_b3?charset=utf8mb4
SANDBOX_BACKEND=auto
SANDBOX_DOCKER_IMAGE=autograder-b3-judge:latest
```

3. 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

4. 初始化数据库结构

```bash
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
  - `command` / `file`：在受控工作目录里真实执行命令并比对输出/文件结果
  - `script`：先静态安全检查，再执行脚本并核验输出
  - `api`：在统一沙盒里执行 Python 代码并调用指定入口函数
- 结果输出：
  - 总评分
  - 用例通过数
  - 细粒度 case 结果
  - 静态安全问题列表

## 测试

项目当前使用 `pytest`，并且已经关闭缓存目录生成，避免出现 `pytest-cache-files-*` 噪音目录。

直接运行：

```bash
pytest -q
```

完整 Ubuntu / Docker / MySQL 启动流程见 [docs/ubuntu_setup.md](/home/lenovo/b3/docs/ubuntu_setup.md)。

最终交付说明见 [FINAL_DELIVERY.md](/home/lenovo/b3/FINAL_DELIVERY.md)。
