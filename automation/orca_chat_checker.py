#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub -> Orca native Chat task checker for the Python course repository.

Read-only polling. Every NEW authorized TASK_ID launches one project-bound
OpenCode Chat, never an OpenCode terminal or a headless executor. State/logs
stay under .git, not in course materials or student-visible paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_REMOTE = "gaolingxi/python"
SCHEDULE_NAME = "Python-Course-Orca-Chat-Checker-10min"
TASK_FILE = "OPENCODE_TASK.md"
REPORT_FILE = "OPENCODE_REPORT.md"
RUNTIME_DIR = "python-course-orca-chat-checker"
WINDOWS_CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


class CheckerFailure(RuntimeError):
    pass


def execute(args: list[str], *, cwd: Path = ROOT, timeout: int = 50) -> str:
    proc = subprocess.run(
        args, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=timeout, shell=False,
        creationflags=WINDOWS_CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    output = proc.stdout.decode("utf-8-sig", errors="replace").strip()
    if proc.returncode != 0:
        reason = proc.stderr.decode("utf-8-sig", errors="replace").strip()
        raise CheckerFailure(f"EXIT_{proc.returncode}: {' '.join(args[:3])}: {reason[-500:]}")
    return output


def git(*args: str, cwd: Path = ROOT, timeout: int = 50) -> str:
    return execute(["git", "-C", str(cwd), *args], cwd=cwd, timeout=timeout)


def runtime_dir(repo: Path) -> Path:
    common = git("rev-parse", "--git-common-dir", cwd=repo)
    p = Path(common)
    if not p.is_absolute():
        p = repo / p
    return p.resolve() / RUNTIME_DIR


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        return default
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise CheckerFailure("INVALID_CHECKER_STATE")
    return obj


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(repo: Path, status: str, **fields: Any) -> None:
    log = runtime_dir(repo) / "events.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "status": status, **fields},
                           ensure_ascii=False) + "\n")


def origin_is_expected(remote: str) -> bool:
    v = remote.strip().replace("\\", "/").lower().removesuffix(".git")
    return bool(re.fullmatch(r"(https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
                             + re.escape(EXPECTED_REMOTE), v))


def fields(text: str) -> dict[str, str]:
    return dict((k.upper(), v.strip()) for k, v in
                re.findall(r"(?m)^([A-Z][A-Z_0-9]*)\s*:\s*([^\r\n]+)", text))


def remote_text(repo: Path, ref: str, path: str) -> str:
    try:
        return git("show", f"{ref}:{path}", cwd=repo)
    except CheckerFailure:
        return ""


def snapshot(repo: Path) -> dict[str, str]:
    if git("branch", "--show-current", cwd=repo) != "main":
        raise CheckerFailure("WRONG_BRANCH_MAIN_REQUIRED")
    if not origin_is_expected(git("remote", "get-url", "origin", cwd=repo)):
        raise CheckerFailure("WRONG_GITHUB_REMOTE")
    git("fetch", "--no-tags", "origin", "main", cwd=repo, timeout=80)
    ref = "origin/main"
    text = remote_text(repo, ref, TASK_FILE)
    if not text:
        raise CheckerFailure("REMOTE_TASK_FILE_MISSING")
    meta = fields(text)
    report = fields(remote_text(repo, ref, REPORT_FILE))
    task_id = meta.get("TASK_ID", "")
    return {
        "task_id": task_id,
        "status": meta.get("STATUS", "").upper(),
        "executor": meta.get("EXECUTOR", "").upper(),
        "next_actor": meta.get("NEXT_ACTOR", "").upper(),
        "automation_ready": meta.get("AUTOMATION_READY", "").upper(),
        "user_review_required": meta.get("USER_REVIEW_REQUIRED", "").upper(),
        "report_task_id": report.get("TASK_ID", ""),
        "report_status": report.get("STATUS", "").upper(),
        "task_blob": git("rev-parse", f"{ref}:{TASK_FILE}", cwd=repo),
        "remote_head": git("rev-parse", ref, cwd=repo),
    }


def decision(s: dict[str, str]) -> str:
    if s["task_id"] in ("", "NONE"):
        return "IDLE_NO_TASK"
    if s["status"] not in ("READY", "PENDING"):
        return "IDLE_NOT_READY"
    if s["executor"] != "OPENCODE" or s["next_actor"] != "OPENCODE":
        return "IDLE_NOT_ASSIGNED"
    if s["automation_ready"] != "YES":
        return "IDLE_AUTOMATION_NOT_APPROVED"
    if s["user_review_required"] in ("YES", "TRUE", "1"):
        return "IDLE_USER_REVIEW_REQUIRED"
    if (s["report_task_id"] == s["task_id"]
            and s["report_status"] in ("DONE", "BLOCKED", "FAILED", "CANCELLED")):
        return "IDLE_ALREADY_REPORTED"
    return "ELIGIBLE"


def orca_command() -> list[str]:
    node = shutil.which("node")
    local = os.environ.get("LOCALAPPDATA")
    if node and local:
        js = (Path(local) / "Programs" / "orca" / "resources" /
              "app.asar.unpacked" / "out" / "cli" / "index.js")
        if js.is_file():
            return [node, str(js)]
    exe = shutil.which("orca")
    if exe:
        return [exe]
    raise CheckerFailure("ORCA_CLI_NOT_FOUND")


