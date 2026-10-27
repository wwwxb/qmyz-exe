# -*- coding: utf-8 -*-
"""QMYZ 图形界面（新增文件，不改动上游任何源码）

用途：
    为 shibig666/QMYZ 提供一个极简的 Windows 刷题界面，内部直接复用
    qm_utils.qm / qm_utils.qm_tools 的原有逻辑。

设计约束：
    1. 不修改 fight.py / qm_cli.py / qm_auto.py / qm_utils/* 的任何一个字节；
    2. 只在界面层做三件事：收集参数、驱动 qm_auto.do()、把 print 输出重定向到日志框；
    3. 支持“停止”，因此不调用 auto_do()（它是死循环），改为界面自己按 3~6 秒
       随机间隔调用 do()，节奏与原实现一致。
"""

import io
import os
import queue
import random
import sys
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "QMYZ 青马易战 刷题助手"
APP_VERSION = "1.0.0"
PLATFORM = "http://112.5.88.114:31101"

# 课程 id -> 名称（取自上游 README，抓不到线上课程列表时作为兜底显示）
COURSE_NAMES = {
    "2": "形势与政策",
    "7": "毛泽东思想和中国特色社会主义理论体系概论",
    "8": "思想道德与法治",
    "9": "马克思主义基本原理",
    "10": "中国近现代史纲要",
    "12": "习近平新时代中国特色社会主义思想概论",
    "50": "党史学习",
    "59": "集训-习近平新时代中国特色社会主义思想",
    "61": "集训-中国近现代史纲要",
    "68": "学习“四史”",
    "138": "《习近平新时代中国特色社会主义思想》部分第二轮复习测验",
    "257": "学习二十大",
    "444": "铸牢中华民族共同体意识",
    "512": "复习题库(512)",
    "520": "二十届三中全会",
}


