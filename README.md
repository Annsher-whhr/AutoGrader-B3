# AutoGrader B3

`B3` 是独立的后端判题服务，覆盖 `problem.txt` 中第 2 到第 10 题，并保留 API 调用型评测框架。

## 启动

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

4. 导入预置题目

```http
POST /api/v1/b3/questions/import/problem-txt
```

## 已实现能力

- 9 道题的题库存储与读取
- 最小必要接口：列表、详情、更新、导题、评测、标答自检
- 安全控制：危险命令扫描、危险 shell 语法扫描、脚本死循环特征扫描
- 三类执行框架：
  - command/file：基于固定题目规则的受控评测
  - api：Python `import` 后调用指定函数
- 结果输出：
  - 总评分
  - 用例通过数
  - 细节评分
  - 安全问题列表
