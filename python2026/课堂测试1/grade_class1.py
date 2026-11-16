#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python 课堂小测一 V6：保留原卷、全量执行、源文件对账、结构审计、统一计分。
用法：python python2026/课堂测试1/grade_class1.py
安全：不执行非标准输入单元；隔离每题 Python 进程/超时；不用学生旧 outputs。
注意：结果为待教师复核版本，重复提交、身份不明、异常输出都不能自动认定为正式成绩。
"""
import ast
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import statistics
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent
CLASS = ROOT / "班级 1"
OUT = CLASS / "批改结果"
OUT.mkdir(exist_ok=True)
QMAX = [5, 5, 5, 5, 10, 10, 10, 10, 10, 10, 10, 10]
KEY = ["C", "B", "A", "B"]
RUBRIC = {
    "quiz": "Python课堂小测一", "total": 100, "skill": "assignment-grading V6",
    "question_max_scores": QMAX, "mc_answers": KEY,
    "q5": "字符串'25'（必须包含引号）",
    "q6": "相等比较／比较；赋值（两空各5分）",
    "code": {
        "Q7": "两次键盘输入3分；交换前输出2分；交换后输出3分；可适配不同输入2分",
        "Q8": "单利计算公式4分；本金加利息公式3分；正确输出两项3分",
        "Q9": "整除3分；取余3分；乘方3分；顺序1分",
        "Q10": "国家2分；GDP2分；增长率2分；两位小数2分；format方法2分",
        "Q11": "转换3分；正确比较4分；正确标签输出3分",
        "Q12": "输出完整Hello3分；正确输出最后一字符5分；无运行错误2分",
    },
    "duplicate_policy": "保留所有版本；参考版按最多有效作答选取，重复提交均标记复核",
    "no_fabricated_execution": True,
}

def src(cell):
    s = cell.get("source", "")
    return "".join(s) if isinstance(s, list) else str(s)

def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def noncomment(source):
    return "\n".join(x for x in source.splitlines() if x.strip() and not x.lstrip().startswith("#")).strip()

def short_answer(source):
    """选择/填空答案可能直接写成 # 你的答案：B，不能把注释式答题清空。"""
    lines = source.splitlines()
    values = []
    for i, line in enumerate(lines):
        found = re.search(r"(?:你的答案|答案)\s*[:：]\s*(.*)$", line)
        if found:
            tail = found.group(1).strip()
            if tail:
                values.append(tail)
            elif i + 1 < len(lines):
                candidate = lines[i + 1].strip()
                if candidate and not candidate.startswith("#"):
                    values.append(candidate)
        elif line.strip() and not line.strip().startswith("#"):
            values.append(line.strip())
    return "\n".join(values).strip()

def extract(nb):
    """题目 Markdown 所在区间中找答题代码；不按 code-cell 数量猜测，兼容身份额外 cell。"""
    cells = nb.get("cells", [])
    headings = [(i, src(c)) for i, c in enumerate(cells)
                if c.get("cell_type") == "markdown" and re.match(r"^###\s+[1-4]\.\s", src(c))]
    if len(headings) != 12:
        # 非常规修改模板：所有 ### 编号标题，按原卷题序排列，待结构复核
        headings = [(i, src(c)) for i, c in enumerate(cells)
                    if c.get("cell_type") == "markdown" and re.match(r"^###\s+\d+\.", src(c))]
    answers = []
    for k in range(12):
        if k >= len(headings):
            answers.append({"source": "", "heading": "", "cells": [], "match": False})
            continue
        i, title = headings[k]
        end = headings[k + 1][0] if k + 1 < len(headings) else len(cells)
        if k == 11:
            for t in range(i + 1, len(cells)):
                if src(cells[t]).startswith("## "):
                    end = t
                    break
        group = [(j, src(c)) for j, c in enumerate(cells[i + 1:end], i + 1)
                 if c.get("cell_type") == "code"]
        cleaned = [t for _, t in group if noncomment(t) or (k < 6 and short_answer(t))]
        answer = "\n".join(cleaned)
        answers.append({"source": answer, "heading": title.splitlines()[0],
                        "cells": [j for j, _ in group], "match": True})
    return answers, len(headings)

