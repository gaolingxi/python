#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compatibility adapter: send new GitHub tasks to one PINNED OpenCode TUI.

No Orca agent launch, no Chat creation, no terminal creation in the checker.
One-time terminal provisioning is explicitly outside this polling helper.
All binding state stays in the Git common directory. A dead, orphaned or
replaced terminal is NOT silently rebound; user must re-provision deliberately.

The historical public import name is kept for compatibility with existing
project-specific checker task gates; prepare()/send() now use Orca terminals.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

class ChatUnavailable(RuntimeError):
    """No verified, idle, fixed OpenCode terminal; do not reserve/claim task."""

class ChatDeliveryUnconfirmed(RuntimeError):
    """A send was attempted; a retry could duplicate an execution."""

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
PIN_NAME = "opencode-fixed-terminal-binding.json"


def _norm(value):
    return os.path.normcase(os.path.normpath(str(value or ""))).rstrip("\\/")


def _cmd():
    node = shutil.which("node")
    appdata = os.getenv("LOCALAPPDATA")
    if not node or not appdata:
        raise ChatUnavailable("WAIT_ORCA_CLI_UNAVAILABLE")
    js = Path(appdata) / "Programs/orca/resources/app.asar.unpacked/out/cli/index.js"
    if not js.is_file():
        raise ChatUnavailable("WAIT_ORCA_CLI_UNAVAILABLE")
    return [node, str(js)]


