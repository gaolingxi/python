TASK_ID: PYTHON2026_QUIZ1_GRADE_RESULTS_TO_D_20261117_1933
TASK_VERSION: 1
STATUS: READY
EXECUTOR: OPENCODE
NEXT_ACTOR: OPENCODE
AUTOMATION_READY: YES
USER_REVIEW_REQUIRED: NO

# Python 课堂小测一：只由 OpenCode 执行私人成绩迁移到 D 盘

2026-11-17 19:33｜执行器：ChatGPT｜当前阶段：向OpenCode交接

## 用户明确指示

“你不要自己执行，你让opencode执行。”

**由 OpenCode 本地执行**；ChatGPT 仅发布任务及核验 OpenCode 回报，不能代替 OpenCode 运行迁移、批改或复制。不要扩展成新一轮全班批改。

## 项目与文件夹

- GitHub: https://github.com/gaolingxi/python，main
- Orca 自动领取工作树为 `D:\课程\python`（只作任务入口，不是成绩最终交付位置）。
- **唯一交付的目标工作树：`D:\gaolingxi-python`**。先核对这个路径是 `gaolingxi/python`，然后从此工作树工作。
- **目标班级文件夹：`D:\gaolingxi-python\python2026\课堂测试1\班级 1\`**
- **私人成绩目标文件夹：`D:\gaolingxi-python\python2026\课堂测试1\班级 1\批改结果\`**
- 前次成绩源位置：`E:\gaolingxi-python\python2026\课堂测试1\班级 1\批改结果\`。
- 已有迁移脚本：`D:\gaolingxi-python\python2026\课堂测试1\migrate_reviewed_results_E_to_D.ps1`。
- 2026-11-17稍早本地检查发现当前机器E盘未挂载；这不是ChatGPT让你跳过执行的理由，而是要求你先核实源盘是否已恢复。**当前如确实未恢复，准确汇报 BLOCKED，不要称已完成。**

## OpenCode 执行步骤

1. 在D盘工作树检查远端/分支与工作树安全状态，安全同步 `origin/main`，读取 `AGENTS.md`、`python2026/课堂测试1/OPENCODE_TASK_选最新版.md`、`python2026/课堂测试1/migrate_reviewed_results_E_to_D.ps1`。
2. 确认 D 盘已有71个学生文件夹和95份 `.ipynb` 原始答卷。**不要修改任意学生原始 Notebook。**
3. 检查 E 盘源目录是否能访问（不猜文件路径）；若存在，**由你执行**仓库内已有的只读迁移脚本，把所有复核后私人成绩及审计文件复制到D盘。
4. 核对完整性：`grade_summary_reviewed.csv` **71行**、`grading_detail_reviewed.csv` **852行**、`question_tamper_audit.csv` **1140行**，全部迁移文件 SHA256 与源一致；如源文件缺失或哈希不符，应 BLOCKED，不能伪造。
5. 如果 E 盘仍离线，在目标 `批改结果` 文件夹保留既有 `迁移状态_等待E盘.txt`，不要用旧初评分数冒充复核后分数，也不要用Git检出时间重新决定重复提交的最新版。
6. 在 GitHub 仓库根目录写不含任何姓名、学号、个人成绩的 `OPENCODE_REPORT.md`，带相同 TASK_ID、`STATUS: DONE` 或 `STATUS: BLOCKED`、原因、执行者、执行时间、证据统计与目标文件夹核验状态。安全推送公开仓库的**仅此非敏感状态报告**。不得提交/推送个人成绩、源代码答案或个人可识别记录。
7. 报告清晰区分“已下发任务”“开始执行”“D盘迁移完成”。**只有文件实际存在且验收通过才能 DONE**。不得自行重新判分、调整均分或改变评分口径。

完成时间：待OpenCode运行填写
当前阶段：私人成绩迁移到D盘
当前状态：READY
下一步：OpenCode通过自动领取并执行
你现在要做：无，任务已经交给OpenCode领取