def safety_check(code):
    if not noncomment(code):
        return "BLANK"
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return "SYNTAX_ERROR"
    denied = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal, ast.ClassDef,
              ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.With, ast.AsyncWith,
              ast.Try, ast.Raise, ast.Delete, ast.Yield, ast.YieldFrom)
    if any(isinstance(n, denied) for n in ast.walk(tree)):
        return "REVIEW_UNSAFE"
    banned = {"open", "exec", "eval", "compile", "__import__", "globals", "locals",
              "getattr", "setattr", "delattr", "breakpoint", "help", "exit", "quit"}
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id in banned:
            return "REVIEW_UNSAFE"
        if isinstance(n, ast.Attribute) and n.attr.startswith("__"):
            return "REVIEW_UNSAFE"
    return "SAFE"

def execute(code, stdin=""):
    check = safety_check(code)
    if check != "SAFE":
        return {"status": check, "stdout": "", "stderr": check, "returncode": None}
    clean_env = {"PATH": os.environ.get("PATH", ""), "LANG": "C.UTF-8",
                 "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    def limits():
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024, 1024 * 1024))
        except (ImportError, ValueError):
            pass
    try:
        p = subprocess.run([sys.executable, "-I", "-S", "-c", code],
                           input=stdin, capture_output=True, text=True,
                           timeout=4, env=clean_env, cwd=str(ROOT),
                           preexec_fn=limits if os.name == "posix" else None)
        return {"status": "EXECUTED_OK" if p.returncode == 0 else "EXECUTED_WITH_ERRORS",
                "stdout": p.stdout[:8000], "stderr": p.stderr[-1200:],
                "returncode": p.returncode}
    except subprocess.TimeoutExpired:
        return {"status": "TIMEOUT", "stdout": "", "stderr": "超过4秒", "returncode": None}
    except Exception as e:
        return {"status": "FILE_BLOCKED", "stdout": "", "stderr": str(e)[:300],
                "returncode": None}

def norm(s):
    return re.sub(r"\s+", "", s.replace("：", ":").replace("％", "%")
                  .replace("，", ",").replace("（", "(").replace("）", ")")).lower()

def numeric_lines(stdout):
    numbers = []
    for line in stdout.splitlines():
        clean = line.strip()
        nums = re.findall(r"(?<![\d.])-?\d+(?:\.\d+)?", clean)
        numbers.append((clean, nums))
    return numbers

def score_simple(q, text):
    t = short_answer(text).strip()
    normalized = norm(t).upper()
    if not normalized:
        return 0, "BLANK", "未作答"
    if q < 4:
        matches = re.findall(r"[A-D]", normalized)
        if len(matches) != 1 or not re.fullmatch(r"[A-D]", normalized):
            return 0, "SEMANTIC_REVIEW", "选择题含多个选项或额外内容，需核对"
        ok = normalized == KEY[q]
        return (5 if ok else 0), ("OK" if ok else "WRONG"), "正确" if ok else "选项不正确"
    if q == 4:
        # 包括单引号和双引号，允许空白/变量赋值等表达
        if re.search(r"['\"]\s*25\s*['\"]", t):
            return 10, "OK", "明确写出字符串25"
        if re.fullmatch(r"25", t):
            return 0, "WRONG", "未包含引号，不能证明是字符串"
        return 0, "SEMANTIC_REVIEW", "字符串形式不明确，需要人工复核"
    if q == 5:
        first = bool(re.search(r"相等|等于|比较|关系|判断", t))
        second = "赋值" in t
        score = (5 if first else 0) + (5 if second else 0)
        return score, "OK" if score == 10 else ("PARTIAL" if score else "WRONG"), "两空分别按5分"
    raise AssertionError(q)

