"""B3 的题目蓝图与附加测试数据。

这里保留的是“判题必须依赖的结构化配置”，例如：
- 题目标题
- 题目类型
- 允许命令
- 测试用例输入文件
- 评测所需的元数据

真正的人类可读题面描述，后续会优先从 `problem.txt` 解析得到，
而不是继续完全依赖这个文件里的硬编码 description。
"""


QUESTION_BLUEPRINTS = [
    {
        "id": "Q02",
        "title": "SSH 登录题",
        "question_type": "command",
        "difficulty": "EASY",
        "allowed_commands": ["ssh", "exit"],
        "metadata_json": {
            "accepted_invocations": ["user01@127.0.0.1", "-l user01 127.0.0.1"],
            "required_exit_command": "exit",
        },
        "cases": [
            {
                "case_no": 1,
                "description": "基础 SSH 登录并退出",
                "expected_output": "ssh user01@127.0.0.1\nexit",
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q03",
        "title": "基础系统命令",
        "question_type": "command",
        "difficulty": "EASY",
        "allowed_commands": ["who", "uname", "date", "cal", "cat"],
        "metadata_json": {"readonly_paths": ["week5_5.txt"]},
        "cases": [
            {
                "case_no": 1,
                "description": "共 5 行命令，命令顺序固定",
                "input_files_json": {"week5_5.txt": "Linux command practice\n"},
                "expected_output": "         system boot  2024-10-01 08:00\n6.8.0-autograder\n2024|10|01_08:00\n    October 1949\nSu Mo Tu We Th Fr Sa\n                   1\n 2  3  4  5  6  7  8\n 9 10 11 12 13 14 15\n16 17 18 19 20 21 22\n23 24 25 26 27 28 29\n30 31\nLinux command practice\n",
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q04",
        "title": "目录切换与文件合并",
        "question_type": "command",
        "difficulty": "EASY",
        "allowed_commands": ["cd", "pwd", "cat"],
        "metadata_json": {
            "expected_output_template": "{child}\n{root}\nalpha\nbeta\ngamma\n",
            "readonly_paths": ["week5_10_1.txt", "week5_10_2.txt", "week5_10_3.txt", "week5_6/.keep"],
        },
        "cases": [
            {
                "case_no": 1,
                "description": "5 行命令，验证目录切换与文件合并",
                "input_files_json": {
                    "week5_6/.keep": "",
                    "week5_10_1.txt": "alpha\n",
                    "week5_10_2.txt": "beta\n",
                    "week5_10_3.txt": "gamma\n",
                },
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q05",
        "title": "文件查看复制改名",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["head", "tail", "ls", "cp", "mv"],
        "metadata_json": {
            "absent_paths": ["week5_15.log"],
            "readonly_paths": ["week5_11.txt", "week5_12.txt", "week5_14.log", ".hidden", "week5_14_dest/.keep"],
        },
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
                "expected_output": "1\n2\n3\n4\n5\nb\nc\nd\ne\nf\ntotal 5\n11 drwxr-xr-x 3 student student 4096 .\n12 drwxr-xr-x 3 student student 4096 ..\n13 -rw-r--r-- 1 student student    2 .hidden\n14 -rw-r--r-- 1 student student   12 week5_11.txt\n15 -rw-r--r-- 1 student student   12 week5_12.txt\n16 -rw-r--r-- 1 student student    8 week5_14.log\n17 drwxr-xr-x 2 student student 4096 week5_14_dest\n18 -rw-r--r-- 1 student student   10 week5_15.log\n",
                "expected_files_json": {"week5_14_dest/week5_14.log": "copy me\n", "week5_15.txt": "rename me\n"},
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q06",
        "title": "vi 与 chmod",
        "question_type": "file",
        "difficulty": "HARD",
        "allowed_commands": ["vi", "vim", "chmod"],
        "metadata_json": {
            "required_vi_markers": ["week6_1.txt", "line22222222", ":5d", "+x"],
            "expected_mode": "754",
            "writable_paths": ["week6_1.txt", "week6_2.dat"],
        },
        "cases": [
            {
                "case_no": 1,
                "description": "验证 vi 参数命令和 chmod",
                "input_files_json": {"week6_1.txt": "line1\nline2\nline3\nline4\nline5\nline6\n", "week6_2.dat": "payload\n"},
                "expected_files_json": {"week6_1.txt": "line1\n[line22222222]\nline2\nline3\nline5\nline6\n"},
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q07",
        "title": "grep 与 sort",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["grep", "sort"],
        "metadata_json": {"readonly_paths": ["week7.txt"]},
        "cases": [
            {
                "case_no": 1,
                "description": "week7 文本处理",
                "input_files_json": {"week7.txt": "Linux is great\n\nlinux tools\nNoSpace\nTwo words\n123\n99\nThe quick\nYou too\nOne day\n"},
                "expected_output": "2\n1\n4:NoSpace\n6:123\n7:99\n123\n99\nYou too\nThe quick\nOne day\n",
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q08",
        "title": "sed 文本筛选",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["sed"],
        "metadata_json": {"readonly_paths": ["week8.txt"]},
        "cases": [
            {
                "case_no": 1,
                "description": "week8 文本处理",
                "input_files_json": {"week8.txt": "first line\nArgument is here\nanother\nargument again\n"},
                "expected_output": "2\n4\n2:Argument is here\n4:argument again\n",
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q09",
        "title": "awk 统计与筛选",
        "question_type": "file",
        "difficulty": "MEDIUM",
        "allowed_commands": ["awk"],
        "metadata_json": {"readonly_paths": ["employee.txt"]},
        "cases": [
            {
                "case_no": 1,
                "description": "employee.txt 统计",
                "input_files_json": {"employee.txt": "1 ajay manager account 45000\n2 sunil clerk account 25000\n3 varun manager sales 50000\n4 amit manager account 47000\n5 tarun peon sales 15000\n6 deepak clerk sales 23000\n7 sunil peon sales 13000\n8 satvik director purchase 80000\n"},
                "expected_output": "25250\n3 varun manager sales 50000\n",
                "score_weight": 1.0,
            }
        ],
    },
    {
        "id": "Q10",
        "title": "Shell 脚本输出非素数",
        "question_type": "script",
        "difficulty": "HARD",
        "allowed_commands": ["for", "while", "if", "echo", "printf", "test", "expr"],
        "metadata_json": {"expected_output": "4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100\n"},
        "cases": [
            {"case_no": 1, "description": "输出格式与结果", "expected_output": "4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100\n", "score_weight": 1.0}
        ],
    },
]


# 这道题主要不是给业务使用，而是用来演示和测试 API 判题流程是否正常。
API_DEMO_QUESTION = {
    "id": "API_DEMO",
    "title": "API 调用型演示题",
    "description": "实现 add(a, b) 并返回两数和。",
    "question_type": "api",
    "difficulty": "EASY",
    "allowed_commands": [],
    "metadata_json": {"entry_function": "add", "python_command": "python3"},
    "cases": [
        {"case_no": 1, "description": "正整数", "call_args_json": [2, 3], "expected_output": "5", "score_weight": 1.0},
        {"case_no": 2, "description": "零值", "call_args_json": [0, 7], "expected_output": "7", "score_weight": 1.0},
    ],
}


def build_seeded_questions(problem_sections: dict[int, str]) -> list[dict]:
    """把题面解析结果和判题蓝图合并成可导入数据库的题目数据。"""

    merged_questions: list[dict] = []
    for blueprint in QUESTION_BLUEPRINTS:
        question_no = int(blueprint["id"][1:])
        description = problem_sections.get(question_no, "").strip()
        payload = dict(blueprint)
        payload["description"] = description or f"{payload['title']}（题面解析失败，当前使用保底描述）"
        merged_questions.append(payload)
    return merged_questions