def orca(repo: Path, args: list[str], timeout: int = 35) -> dict[str, Any]:
    output = execute([*orca_command(), *args, "--json"], cwd=repo, timeout=timeout)
    try:
        parsed = json.loads(output)
    except ValueError as exc:
        raise CheckerFailure("ORCA_JSON_BAD_OUTPUT") from exc
    if not isinstance(parsed, dict) or parsed.get("ok") is not True:
        raise CheckerFailure("ORCA_RUNTIME_NOT_READY")
    return parsed.get("result") or {}


def registered_workspace(repo: Path) -> None:
    result = orca(repo, ["worktree", "show", "--worktree", f"path:{repo}"])
    w = result.get("worktree")
    if not isinstance(w, dict):
        raise CheckerFailure("ORCA_WORKTREE_UNREGISTERED")
    path = w.get("path")
    if not isinstance(path, str) or os.path.normcase(
        os.path.abspath(path)
    ) != os.path.normcase(os.path.abspath(str(repo))):
        raise CheckerFailure("ORCA_WORKTREE_PATH_MISMATCH")
    if str(w.get("projectId") or "").lower() != "github:gaolingxi/python":
        raise CheckerFailure("ORCA_PROJECT_ID_MISMATCH")


def launch_chat(repo: Path, task_id: str) -> dict[str, str]:
    prompt = (
        "继续。只领取 GitHub gaolingxi/python 的最新任务 TASK_ID=" + task_id
        + "。先安全 git pull --ff-only，核对 AGENTS.md、OPENCODE_TASK.md、"
          "AUTOMATION_READY 与 NEXT_ACTOR；任务已完成、发生冲突或需人工审核时停止。"
          "不得覆盖教师答案或学生成绩，不要重跑旧任务。"
    )
    result = orca(repo, [
        "agent", "launch", "--agent", "opencode",
        "--worktree", f"path:{repo}", "--surface", "chat", "--prompt", prompt,
    ], timeout=60)
    kind = str((result.get("outcome") or {}).get("kind") or "")
    if "chat" not in kind.lower():
        raise CheckerFailure(f"ORCA_NOT_NATIVE_CHAT: {kind or 'UNKNOWN'}")
    return {"chat_outcome": kind, "session_id": str(result.get("sessionId") or "")}


def check_once(repo: Path = ROOT, *, check_only: bool = False, doctor: bool = False) -> dict[str, Any]:
    repo = repo.resolve()
    snap = snapshot(repo)
    outcome = decision(snap)
    if doctor:
        registered_workspace(repo)
        return {"status": "DOCTOR_READY", "mode": "ORCA_NATIVE_CHAT",
                "task_id": snap["task_id"], "task_decision": outcome}
    if check_only:
        return {"status": "CHECK_ONLY", "task_id": snap["task_id"],
                "task_decision": outcome, "would_launch_chat": outcome == "ELIGIBLE"}
    folder = runtime_dir(repo)
    folder.mkdir(parents=True, exist_ok=True)
    lock = folder / "checker.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return {"status": "CHECKER_BUSY"}
    try:
        os.close(fd)
        state_path = folder / "state.json"
        state = read_json(state_path, {"version": 1, "launched": {}})
        # First run is a non-executing migration fence, even if the remote
        # already contains a READY task that may have been handled in Chat.
        if "baseline_task_id" not in state:
            state["baseline_task_id"] = snap["task_id"]
            state["baseline_at"] = now()
            atomic_json(state_path, state)
            log_event(repo, "BASELINE_SET_NO_EXECUTION", task_id=snap["task_id"])
            return {"status": "BASELINE_SET_NO_EXECUTION", "task_id": snap["task_id"]}
        if snap["task_id"] == state["baseline_task_id"]:
            return {"status": "BASELINE_TASK_SKIPPED", "task_id": snap["task_id"]}
        if outcome != "ELIGIBLE":
            return {"status": outcome, "task_id": snap["task_id"]}
        launched = state.setdefault("launched", {})
        if snap["task_id"] in launched:
            return {"status": "ALREADY_CLAIMED_OR_UNCONFIRMED",
                    "task_id": snap["task_id"],
                    "claim_status": launched[snap["task_id"]]["status"]}
        registered_workspace(repo)
        # Reserve on disk BEFORE side effects. Transport errors are ambiguous.
        launched[snap["task_id"]] = {
            "status": "LAUNCH_UNCONFIRMED", "reserved_at": now(),
            "task_blob": snap["task_blob"], "remote_head": snap["remote_head"],
        }
        atomic_json(state_path, state)
        try:
            result = launch_chat(repo, snap["task_id"])
        except Exception as exc:
            log_event(repo, "CHAT_LAUNCH_UNCONFIRMED", task_id=snap["task_id"],
                      error=str(exc))
            raise
        launched[snap["task_id"]].update(
            status="CHAT_LAUNCHED", delivered_at=now(), **result,
        )
        atomic_json(state_path, state)
        log_event(repo, "CHAT_LAUNCHED", task_id=snap["task_id"], **result)
        return {"status": "CHAT_LAUNCHED", "task_id": snap["task_id"], **result}
    finally:
        lock.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = check_once(ROOT, check_only=args.check, doctor=args.doctor)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        try:
            log_event(ROOT, "CHECKER_ERROR", error=repr(exc))
        except Exception:
            pass
        print(json.dumps({"status": "CHECKER_ERROR", "reason": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