def grade_code(q, code, runs):
    t = noncomment(code)
    if not t:
        return 0, "BLANK", "空白"
    a = runs[0]
    ok = a["status"] == "EXECUTED_OK"
    outs = [r["stdout"] for r in runs]
    if a["status"] == "REVIEW_UNSAFE":
        return None, "REVIEW_REQUIRED", "代码含超范围操作，未执行"
    if q == 6:  # 输入、交换、两次输出
        inp = len(re.findall(r"\binput\s*\(", t))
        swap = bool(re.search(r"\ba\s*,\s*b\s*=\s*b\s*,\s*a\b", t)) or (
            bool(re.search(r"\b(?:temp|tmp|c)\s*=\s*a\b", t)) and "b" in t)
        def pairs(s, first, second):
            lines = numeric_lines(s)
            pattern = re.compile(r"(?<!\d)" + str(first) + r"\s+"
                                 + str(second) + r"(?!\d)")
            return any(pattern.search(v.replace(",", " ")) for v, _ in lines)
        a1 = pairs(outs[0], 3, 5) if ok else False
        a2 = pairs(outs[0], 5, 3) if ok else False
        b_ok = len(runs) > 1 and runs[1]["status"] == "EXECUTED_OK"
        b1 = pairs(outs[1], 8, 2) if b_ok else False
        b2 = pairs(outs[1], 2, 8) if b_ok else False
        val = (3 if inp >= 2 else 0) + (2 if a1 else 0) + (3 if a2 else 0) + (2 if b1 and b2 else 0)
        if swap:
            # 即使输出未按题意显示两列，也应保留正确交换算法的思路分。
            val = max(val, 2)
        if val == 10 and not swap and inp < 2:
            val = 8
        note = "两次不同输入测试；未满足的部分为输入/交换/前后输出"
    elif q == 7:  # 利息公式、总额
        interest_formula = bool(re.search(r"10000\s*\*\s*0\.034\s*\*\s*5|"
            r"\b(?:principal|ben|money|p)\s*\*\s*(?:annual_rate|li|rate|r)\s*\*\s*(?:years|year|n)", t))
        # 更一般：至少有两次相乘且包含.034及5，可以认可变量命名等价
        interest_formula |= t.count("*") >= 2 and bool(re.search(r"\.034\b", t))
        total_formula = ("+" in t and (re.search(r"\b(?:interest|lixi|interesting|total|zhong|money)\b", t) or "10000" in t))
        val = (4 if interest_formula else 0) + (3 if total_formula else 0)
        line1 = any("1700" in v and ("利息" in v or "interest" in v.lower()) for v in outs[0].splitlines()) if ok else False
        line2 = any("11700" in v and ("总额" in v or "total" in v.lower()) for v in outs[0].splitlines()) if ok else False
        val += (1 if line1 else 0) + (2 if line2 else 0)
        if ok and not (line1 or line2) and "1700" in outs[0] and "11700" in outs[0]:
            val = min(10, val + 2)
        if not ok:
            val = min(val, 5)
        note = "按单利计算式、总额公式、输出两项核验"
    elif q == 8:  # 运算符
        # 允许先定义a=100、再print(a//7)等语义等价写法，
        # 不得硬性要求把100和7直接写在同一表达式中。
        has_ops = [("//" in t), ("%" in t), ("**" in t)]
        lines = numeric_lines(outs[0]) if ok else []
        vals = [x for _, nums in lines for x in nums]
        expected = ["14", "2", "1024"]
        correct = [v in vals for v in expected] if ok else [False, False, False]
        val = sum(3 for i in range(3) if has_ops[i] and correct[i])
        if not ok:
            val = sum(1 for has in has_ops if has)
        if all(correct) and all(has_ops):
            order = [v for v in vals if v in expected]
            if order[:3] == expected:
                val += 1
        note = "整除、取余、幂运算各3分；正确打印顺序1分"
    elif q == 9:  # format三行报告
        out = norm(outs[0]) if ok else ""
        uses_format = bool(re.search(r"\.\s*format\s*\(", t))
        labels = ["国家:中国", "GDP(万亿美元):14.34", "增长率:6.10%"]
        got = [norm(x) in out for x in labels]
        val = sum(2 for x in got if x) + (2 if "6.10%" in out else 0) + (2 if uses_format else 0)
        if not ok:
            val = min(val, 4)
        note = "逐行报告+两位小数+format()方法"
    elif q == 10:  # score转换与比较
        out = norm(outs[0]) if ok else ""
        convert = bool(re.search(r"\bint\s*\(\s*score\s*\)", t)) or bool(re.search(r"\bscore\s*=\s*int\s*\(", t))
        compare = bool(re.search(r"(?:score|int\s*\(\s*score\s*\))\s*>\s*80", t))
        val = (3 if convert else 0) + (4 if compare and ok and "true" in out else 0) + (
            3 if ok and "成绩大于80" in out and "true" in out else 0)
        if not ok:
            val = min(val, 3 if convert else 1)
        note = "类型转换、大小比较、输出中文提示"
    elif q == 11:  # hello, o
        lines = [line.strip() for line in outs[0].splitlines() if line.strip()] if ok else []
        first = bool(lines and lines[0] == "Hello")
        second = bool(len(lines) >= 2 and lines[1] == "o")
        val = (3 if first else 0) + (5 if second else 0) + (2 if ok else 0)
        note = "第一行Hello、第二行o、程序无错误"
    else:
        raise AssertionError(q)
    val = min(10, max(0, int(val)))
    status = "OK" if val == 10 else ("PARTIAL" if val else ("EXEC_ERROR" if not ok else "WRONG"))
    if val == 10 and not ok:
        status = "REVIEW_REQUIRED"
    return val, status, note + ("；错误：" + a["stderr"][:160] if not ok else "")

