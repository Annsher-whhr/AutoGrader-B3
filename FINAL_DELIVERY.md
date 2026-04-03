# AutoGrader B3 最终交付说明

## 1. 项目结论

`B3` 模块已经完成从“静态规则判题演示版”到“可执行代码判题版”的升级，当前可以在 Ubuntu 环境中完成：

- 题库导入与查询
- MySQL 数据库存储
- Shell / 文件 / 脚本题的动态执行判题
- Python API 题的沙盒执行判题
- 评测结果落库
- 自动化测试验证

当前测试结果：

```text
26 passed
```

## 2. 当前实现能力

### 2.1 题库与数据

- 题面来源：`problem.txt`
- 已导入题目：`Q02` 到 `Q10`，以及 `API_DEMO`
- 数据库存储：
  - `questions`
  - `test_cases`
  - `evaluation_records`
  - `evaluation_case_results`

### 2.2 判题能力

- `Q02`：通过 mock `ssh` 在沙盒中验证目标主机和登录参数
- `Q03-Q09`：在受控工作目录中真实执行命令，并比对输出/文件结果
- `Q10`：真实执行 shell 脚本并校验输出，同时保留硬编码答案拦截
- `API_DEMO`：在沙盒中执行 Python 代码并调用指定函数

### 2.3 沙盒能力

- 支持两种后端：
  - `Docker` 容器沙盒
  - 本地受限子进程回退
- 当前配置为：
  - `SANDBOX_BACKEND=auto`
  - Docker 可用时优先走容器

## 3. 关键文件

- 服务入口：[app/main.py](/home/lenovo/b3/app/main.py)
- 评测总流程：[app/services/evaluation_service.py](/home/lenovo/b3/app/services/evaluation_service.py)
- 动态判题执行器：[app/judge/dynamic_runner.py](/home/lenovo/b3/app/judge/dynamic_runner.py)
- 沙盒实现：[app/judge/sandbox.py](/home/lenovo/b3/app/judge/sandbox.py)
- Python API 判题：[app/judge/api_runner.py](/home/lenovo/b3/app/judge/api_runner.py)
- 安全检查：[app/judge/security_checks.py](/home/lenovo/b3/app/judge/security_checks.py)
- 题库蓝图：[app/seed_data.py](/home/lenovo/b3/app/seed_data.py)
- 运维说明：[docs/ubuntu_setup.md](/home/lenovo/b3/docs/ubuntu_setup.md)

## 4. 当前环境状态

- Ubuntu / WSL 环境已可运行项目
- MySQL 已恢复并可用
- Docker 已安装并已用于容器判题验证
- B3 参考答案接口已验证通过：
  - `Q02`
  - `Q05`
  - `Q06`
  - `Q10`
  - `API_DEMO`

## 5. 启动与演示

### 5.1 启动服务

```bash
cd ~/b3
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

### 5.2 导入题库

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/questions/import/problem-txt
```

### 5.3 参考答案自测

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q02
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q05
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q10
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/API_DEMO
```

### 5.4 测试

```bash
env DEBUG=true .venv/bin/pytest -q
```

## 6. 适合汇报时的表述

可以直接这样描述当前成果：

> 我们组负责的 B3 模块已经完成题库管理、动态判题和评测结果落库的完整闭环。原先只能通过静态规则判断答案，现在已经支持在 Ubuntu 环境下通过沙盒真实运行代码后再判题，并且已经接入 MySQL 数据库和 Docker 容器沙盒，自动化测试全部通过。
