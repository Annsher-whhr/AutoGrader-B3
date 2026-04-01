SEEDED_QUESTIONS = [
    {
        "id": "Q02",
        "title": "SSH 登录题",
        "description": "使用 ssh 登录到 127.0.0.1，用户 user01，密码 12345678，登录后退出。",
        "question_type": "command",
        "difficulty": "EASY",
        "allowed_commands": ["ssh", "exit"],
        "metadata_json": {"accepted_patterns": [r"^ssh\s+user01@127\.0\.0\.1$", r"^ssh\s+-l\s+user01\s+127\.0\.0\.1$"]},
        "cases": [
            {"case_no": 1, "description": "基础 SSH 命令", "expected_output": "ssh user01@127.0.0.1", "score_weight": 1.0}
        ],
    },
    {
        "id": "Q03",
        "title": "基础系统命令",
        "description": "who/uname/date/cal/cat 组合命令。",
        "question_type": "command",
        "difficulty": "EASY",
        "allowed_commands": ["who", "uname", "date", "cal", "cat"],
        "metadata_json": {},
        "cases": [{"case_no": 1, "description": "共 5 行命令，命令顺序固定", "score_weight": 1.0}],
    },
    {
        "id": "Q04",
        "title": "目录切换与文件合并",
        "description": "cd/pwd/cat 组合操作。",
        "question_type": "command",
        "difficulty": "EASY",
        "allowed_commands": ["cd", "pwd", "cat"],
        "metadata_json": {},
        "cases": [{"case_no": 1, "description": "5 行命令，验证目录切换与文件合并", "score_weight": 1.0}],
    },
    {
        "id": "Q05",
        "title": "文件查看复制改名",
        "description": "head/tail/ls/cp/mv 组合操作。",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["head", "tail", "ls", "cp", "mv"],
        "metadata_json": {},
        "cases": [
            {
                "case_no": 1,
                "description": "文件与目录操作",
                "input_files_json": {
                    "week5_11.txt": "1\n2\n3\n4\n5\n6\n",
                    "week5_12.txt": "a\nb\nc\nd\ne\nf\n",
                    "week5_14.log": "copy me\n",
                    "week5_15.log": "rename me\n",
                    ".hidden": "x\n",
                    "week5_14_dest/.keep": ""
                },
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q06",
        "title": "vi 与 chmod",
        "description": "使用 vi 参数编辑文件，并调整权限。",
        "question_type": "file",
        "difficulty": "HARD",
        "allowed_commands": ["vi", "vim", "chmod"],
        "metadata_json": {},
        "cases": [
            {
                "case_no": 1,
                "description": "验证 vi 参数命令和 chmod",
                "input_files_json": {"week6_1.txt": "line1\nline2\nline3\nline4\nline5\nline6\n", "week6_2.dat": "payload\n"},
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q07",
        "title": "grep 与 sort",
        "description": "grep/sort 文本处理。",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["grep", "sort"],
        "metadata_json": {},
        "cases": [
            {"case_no": 1, "description": "week7 文本处理", "input_files_json": {"week7.txt": "Linux is great\n\nlinux tools\nNoSpace\nTwo words\n123\n99\nThe quick\nYou too\nOne day\n"}, "score_weight": 1.0}
        ],
    },
    {
        "id": "Q08",
        "title": "sed 文本筛选",
        "description": "sed 查找 argument 所在行。",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["sed"],
        "metadata_json": {},
        "cases": [
            {"case_no": 1, "description": "week8 文本处理", "input_files_json": {"week8.txt": "first line\nArgument is here\nanother\nargument again\n"}, "score_weight": 1.0}
        ],
    },
    {
        "id": "Q09",
        "title": "awk 统计与筛选",
        "description": "awk 处理 employee.txt。",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["awk"],
        "metadata_json": {},
        "cases": [
            {"case_no": 1, "description": "employee.txt 统计", "input_files_json": {"employee.txt": "1 ajay manager account 45000\n2 sunil clerk account 25000\n3 varun manager sales 50000\n4 amit manager account 47000\n5 tarun peon sales 15000\n6 deepak clerk sales 23000\n7 sunil peon sales 13000\n8 satvik director purchase 80000\n"}, "score_weight": 1.0}
        ],
    },
    {
        "id": "Q10",
        "title": "Shell 脚本输出非素数",
        "description": "编写 shell 脚本输出 2-100 内非素数，禁止直接硬编码完整结果。",
        "question_type": "script",
        "difficulty": "HARD",
        "allowed_commands": ["for", "while", "if", "echo", "printf", "test", "expr"],
        "metadata_json": {"expected_output": "4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100\n"},
        "cases": [
            {"case_no": 1, "description": "输出格式与结果", "expected_output": "4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100\n", "score_weight": 1.0}
        ],
    },
]


API_DEMO_QUESTION = {
    "id": "API_DEMO",
    "title": "API 调用型演示题",
    "description": "实现 add(a, b) 并返回两数和。",
    "question_type": "api",
    "difficulty": "EASY",
    "allowed_commands": [],
    "metadata_json": {"entry_function": "add"},
    "cases": [
        {"case_no": 1, "description": "正整数", "call_args_json": [2, 3], "expected_output": "5", "score_weight": 1.0},
        {"case_no": 2, "description": "零值", "call_args_json": [0, 7], "expected_output": "7", "score_weight": 1.0},
    ],
}