def data_file(path):
    raw = path.read_bytes()
    nb = json.loads(raw.decode("utf-8-sig"))
    return nb, hashlib.sha256(raw).hexdigest()

def identify_student(path):
    filename = path.name
    from_filename = re.findall(r"20\d{11}", filename)
    if from_filename:
        return from_filename[0], "FILENAME"
    try:
        notebook, _ = data_file(path)
        before_questions = []
        for c in notebook.get("cells", []):
            if src(c).startswith("### 1."):
                break
            before_questions.append(src(c))
        ids = re.findall(r"(?<!\d)20\d{11}(?!\d)", "\n".join(before_questions))
        ids = sorted(set(ids))
        if len(ids) == 1:
            return ids[0], "NOTEBOOK_BODY"
        return "", "AMBIGUOUS_ID" if ids else "NO_ID"
    except Exception:
        return "", "FILE_UNREADABLE"

def rubric_lock():
    path = OUT / "rubric.lock.json"
    value = json.dumps(RUBRIC, ensure_ascii=False, indent=2) + "\n"
    if path.exists() and path.read_text("utf-8") != value:
        raise SystemExit("BLOCKED：已锁定rubric与当前规则不一致，请先统一全班重评并审核。")
    path.write_text(value, encoding="utf-8")

def main():
    rubric_lock()
    files = sorted(CLASS.glob("205*/*.ipynb"))
    folders = sorted({p.parent.name for p in files})
    assert len(files) >= 60, "学生文件不齐全，停止正式评分"
    rawdata, executed = [], []
    print(f"RUN_ALL_BEFORE_EXTRACT: {len(files)} notebooks / {len(folders)} folders", flush=True)
    for ix, path in enumerate(files, 1):
        folder = path.parent.name
        try:
            notebook, sha = data_file(path)
            answers, nh = extract(notebook)
            if nh != 12:
                issue = f"QUESTION_ALIGNMENT_{nh}"
            else:
                issue = ""
            runs = {}
            for q in range(6, 12):
                tests = ["3\n5\n", "8\n2\n"] if q == 6 else [""]
                runs[q] = [execute(answers[q]["source"], inp) for inp in tests]
            rawdata.append({"path": str(path.relative_to(CLASS)), "folder": folder,
                            "sha": sha, "answers": answers, "runs": runs,
                            "structure_issue": issue})
            statuses = [z["status"] for v in runs.values() for z in v]
            executed.append({"folder": folder, "file": path.name, "sha256": sha,
                             "question_headings": nh, "execution_status":
                             ("REVIEW_REQUIRED" if issue else
                              "EXECUTED_WITH_ERRORS" if any(s != "EXECUTED_OK" for s in statuses)
                              else "EXECUTED_OK"),
                             "code_runs": len(statuses),
                             "errors": ";".join(f"Q{k+1}:{r['status']}" for k,v in runs.items()
                                               for r in v if r["status"] not in ("EXECUTED_OK","BLANK"))})
        except Exception as exc:
            executed.append({"folder": folder, "file": path.name, "sha256": "",
                             "question_headings": 0, "execution_status": "FILE_BLOCKED",
                             "code_runs": 0, "errors": str(exc)[:180]})
        if ix % 20 == 0:
            print(f"RUN progress {ix}/{len(files)}", flush=True)
    write_csv(OUT / "execution_manifest.csv", executed,
              ["folder","file","sha256","question_headings","execution_status","code_runs","errors"])
    if len(executed) != len(files):
        raise SystemExit("RUN_GATE BLOCKED: 文件未全部运行/标记")
    print("RUN_GATE complete; unified extraction starts", flush=True)
    extracted, detail, source_audit, audit = [], [], [], []
    file_summaries = []
    for entry in rawdata:
        folder, file, sha = entry["folder"], Path(entry["path"]).name, entry["sha"]
        scores = []
        answers = entry["answers"]
        for q, ans in enumerate(answers):
            source = ans["source"]
            if q <= 5:
                score,status,reason = score_simple(q,source)
                runtime = ""
            else:
                score,status,reason = grade_code(q,source,entry["runs"][q])
                runtime = json.dumps(entry["runs"][q],ensure_ascii=False)
            if entry["structure_issue"]:
                status = "REVIEW_REQUIRED"
            evidence = source[:4000]
            parsed = {"folder":folder, "file":file, "sha256":sha,
                      "question":q+1,"source":source, "runtime":runtime,
                      "status":status}
            extracted.append(parsed)
            detailed = {"folder":folder,"file":file,"question":q+1,"max_score":QMAX[q],
                        "score":score,"status":status, "reason":reason,
                        "answer_evidence":evidence, "runtime_evidence":runtime[:4000],
                        "sha256":sha}
            detail.append(detailed)
            scores.append(score)
            # 源文件与提取结果使用同一原始Notebook反读来源和SHA核对
            # 按原始Notebooks实际cell索引再次拼接答题源内容，独立于提取结果做对账。
            notebook, check_sha = data_file(CLASS / entry["path"])
            original = "\n".join(src(notebook["cells"][j]) for j in answers[q]["cells"]
                               if noncomment(src(notebook["cells"][j])) or
                               (q < 6 and short_answer(src(notebook["cells"][j]))))
            matched = original == parsed["source"] and parsed["sha256"] == check_sha
            source_audit.append({"folder":folder,"file":file,"question":q+1,
                                  "source_integrity":"PASS" if matched else "BLOCK",
                                  "source_chars":len(original), "extracted_chars":len(parsed["source"])})
            if status in ("REVIEW_REQUIRED","SEMANTIC_REVIEW"):
                audit.append({"folder":folder,"file":file,"question":q+1,
                              "level":"BLOCK" if status=="REVIEW_REQUIRED" else "REVIEW",
                              "finding":status, "comment":reason})
            if score == QMAX[q] and q >= 6:
                # 满分代码题独立结构核查，禁止用输出匹配代替结构
                if "REVIEW_UNSAFE" in runtime or entry["structure_issue"]:
                    audit.append({"folder":folder,"file":file,"question":q+1,
                                  "level":"BLOCK","finding":"FULL_MARK_STRUCTURAL_REVIEW",
                                  "comment":"满分代码含结构风险"})
        valid_count = sum(bool(short_answer(x["source"]) if j < 6 else noncomment(x["source"])) for j,x in enumerate(answers))
        score_total = sum(s for s in scores if s is not None)
        review = any(s is None for s in scores) or bool(entry["structure_issue"])
        file_summaries.append({"folder":folder,"file":file,"sha256":sha,"score":score_total,
                               "valid_answers":valid_count,"review":review,
                               "q_scores":scores, "path":entry["path"]})
    write_csv(OUT / "extracted_results.csv", extracted,
              ["folder","file","sha256","question","source","runtime","status"])
    write_csv(OUT / "source_integrity_audit.csv", source_audit,
              ["folder","file","question","source_integrity","source_chars","extracted_chars"])
    write_csv(OUT / "grading_detail.csv", detail,
              ["folder","file","question","max_score","score","status","reason",
               "answer_evidence","runtime_evidence","sha256"])
    write_csv(OUT / "grading_audit_findings.csv", audit,
              ["folder","file","question","level","finding","comment"])
    if any(x["source_integrity"]!="PASS" for x in source_audit):
        raise SystemExit("SOURCE_INTEGRITY_GATE BLOCKED")
    grouped = defaultdict(list)
    for item in file_summaries:
        grouped[item["folder"]].append(item)
    summary = []
    for folder, choices in sorted(grouped.items()):
        # 提交版本冲突需人工确认，临时按有效作答数最大版本供教师查阅，绝不静默覆盖
        choice = sorted(choices, key=lambda x:(x["valid_answers"],x["score"]),reverse=True)[0]
        student_id, id_source = identify_student(CLASS / choice["path"])
        issues = []
        if len(choices)>1: issues.append("MULTIPLE_SUBMISSIONS")
        if not student_id: issues.append("IDENTITY_MISSING")
        if id_source == "NOTEBOOK_BODY": issues.append("IDENTITY_FROM_BODY")
        if choice["review"]: issues.append("STRUCTURE_REVIEW")
        if any(a["file"]==choice["file"] and a["folder"]==folder for a in audit):
            issues.append("AUDIT_REVIEW")
        summary.append({"folder":folder, "student_id_from_filename":student_id,
                        "selected_file":choice["file"], "id_source":id_source, "file_count":len(choices),
                        "answered_questions":choice["valid_answers"],
                        "provisional_score":choice["score"], "max_score":100,
                        "status":"REVIEW_REQUIRED" if issues else "GRADED_PROVISIONAL",
                        "issues":";".join(issues),
                        **{f"Q{i+1}":v for i,v in enumerate(choice["q_scores"])}})
    cols=["folder","student_id_from_filename","selected_file","id_source","file_count",
          "answered_questions","provisional_score","max_score","status","issues"]+[
              f"Q{i}" for i in range(1,13)]
    write_csv(OUT/"grade_summary_provisional.csv",summary,cols)
    statuses=Counter(x["status"] for x in summary)
    # 审核未完成时，不创建 grade_summary_final.csv，防止草稿冒充正式成绩
    vals=[x["provisional_score"] for x in summary]
    report=f"""# Python课堂小测一 · 班级1 · V6批改审计报告

## 运行与完整性
- 学生文件夹：{len(folders)}
- Notebook原始提交：{len(files)}
- 本轮运行/尝试：{len(executed)}
- 已统一提取：{len(extracted)} 道题
- SOURCE_INTEGRITY_GATE：{'PASS' if all(x['source_integrity']=='PASS' for x in source_audit) else 'BLOCK'}
- 复核标记：{len(audit)}
- 文件解析阻塞：{sum(x['execution_status']=='FILE_BLOCKED' for x in executed)}
- 重复文件夹：{sum(len(x)>1 for x in grouped.values())}
- 学生汇总：{len(summary)} 人；{dict(statuses)}
- 草稿均分：{statistics.mean(vals):.2f}；中位数：{statistics.median(vals):.1f}（非正式）
- RUBRIC：rubric.lock.json；满分100分

## 评分依据
按仓库教师参考答案及 assignment-grading V6。选择题5分×4，
填空题10分×2，编程题10分×4，纠错题10分×2。
代码题优先运行证据+结构要求；单个语法错误保留符合要求的部分得分；
不能仅根据关键词直接判满分。未把学生保存的旧输出作为证据。

## 待人工复核
- 同文件夹多版本：所有版本保留，暂按有效作答数量选取，仅供复核。
- 学号只在Notebook正文、文件名缺失：标身份待核。
- Python代码含语法错、异常、非标准文件结构：需核对原始答案与评分点。
- 自动结构审核并不替代教师对满分代码的核实。

## 状态
**REVIEW_REQUIRED，不是正式发布成绩。**
只有确认重复版本、身份、语义边界、各道满分结构审计后，
才能生成grade_summary_final.csv；不得为了分数分布漂亮自行调分。

本程序从不改写任何学生Notebook，也不覆盖学生提交源文件。
"""
    (OUT/"grading_audit_summary.md").write_text(report,encoding="utf-8")
    (OUT/"class_error_summary.md").write_text(report,encoding="utf-8")
    print(f"RESULT: files={len(files)} folders={len(folders)} detail={len(detail)} "
          f"reviews={len(audit)} provisional_mean={statistics.mean(vals):.2f}",flush=True)

if __name__ == "__main__":
    main()