def _run(repo, parts, *, timeout=35, delivery=False):
    try:
        p = subprocess.run(
            [*_cmd(), *parts, "--json"],
            cwd=str(repo),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=False,
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        obj = json.loads(p.stdout.decode("utf-8-sig"))
    except (OSError, subprocess.TimeoutExpired, UnicodeError, ValueError) as exc:
        error = ChatDeliveryUnconfirmed if delivery else ChatUnavailable
        raise error("ORCA_TERMINAL_TRANSPORT_UNCONFIRMED") from exc
    if p.returncode != 0 or not isinstance(obj, dict) or obj.get("ok") is not True:
        error_obj = obj.get("error") if isinstance(obj, dict) else {}
        code = str((error_obj or {}).get("code") or "FAILED")
        if not delivery and code in {"timeout", "not_ready", "terminal_busy"}:
            raise ChatUnavailable("WAIT_FIXED_OPENCODE_TERMINAL_IDLE")
        error = ChatDeliveryUnconfirmed if delivery else ChatUnavailable
        raise error("ORCA_FIXED_TERMINAL_"+code[:80])
    return obj.get("result") or {}


def _gitdir(repo):
    p = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--git-common-dir"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    result = Path(p.stdout.decode("utf-8-sig").strip())
    if not result.is_absolute():
        result = Path(repo) / result
    return result.resolve()


def _pin(repo):
    return _gitdir(repo) / PIN_NAME


def _save_pin(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    if tmp.exists():
        raise ChatUnavailable("FIXED_TERMINAL_BINDING_WRITE_ALREADY_IN_PROGRESS")
    with tmp.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _show(repo, handle, workspace):
    result = _run(repo, ["terminal", "show", "--terminal", handle])
    term = result.get("terminal") or {}
    if (not isinstance(term, dict) or
        term.get("handle") != handle or
        not _norm(term.get("worktreePath")) == _norm(workspace) or
        term.get("agentIdentity") != "opencode" or
        term.get("connected") is not True or
        term.get("writable") is not True or
        term.get("orphaned") is True):
        raise ChatUnavailable("WAIT_FIXED_OPENCODE_TERMINAL_VALID")
    incarnation = term.get("incarnationId")
    if not isinstance(incarnation, str) or not incarnation:
        raise ChatUnavailable("WAIT_TERMINAL_INCARNATION_UNAVAILABLE")
    return term


def _idle(repo, handle):
    try:
        result = _run(repo, [
            "terminal", "wait", "--terminal", handle,
            "--for", "tui-idle", "--timeout-ms", "1200",
        ], timeout=12)
    except ChatUnavailable as exc:
        raise ChatUnavailable("WAIT_FIXED_OPENCODE_TERMINAL_IDLE") from exc
    if (result.get("wait") or {}).get("satisfied") is not True:
        raise ChatUnavailable("WAIT_FIXED_OPENCODE_TERMINAL_IDLE")


def prepare(repo, workspace):
    repo, workspace = Path(repo).resolve(), Path(workspace).resolve()
    path = _pin(repo)
    if path.exists():
        try:
            binding = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            raise ChatUnavailable("FIXED_TERMINAL_BINDING_CORRUPT") from exc
        if _norm(binding.get("workspace")) != _norm(workspace):
            raise ChatUnavailable("FIXED_TERMINAL_WRONG_WORKSPACE")
        handle = binding.get("handle", "")
        term = _show(repo, handle, workspace)
        if binding.get("incarnation_id") != term.get("incarnationId"):
            raise ChatUnavailable("FIXED_TERMINAL_CHANGED_REQUIRES_REBIND")
    else:
        listed = _run(repo, ["terminal", "list", "--worktree", f"path:{workspace}", "--limit", "100"])
        matches = []
        for candidate in listed.get("terminals") or []:
            if not isinstance(candidate, dict):
                continue
            handle = candidate.get("handle")
            if not isinstance(handle, str) or not handle.startswith("term_"):
                continue
            try:
                term = _show(repo, handle, workspace)
                matches.append(term)
            except ChatUnavailable:
                continue
        if not matches:
            raise ChatUnavailable("WAIT_FIXED_OPENCODE_TERMINAL_NOT_FOUND")
        if len(matches) != 1:
            raise ChatUnavailable("WAIT_FIXED_OPENCODE_TERMINAL_AMBIGUOUS")
        term = matches[0]
        binding = {
            "version": 1,
            "handle": term["handle"],
            "incarnation_id": term["incarnationId"],
            "workspace": str(workspace),
            "purpose": "one fixed OpenCode TUI per project; never auto launch",
        }
        _save_pin(path, binding)
        handle = binding["handle"]
    _idle(repo, handle)
    return {
        "session_id": handle,  # legacy bridge to old checker protocol
        "terminal_handle": handle,
        "incarnation_id": binding["incarnation_id"],
        "workspace": str(workspace),
        "mode": "FIXED_OPENCODE_TERMINAL",
    }


def send(repo, prepared, message):
    repo = Path(repo).resolve()
    workspace = Path(prepared["workspace"]).resolve()
    pin_path = _pin(repo)
    if not pin_path.exists():
        raise ChatDeliveryUnconfirmed("TERMINAL_BINDING_NOT_FOUND_BEFORE_SEND")
    saved = json.loads(pin_path.read_text(encoding="utf-8-sig"))
    handle = prepared.get("terminal_handle") or prepared.get("session_id")
    if (saved.get("handle") != handle or
        _norm(saved.get("workspace")) != _norm(workspace)):
        raise ChatDeliveryUnconfirmed("TERMINAL_HANDLE_CHANGED_DURING_DISPATCH")
    try:
        term = _show(repo, handle, workspace)
    except ChatUnavailable as exc:
        raise ChatDeliveryUnconfirmed("TERMINAL_LOST_BEFORE_SEND") from exc
    if saved.get("incarnation_id") != term.get("incarnationId"):
        raise ChatDeliveryUnconfirmed("TERMINAL_INCAR_CHANGED_DURING_DISPATCH")
    if not isinstance(message, str) or not message.strip():
        raise ChatDeliveryUnconfirmed("EMPTY_TASK_PROMPT")
    # Caller has already durably reserved this task: NEVER retry after error.
    result = _run(repo, [
        "terminal", "send", "--terminal", handle, "--text", message,
        "--enter", "--wait-submit", "5",
    ], timeout=25, delivery=True)
    receipt = result.get("send") or {}
    if not isinstance(receipt, dict) or receipt.get("accepted") is not True:
        raise ChatDeliveryUnconfirmed("TERMINAL_SEND_NOT_ACCEPTED_OR_UNCONFIRMED")
    return {
        "terminal_handle": handle,
        "session_id": handle,  # compatible with old status JSON
        "mode": "FIXED_OPENCODE_TERMINAL",
        "accepted": True,
        "turn_observed": receipt.get("submitted", receipt.get("turnStarted")),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "send"])
    parser.add_argument("--repo", required=True)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--session")
    parser.add_argument("--prompt-file")
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            value = prepare(Path(args.repo), Path(args.workspace))
            result = {"status": "READY_FIXED_TERMINAL", **value}
        else:
            if not args.session or not args.prompt_file:
                raise ChatUnavailable("HANDLE_AND_PROMPT_FILE_REQUIRED")
            target = {"session_id": args.session, "workspace": args.workspace}
            content = Path(args.prompt_file).read_text(encoding="utf-8-sig")
            delivered = send(Path(args.repo), target, content)
            # Old PowerShell consumer expects this literal status.
            result = {"status": "EXISTING_CHAT_MESSAGED", **delivered}
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except ChatUnavailable as exc:
        print(json.dumps({"status": "WAIT_FIXED_TERMINAL", "reason": str(exc)}, ensure_ascii=False))
        return 2
    except ChatDeliveryUnconfirmed as exc:
        print(json.dumps({"status": "TERMINAL_SEND_UNCONFIRMED", "reason": str(exc)}, ensure_ascii=False))
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
