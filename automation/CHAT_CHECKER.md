> **2026-11-17 更新：禁止自动创建新的 Orca Chat。** 只有检测到当前 Orca CLI 提供 `chat list/send`、并找到此项目已存在且空闲的 OpenCode Chat 时，checker 才将新任务继续发送到该 Chat；复用后固定会话ID。当前 Orca 1.4.261 尚未提供这些命令，因此新任务显示 `WAIT_EXISTING_ORCA_CHAT` 并继续检查，但绝不新建窗口，也不把未投递任务标记为已领取。无需运行 headless OpenCode。原下文每任务新建 Chat 的描述为历史方案。

# Python 课程：GitHub → Orca Chat 自动领取

**2026-11-17 新增。** 项目工作树：`D:\课程\python`，远端：`gaolingxi/python`。

- Windows 计划任务：`Python-Course-Orca-Chat-Checker-10min`；每10分钟通过 `pythonw.exe` 后台运行 `automation/orca_chat_checker.py`，**不打开终端窗口**。
- 使用 `git fetch origin main` 只读检查 GitHub 的 `OPENCODE_TASK.md`；本地科研/课件文件不会由 checker 自动合并或更改。
- 领取条件**全部满足**：`TASK_ID` 是新的非空ID；`STATUS: PENDING` 或 `READY`；`EXECUTOR: OPENCODE`；`NEXT_ACTOR: OPENCODE`；`AUTOMATION_READY: YES`；未要求用户审核、没有同 TASK_ID 的 DONE/BLOCKED 报告。
- 命中新任务时使用 Orca 的 **`agent launch --agent opencode --surface chat --prompt`** 在**当前项目**新建原生 Chat；不是向终端发“继续”，也不是向已有 Chat 加消息（Orca CLI 当前不支持后者）。
- 第一次运行只登记旧任务基线，避免突然启动旧课件任务；没有新任务时不会打开聊天。后续每个TASK_ID最多调用一次 Chat；若启动反馈不确定，写入 `LAUNCH_UNCONFIRMED` 并停止自动重试，避免重复执行。
- checker 运行状态与日志保存在本项目 `.git/python-course-orca-chat-checker/`（非公开 GitHub）；不写入课件目录，更不上传学生信息/教师答案。
- 教师提供的测试答案、课程内学生信息和成绩仍按 AGENTS.md 保护；checker本身不处理或上传课程内容。

## 使用 / 检查

```powershell
python automation/orca_chat_checker.py --doctor # GitHub 与 Orca 工作树就绪检查，不启动Chat
python automation/orca_chat_checker.py --check  # 查看新任务是否满足自动领取条件，不启动Chat
python -m unittest discover -s automation/tests -p test_orca_chat_checker.py -v
```

## 创建新任务

ChatGPT 把具体任务写入 `OPENCODE_TASK.md` 并推送到 GitHub main，字段例如：

```text
TASK_ID: PYTHON2026_CH05_EXERCISES_20261118
STATUS: PENDING
EXECUTOR: OPENCODE
NEXT_ACTOR: OPENCODE
AUTOMATION_READY: YES
USER_REVIEW_REQUIRED: NO

# 任务
先安全同步 GitHub，读取 AGENTS.md；仅完成任务说明中要求的教学文件修改。
```

OpenCode 完成后写 `OPENCODE_REPORT.md`（含同 TASK_ID、`STATUS: DONE/BLOCKED`、证据与实际提交），并推送。发布时不能把已完成旧任务改头换面重发，也不能为改变显著性或考试答案去自动扩张范围。

手动关闭：在 Windows 任务计划程序中禁用 `Python-Course-Orca-Chat-Checker-10min`。
