# OPENCODE_TASK｜Python 课堂小测一 · 班级1 · 按原始修改时间选卷

TASK_ID: PYTHON_QUIZ1_CLASS1_SELECT_LATEST_MTIME
状态：READY_FOR_OPENCODE（本地连接在线时执行）

## 目标

对 `python2026/课堂测试1/班级 1` 的71个学生文件夹、95份提交统一按 `gaolingxi/skill/assignment-grading/SKILL.md` V6 重新审核。**有多个文件的学生仅使用原始收卷目录中最后修改时间最晚的那份进行最终候选评分，不使用最高分或作答最多的版本。** 所有版本保留逐题原始评分。

## 必须使用原始收卷目录

当前公开GitHub中原卷来自2026-11-16一次批量提交；所有重复文件的Git提交时间相同，不代表学生原始修改时间。Jupyter Notebook内未保存可确认的修改时间，不能靠Git时间或文件名的`(2)`、`改`来猜。

先在 Windows 本地只读原始目录（提交检查报告中的路径）：

```powershell
$env:CLASS1_ORIGINAL_SOURCE_DIR = 'C:\Users\Public\Documents\极域课堂管理系统软件V6.0 2016 豪华版\guest\Received Files\班级 1'
python 'python2026/课堂测试1/grade_class1.py'
```

工作目录必须是当前 `gaolingxi/python` 仓库根目录，先 `git pull --ff-only`。脚本不修改学生原卷。**读取每个原始文件的 `st_mtime_ns`，先做SHA256原始字节比对**；原始文件缺失、内容不一致或时间相同时，标记 `LATEST_UNVERIFIED`，不得改为“分最高/最完整”。

## 输出与检查

全部留在仓库工作目录 `python2026/课堂测试1/班级 1/批改结果/`，已经被 `.gitignore` 排除：

- `latest_selection_evidence.csv`：每份文件的修改时间、SHA证据、选中状态；
- `grade_summary_provisional.csv`：71个学生文件夹，最新有效卷的12题得分；
- `grading_detail.csv`：95份卷子的全部逐题记录；
- `execution_manifest.csv`、`extracted_results.csv`、`source_integrity_audit.csv`；
- `grading_audit_findings.csv`、`grading_audit_summary.md`。

完成后逐项对账：17个重复提交文件夹的全部可核实修改时间、选中的最新版文件、相应的12题分数，以及未解决的身份/结构审计异常。必须清楚区分【最新版选卷通过】和【最后成绩审计通过】，不得把初评分当正式分。不要提交学生个人分数、原始答案或评分细节到公共GitHub；只回写不含个人信息的任务状态总结。

停止条件：`71文件夹版本选择完毕（或列出确实缺时间的BLOCK） → 全班评分证据通过SOURCE_INTEGRITY_GATE → 结构审计 → DONE_AWAITING_TEACHER_REVIEW`。
