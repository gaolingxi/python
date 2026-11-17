# 固定 OpenCode 终端模式（2026-11-17）

因每次自动领取在 Orca 原生 Chat 中新建窗口，checker 已改回 **一个项目绑定同一个 OpenCode TUI 终端**。

- 任务审核、锁、去重和 GitHub 双文件状态门槛由各项目原 watcher 保持；修改的仅为 `orca_existing_chat.py` 的兼容发送层。旧文件名只是维持接口兼容，**实际使用 `terminal list/show/wait/send`，绝不使用 `agent launch`**。
- 固定终端绑定于项目 Git common dir 下的 `opencode-fixed-terminal-binding.json`；包含终端 `handle`、`incarnation_id` 和精确 Orca `worktree`。只能自动绑定唯一已存在的、已连接且可写的 OpenCode TUI；绑定后不随意重选。
- checker 不创建终端、不打开新窗口。已关闭或失效的固定终端返回 `WAIT_FIXED_TERMINAL`，等用户明确恢复或管理员重新绑定，不能在每个任务周期新开一个。
- 只有 TUI 闲置且明确匹配同一项目才向它发送 `继续 + TASK_ID ...`，已有发送/未知状态保留去重，不重发。
- 若旧 Chat 任务正在执行或已有 `DONE/BLOCKED` 报告，不得跨模式重复执行；自动化切换不重置任务 ID、V7/P03 云端标签工作或原研究数据。
- Windows 定时任务每10分钟运行，不改变既有 GitHub 状态协议。用户明确暂停的 `AI-income-age-gap` 不参与本轮恢复。
