#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Only send to an EXISTING Orca OpenCode Chat; never launch a new tab."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import subprocess

class ChatUnavailable(RuntimeError):
    pass

class ChatDeliveryUnconfirmed(RuntimeError):
    pass

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

def _cmd():
    node = shutil.which("node")
    appdata = os.getenv("LOCALAPPDATA")
    if not node or not appdata:
        raise ChatUnavailable("WAIT_ORCA_CHAT_CLI")
    js = Path(appdata) / "Programs/orca/resources/app.asar.unpacked/out/cli/index.js"
    if not js.is_file():
        raise ChatUnavailable("WAIT_ORCA_CHAT_CLI")
    return [node, str(js)]

def _run(repo, parts, *, input_bytes=None, timeout=40):
    try:
        p = subprocess.run([*_cmd(), *parts, "--json"], cwd=str(repo),
                           input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout,
                           creationflags=CREATE_NO_WINDOW if os.name=="nt" else 0)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ChatDeliveryUnconfirmed("ORCA_CHAT_TRANSPORT_UNCERTAIN") from exc
    if p.returncode:
        raise ChatDeliveryUnconfirmed("ORCA_CHAT_CLI_RETURNED_ERROR")
    try:
        obj=json.loads(p.stdout.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise ChatDeliveryUnconfirmed("ORCA_CHAT_MALFORMED_RESULT") from exc
    if not isinstance(obj, dict) or obj.get("ok") is not True:
        raise ChatDeliveryUnconfirmed("ORCA_CHAT_RESULT_ERROR")
    return obj.get("result") or {}

def supported():
    try:
        p=subprocess.run([*_cmd(),"chat","--help"],capture_output=True,timeout=15,
                         creationflags=CREATE_NO_WINDOW if os.name=="nt" else 0)
    except (OSError, subprocess.TimeoutExpired, ChatUnavailable):
        return False
    lines=p.stdout.decode("utf-8",errors="replace").splitlines()
    commands={x.strip().split()[0] for x in lines if x.startswith("  ") and x.strip()}
    return p.returncode == 0 and {"list","send"}.issubset(commands)

def _gitdir(repo):
    p=subprocess.run(["git","-C",str(repo),"rev-parse","--git-common-dir"],
                     capture_output=True,timeout=15)
    if p.returncode:
        raise ChatUnavailable("GIT_COMMON_DIR_UNAVAILABLE")
    path=Path(p.stdout.decode("utf-8-sig").strip())
    return (path if path.is_absolute() else repo/path).resolve()

def _pin(repo):
    return _gitdir(repo)/"orca-single-chat-session.json"

def _field(row, *names):
    for key in names:
        v=row.get(key)
        if isinstance(v,str) and v.strip():
            return v.strip()
    return ""

def prepare(repo, workspace):
    repo, workspace=Path(repo).resolve(), Path(workspace).resolve()
    if not supported():
        raise ChatUnavailable("WAIT_ORCA_VERSION_WITH_CHAT_SEND")
    result=_run(repo,["chat","list","--worktree",f"path:{workspace}"])
    rows=next((result[k] for k in ("chats","sessions","items","rows")
               if isinstance(result.get(k),list)),None)
    if rows is None:
        raise ChatUnavailable("CHAT_LIST_SCHEMA_UNKNOWN")
    options=[]
    target=os.path.normcase(os.path.normpath(str(workspace)))
    for r in rows:
        if not isinstance(r,dict):
            continue
        if _field(r,"agentType","agent","agentId").lower() not in ("opencode","opencode2"):
            continue
        path=_field(r,"worktreePath","workspacePath","path")
        if path and os.path.normcase(os.path.normpath(path)) != target:
            continue
        session=_field(r,"sessionId","session_id","handle","session","id")
        if session:
            options.append((session,r))
    if not options:
        raise ChatUnavailable("WAIT_NO_EXISTING_CHAT")
    pin=_pin(repo)
    if pin.is_file():
        try:
            saved=json.loads(pin.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            raise ChatUnavailable("PIN_STATE_INVALID") from exc
        if str(saved.get("workspace","")).lower() != str(workspace).lower():
            raise ChatUnavailable("PIN_WORKSPACE_MISMATCH")
        chosen=next((v for v in options if v[0]==saved.get("session_id")),None)
        if not chosen:
            raise ChatUnavailable("PINNED_CHAT_MISSING_DO_NOT_CREATE")
    else:
        options.sort(key=lambda v:str(v[1].get("updatedAt") or v[1].get("lastActivityAt") or ""),reverse=True)
        if len(options)>1 and not (options[0][1].get("updatedAt") or options[0][1].get("lastActivityAt")):
            raise ChatUnavailable("MULTIPLE_CHATS_REQUIRE_PIN")
        chosen=options[0]
    status=_field(chosen[1],"state","status","agentState").lower()
    if status not in ("done","idle","completed","inactive"):
        raise ChatUnavailable("WAIT_CHAT_NOT_IDLE_"+(status or "UNKNOWN"))
    return {"session_id":chosen[0],"workspace":str(workspace)}

def send(repo, prepared, message):
    if not supported():
        raise ChatUnavailable("WAIT_ORCA_VERSION_WITH_CHAT_SEND")
    result=_run(Path(repo).resolve(),
                ["chat","send","--session",prepared["session_id"],"--text-file","-"],
                input_bytes=message.encode("utf-8"),timeout=65)
    def status(obj):
        if isinstance(obj,str):
            return obj.lower() if obj.lower() in ("submitted","queued") else ""
        if isinstance(obj,dict):
            if obj.get("submitted") is True:return "submitted"
            if obj.get("queued") is True:return "queued"
            for key in ("status","delivery","send","result","state","admission"):
                if key in obj:
                    v=status(obj[key])
                    if v:return v
        return ""
    receipt=status(result)
    if not receipt:
        raise ChatDeliveryUnconfirmed("ORCA_CHAT_SEND_NOT_ACKNOWLEDGED")
    pin=_pin(Path(repo).resolve())
    if not pin.exists():
        tmp=pin.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(prepared,ensure_ascii=False)+"\n",encoding="utf-8")
        os.replace(tmp,pin)
    return {"chat_outcome":"existing","session_id":prepared["session_id"],
            "chat_admission":receipt}


def main():
    """CLI adapter for Windows PowerShell checkers; safe before claim reservation."""
    import argparse
    import sys
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["prepare","send"])
    parser.add_argument("--repo",required=True)
    parser.add_argument("--workspace",required=True)
    parser.add_argument("--session")
    parser.add_argument("--prompt-file")
    args=parser.parse_args()
    try:
        if args.action=="prepare":
            value=prepare(Path(args.repo),Path(args.workspace))
            result={"status":"READY_EXISTING_CHAT",**value}
        else:
            if not args.session or not args.prompt_file:
                raise ChatUnavailable("SESSION_AND_PROMPT_FILE_REQUIRED")
            target={"session_id":args.session,"workspace":str(Path(args.workspace).resolve())}
            message=Path(args.prompt_file).read_text(encoding="utf-8-sig")
            sent=send(Path(args.repo),target,message)
            result={"status":"EXISTING_CHAT_MESSAGED",**sent}
        print(json.dumps(result,ensure_ascii=False))
        return 0
    except ChatUnavailable as exc:
        print(json.dumps({"status":"WAIT_EXISTING_ORCA_CHAT","reason":str(exc)}))
        return 2
    except ChatDeliveryUnconfirmed as exc:
        print(json.dumps({"status":"CHAT_SEND_UNCONFIRMED","reason":str(exc)}))
        return 3

if __name__=="__main__":
    raise SystemExit(main())
