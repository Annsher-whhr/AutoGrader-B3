# B3 Ubuntu 运维与判题环境

## 1. 安装系统依赖

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip mysql-server docker.io
```

## 2. 初始化 Python 环境

```bash
cd /home/lenovo/b3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. 启动 MySQL 并准备数据库

```bash
sudo systemctl enable --now mysql
mysql -uroot -p
```

执行：

```sql
ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '123456';
CREATE DATABASE IF NOT EXISTS autograder_b3 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

`.env` 推荐配置：

```env
DATABASE_URL=mysql+pymysql://root:123456@127.0.0.1:3306/autograder_b3?charset=utf8mb4
APP_PORT=8003
DEBUG=true
SANDBOX_BACKEND=auto
SANDBOX_DOCKER_IMAGE=autograder-b3-judge:latest
```

## 4. 构建 Docker 判题镜像

```bash
sudo usermod -aG docker "$USER"
newgrp docker
docker build -t autograder-b3-judge:latest -f docker/judge.Dockerfile .
```

如果当前机器还没装好 Docker，也可以先临时切到：

```env
SANDBOX_BACKEND=local
```

这会使用本机受限子进程执行，方便先调试功能。

## 5. 初始化数据库结构并导入题库

```bash
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

另开一个终端导题：

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/questions/import/problem-txt
```

## 6. 验证动态判题

参考答案自检：

```bash
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q05
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/Q10
curl -X POST http://127.0.0.1:8003/api/v1/b3/evaluate/answer/API_DEMO
```

运行测试：

```bash
source .venv/bin/activate
pytest -q
```

## 7. 当前判题策略说明

- `auto`：优先使用 Docker 镜像，镜像不可用时回退到本机受限子进程
- `docker`：强制使用 Docker 判题，镜像缺失会直接报错
- `local`：强制使用本机受限子进程，适合开发阶段

## 8. 已接入动态执行的题目

- `Q02`：mock `ssh` 验证目标和参数
- `Q03`：mock `who/uname/date/cal`，其余命令真实执行
- `Q04`：真实执行目录切换和文件拼接
- `Q05`：真实执行 `head/tail/cp/mv`，并检查文件结果
- `Q06`：mock `vi`，真实执行 `chmod`
- `Q07-Q09`：真实执行文本处理命令
- `Q10`：真实执行 shell 脚本
- `API_DEMO`：统一走沙盒中的 Python 运行器