def base_dir():
    """exe 所在目录（便携版根目录），PyInstaller 下为 sys.executable 的父目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def bank_dirs():
    """题库候选目录，优先级：用户可编辑目录 > 打包内置目录。"""
    cands = []
    b = base_dir()
    cands.append(os.path.join(b, "qmyz"))                  # 便携版：用户可自行替换题库
    cands.append(os.path.join(b, "_internal", "qmyz"))     # onedir 内置数据
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(os.path.join(meipass, "qmyz"))        # onefile 解包目录
    cands.append(os.path.join(b, "app", "qmyz"))           # 开发态
    cands.append(os.path.join(b, "qmyz"))                  # 开发态
    seen, out = set(), []
    for c in cands:
        c = os.path.abspath(c)
        if c not in seen and os.path.isdir(c):
            seen.add(c)
            out.append(c)
    return out


def find_bank(course_id):
    for d in bank_dirs():
        p = os.path.join(d, "{}.csv".format(course_id))
        if os.path.isfile(p):
            return p
    return None


def local_courses():
    """本地题库里实际存在的课程 id 列表（按数字排序）。"""
    ids = set()
    for d in bank_dirs():
        for name in os.listdir(d):
            if name.endswith(".csv") and name[:-4].isdigit():
                ids.add(name[:-4])
    return sorted(ids, key=lambda x: int(x))


class QueueWriter(io.TextIOBase):
    """把原代码里的 print 重定向到日志队列，保持日志实时。"""

    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(("log", s))
        return len(s)

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.q = queue.Queue()
        self.worker = None
        self.stop_event = threading.Event()
        self.qm = None
        self.session_cookie = ""

        root.title("{} v{}".format(APP_TITLE, APP_VERSION))
        root.geometry("760x560")
        root.minsize(680, 480)

        self.var_url = tk.StringVar()
        self.var_course = tk.StringVar()
        self.var_num = tk.IntVar(value=0)
        self.var_acc = tk.IntVar(value=100)
        self.var_status = tk.StringVar(value="就绪")

        self._build_ui()
        self._fill_courses_from_local()
        self.root.after(100, self._pump)
        self.log("便携版 v{} | 平台 {} ".format(APP_VERSION, PLATFORM))
        self.log("题库目录：{}".format(bank_dirs() or "未找到"))
        self.log("使用步骤：浏览器登录平台 → 复制首页地址 → 粘贴到下方 → 获取课程 → 开始")
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- UI ----------------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 4}
        frm = ttk.Frame(self.root)
        frm.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(frm, text="登录URL").grid(row=0, column=0, sticky="w")
        e = ttk.Entry(frm, textvariable=self.var_url)
        e.grid(row=0, column=1, columnspan=4, sticky="ew", **pad)
        ttk.Button(frm, text="粘贴", width=6, command=self._paste).grid(row=0, column=5, **pad)
        ttk.Button(frm, text="获取课程", width=9, command=self._fetch_courses).grid(row=0, column=6, **pad)

        ttk.Label(frm, text="课程").grid(row=1, column=0, sticky="w")
        self.cmb_course = ttk.Combobox(frm, textvariable=self.var_course, width=52)
        self.cmb_course.grid(row=1, column=1, columnspan=3, sticky="ew", **pad)
        self.lbl_bank = ttk.Label(frm, text="题库: -")
        self.lbl_bank.grid(row=1, column=4, columnspan=3, sticky="w", **pad)

        ttk.Label(frm, text="答题量").grid(row=2, column=0, sticky="w")
        ttk.Spinbox(frm, from_=0, to=99999, width=8, textvariable=self.var_num).grid(row=2, column=1, sticky="w", **pad)
        ttk.Label(frm, text="0=无限").grid(row=2, column=2, sticky="w")
        ttk.Label(frm, text="准确度").grid(row=2, column=3, sticky="e")
        ttk.Spinbox(frm, from_=0, to=100, width=8, textvariable=self.var_acc).grid(row=2, column=4, sticky="w", **pad)

        frm.columnconfigure(1, weight=1)

        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=6)
        self.btn_start = ttk.Button(bar, text="开始刷题", command=self._start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(bar, text="停止", command=self._stop, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        ttk.Button(bar, text="打开题库目录", command=self._open_bank).pack(side="left", padx=6)
        ttk.Button(bar, text="清空日志", command=lambda: self.txt.delete("1.0", "end")).pack(side="left", padx=6)
        ttk.Label(bar, textvariable=self.var_status).pack(side="right")

        self.txt = tk.Text(self.root, height=20, wrap="word", state="disabled",
                           font=("Consolas", 10))
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.cmb_course.bind("<<ComboboxSelected>>", lambda e: self._update_bank_label())

    # ---------------- helpers ----------------
    def log(self, msg):
        self.txt.configure(state="normal")
        self.txt.insert("end", msg.rstrip("\n") + "\n")
        self.txt.see("end")
        self.txt.configure(state="disabled")

    def _pump(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "log":
                    self.log(payload)
                elif kind == "status":
                    self.var_status.set(payload)
                elif kind == "finish":
                    self._worker_done()
        except queue.Empty:
            pass
        self.root.after(100, self._pump)

    def _paste(self):
        try:
            self.var_url.set(self.root.clipboard_get().strip())
        except tk.TclError:
            pass

    def _fill_courses_from_local(self):
        items = []
        for cid in local_courses():
            name = COURSE_NAMES.get(cid, "课程{}".format(cid))
            items.append("{} | {}".format(cid, name))
        self.cmb_course["values"] = items
        if items and not self.var_course.get():
            self.var_course.set(items[0])
        self._update_bank_label()

    def _course_id(self):
        raw = self.var_course.get().strip()
        if not raw:
            return ""
        return raw.split("|")[0].strip()

    def _update_bank_label(self):
        cid = self._course_id()
        path = find_bank(cid) if cid else None
        if not path:
            self.lbl_bank.configure(text="题库: 未找到（将无法答题）")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                n = max(0, sum(1 for _ in f) - 1)
        except Exception:
            n = -1
        self.lbl_bank.configure(text="题库: {} 题".format(n))

    def _open_bank(self):
        d = bank_dirs()
        if not d:
            messagebox.showwarning("提示", "没有找到题库目录")
            return
        os.startfile(d[0])

    # ---------------- actions ----------------
    def _fetch_courses(self):
        url = self.var_url.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先粘贴登录URL")
            return
        self.var_status.set("正在获取课程…")
        threading.Thread(target=self._fetch_courses_worker, args=(url,), daemon=True).start()

    def _fetch_courses_worker(self, url):
        try:
            import qm_utils.qm_tools as qm_tools
            cookie = qm_tools.get_cookie_from_url(url)
            self.session_cookie = cookie
            courses = qm_tools.get_courses(cookie)
            if courses:
                items = ["{} | {}".format(k, v) for k, v in courses.items()]
                self.q.put(("log", "从平台获取到 {} 门课程".format(len(items))))
            else:
                items = None
                self.q.put(("log", "平台未返回课程列表，改用本地题库列表"))
            self.root.after(0, lambda: self._apply_courses(items))
        except Exception as e:
            self.q.put(("log", "获取课程失败：{}".format(e)))
        finally:
            self.q.put(("status", "就绪"))

    def _apply_courses(self, items):
        if items:
            self.cmb_course["values"] = items
            self.var_course.set(items[0])
        else:
            self._fill_courses_from_local()
        self._update_bank_label()

    def _start(self):
        if self.worker and self.worker.is_alive():
            return
        url = self.var_url.get().strip()
        cid = self._course_id()
        if not url:
            messagebox.showwarning("提示", "请先粘贴登录URL")
            return
        if not cid:
            messagebox.showwarning("提示", "请选择课程")
            return
        path = find_bank(cid)
        if not path:
            messagebox.showerror("错误", "本地没有该课程题库：{}".format(cid))
            return
        num = int(self.var_num.get() or 0)
        acc = int(self.var_acc.get() or 100)
        if acc < 0 or acc > 100:
            messagebox.showwarning("提示", "准确度需在 0-100 之间")
            return

        self.stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.var_status.set("运行中…")
        self.worker = threading.Thread(target=self._run_worker,
                                       args=(url, cid, path, num, acc), daemon=True)
        self.worker.start()

    def _stop(self):
        self.stop_event.set()
        self.var_status.set("正在停止…")

    def _run_worker(self, url, cid, path, num, acc):
        old_out = sys.stdout
        sys.stdout = QueueWriter(self.q)
        try:
            import requests
            requests.packages.urllib3.disable_warnings()

            import qm_utils
            ti = qm_utils.qm.qm_tiku(path)
            engine = qm_utils.qm.qm_auto(url, ti.tiku, cid,
                                         JSESSIONID=self.session_cookie, accuracy=acc)
            self.qm = engine
            self.q.put(("log", "题库载入 {} 条，课程 {}，准确度 {}%，答题量 {}".format(
                len(ti.tiku), cid, acc, "无限" if num <= 0 else num)))

            done = 0
            while not self.stop_event.is_set():
                if num > 0 and done >= num:
                    self.q.put(("log", "已完成 {} 题，结束".format(done)))
                    break
                time.sleep(random.randint(3, 6))
                if self.stop_event.is_set():
                    break
                engine.do()
                done += 1
                self.q.put(("status", "已答 {} 题 | 对 {} 错 {}".format(
                    done, engine.num[0], engine.num[1])))
        except Exception as e:
            self.q.put(("log", "运行出错：{}".format(e)))
            self.q.put(("log", traceback.format_exc()))
        finally:
            sys.stdout = old_out
            self.q.put(("finish", None))

    def _worker_done(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        if self.qm is not None:
            n0, n1 = self.qm.num[0], self.qm.num[1]
            total = n0 + n1
            rate = (n0 / total * 100) if total else 0
            self.var_status.set("结束 | 共 {} 题，正确率 {:.1f}%".format(total, rate))
            self.log("=== 结束：共 {} 题，对 {} 错 {}，正确率 {:.1f}% ===".format(
                total, n0, n1, rate))
        else:
            self.var_status.set("已停止")

    def _on_close(self):
        self.stop_event.set()
        self.root.destroy()


def _selftest(out_path):
    """无人工干预的自检：建窗口 -> 检查题库/依赖 -> 写结果文件 -> 退出。

    供打包后验证使用： QMYZ.exe --selftest <结果文件路径>
    """
    lines = []
    code = 0
    try:
        root = tk.Tk()
        app = App(root)
        lines.append("tk ok")
        lines.append("bank_dirs={}".format(bank_dirs()))
        courses = local_courses()
        lines.append("courses={}".format(",".join(courses)))
        lines.append("bank9={}".format(find_bank("9")))
        with open(find_bank("9"), "r", encoding="utf-8") as f:
            lines.append("bank9_rows={}".format(max(0, sum(1 for _ in f) - 1)))
        import requests
        lines.append("requests={}".format(requests.__version__))
        from Crypto.Cipher import AES  # noqa: F401
        lines.append("pycryptodome=ok")
        lines.append("app_title={}".format(app.root.title()))
        root.after(300, root.destroy)
        root.mainloop()
        lines.append("mainloop ok")
    except Exception:
        code = 1
        lines.append("ERROR:\n" + traceback.format_exc())
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        code = 2
    os._exit(code)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    if "--selftest" in sys.argv:
        idx = sys.argv.index("--selftest")
        out = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "selftest.txt"
        _selftest(out)
        return
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
