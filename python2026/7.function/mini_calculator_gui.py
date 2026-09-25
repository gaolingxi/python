"""第七章综合实践：具有计算器外观的 tkinter 图形界面计算器。"""
import tkinter as tk

# 第一部分：四个运算函数，函数章节的学习重点
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b == 0:
        return None
    return a / b

def calculate(a, b, op):
    if op == "+":
        return add(a, b)
    if op == "−":
        return subtract(a, b)
    if op == "×":
        return multiply(a, b)
    if op == "÷":
        return divide(a, b)
    return None

def format_number(number):
    if number == 0:
        return "0"
    return f"{number:.12g}"

# 第二部分：老师提供窗口和按钮框架，学生可以更换配色或布局
def create_calculator():
    root = tk.Tk()
    root.title("迷你计算器")
    root.geometry("360x535")
    root.resizable(False, False)
    root.configure(bg="#151A23")

    display = tk.StringVar(value="0")
    history = tk.StringVar(value="")
    state = {"left": None, "operator": None, "new_number": False}

    def reset():
        display.set("0")
        history.set("")
        state.update(left=None, operator=None, new_number=False)

    def show_error():
        display.set("不能除以 0")
        history.set("按 C 重新开始")
        state.update(left=None, operator=None, new_number=True)

    def press(key):
        current = display.get()
        if key == "C":
            reset()
            return

        if key == "DEL":
            if state["new_number"]:
                return
            display.set(current[:-1] if len(current) > 1 else "0")
            if display.get() in ("", "-"):
                display.set("0")
            return

        if key == "±":
            if state["new_number"]:
                display.set("0")
                state["new_number"] = False
            current = display.get()
            if current != "0":
                display.set(current[1:] if current.startswith("-") else "-" + current)
            return

        if key in ("0", "00", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."):
            if state["new_number"] or current == "不能除以 0":
                current = "0"
                display.set("0")
                state["new_number"] = False
                if state["operator"] is None:
                    history.set("")
            if key == ".":
                if "." not in current:
                    display.set(current + ".")
            elif key == "00":
                if current not in ("0", "-0"):
                    display.set(current + "00")
            elif current in ("0", "-0"):
                display.set(("-" if current.startswith("-") else "") + key)
            else:
                display.set(current + key)
            return

        if key in ("+", "−", "×", "÷"):
            if current == "不能除以 0":
                return
            if state["operator"] is not None and not state["new_number"]:
                result = calculate(state["left"], float(current), state["operator"])
                if result is None:
                    show_error()
                    return
                display.set(format_number(result))
            state["left"] = float(display.get())
            state["operator"] = key
            state["new_number"] = True
            history.set(f"{display.get()} {key}")
            return

        if key == "=":
            if state["operator"] is None or state["new_number"]:
                return
            right = float(display.get())
            result = calculate(state["left"], right, state["operator"])
            if result is None:
                show_error()
                return
            history.set(f"{format_number(state['left'])} {state['operator']} {format_number(right)} =")
            display.set(format_number(result))
            state.update(left=None, operator=None, new_number=True)

    # 显示屏：上方显示上一步算式，下方显示当前数字
    screen = tk.Frame(root, bg="#202735", padx=13, pady=11)
    screen.pack(fill="x", padx=14, pady=(16, 9))
    tk.Label(
        screen, textvariable=history, anchor="e", bg="#202735",
        fg="#AAB5C3", font=("Microsoft YaHei UI", 11), height=2
    ).pack(fill="x")
    tk.Entry(
        screen, textvariable=display, state="readonly", readonlybackground="#202735",
        fg="#F8FAFC", justify="right", relief="flat", borderwidth=0,
        font=("Segoe UI", 32, "bold")
    ).pack(fill="x", ipady=10)

    # 按键区：四列五行，浅色工具键 / 深色数字键 / 橙色运算键 / 绿色等号
    pad = tk.Frame(root, bg="#151A23", padx=10, pady=5)
    pad.pack(fill="both", expand=True)
    for col in range(4):
        pad.columnconfigure(col, weight=1, uniform="button")
    for row in range(5):
        pad.rowconfigure(row, weight=1, uniform="button")

    keys = [
        ["C", "DEL", "±", "÷"],
        ["7", "8", "9", "×"],
        ["4", "5", "6", "−"],
        ["1", "2", "3", "+"],
        ["00", "0", ".", "="],
    ]
    for row, line in enumerate(keys):
        for col, key in enumerate(line):
            if key == "=":
                bg, fg, active = "#4FC3A1", "#10221E", "#70D7B8"
            elif key in ("+", "−", "×", "÷"):
                bg, fg, active = "#EF9A4A", "#231509", "#FFBB77"
            elif key in ("C", "DEL", "±"):
                bg, fg, active = "#424D60", "#F8FAFC", "#596981"
            else:
                bg, fg, active = "#2B3444", "#F8FAFC", "#455269"
            tk.Button(
                pad, text=key, command=lambda value=key: press(value),
                font=("Segoe UI", 20, "bold"), bg=bg, fg=fg,
                activebackground=active, activeforeground=fg,
                relief="flat", bd=0, cursor="hand2", takefocus=0
            ).grid(row=row, column=col, sticky="nsew", padx=4, pady=4)

    # 加分功能：也支持用数字键盘、回车、Esc 和 Backspace 操作
    def on_keyboard(event):
        mapped = {
            "/": "÷", "*": "×", "-": "−", "Return": "=",
            "Escape": "C", "BackSpace": "DEL"
        }
        key = mapped.get(event.keysym, event.char)
        if (key in "0123456789" and len(key) == 1) or key in (".", "+", "−", "×", "÷", "=", "C", "DEL"):
            press(key)

    root.bind("<Key>", on_keyboard)
    return root

def main():
    window = create_calculator()
    window.mainloop()

if __name__ == "__main__":
    main()
