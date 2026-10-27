# QMYZ Windows 便携版分发方案（已实测验证）

目标：把 https://github.com/shibig666/QMYZ 做成**解压即用的绿色版**，内置 Python 运行环境与题库，新增一个简单刷题界面，尽量不改动上游代码。

本方案不是纸上推演：本文档中的数字和结论都来自本机实际打包与运行验证（2026-10-27）。

---

## 一、核实结果（先看这个）

| 项目 | 结论 | 依据 |
|---|---|---|
| 语言/技术栈 | **纯 Python 3 + requests 同步 HTTP 脚本**，无框架、无数据库、无浏览器自动化 | 26 个文件全部读完；`requirements.txt` 仅 2 行 |
| 运行依赖 | `requests`、`pycryptodome`（仅用 AES-ECB 解密题干），以及标准库 `csv` / `re` / `argparse` / `os` | `qm_utils/qm.py:1-6`、`qm_utils/qm_tools.py:1-5` |
| 许可证 | **GPL-3.0**（仓库 `LICENSE.txt`，README 第 88 行亦声明） | GitHub API `license.spdx_id = GPL-3.0` |
| 体量 | 源码 26 文件；题库 14 个 CSV 共约 3.4 MB、12,000+ 题 | 实测 |
| 启动方式 | 三个独立入口，均为脚本级执行（无 `setup.py`/`pyproject.toml`，**不是 pip 包**） | 仓库根目录 |
| 网络要求 | **只访问 `http://112.5.88.114:31101`（明文 HTTP，固定 IP + 端口）**，全部 `verify=False`；不需要 HTTPS、不需要梯子 | `qm_utils/qm.py:80,133`、`qm_utils/qm_tools.py:59` |
| 登录方式 | 不自动登录。用户自己在浏览器登录后，把带 `JSESSIONID` 的地址整段复制进来，程序从 `set-cookie` 里取 cookie | `qm_utils/qm.py:70-76`、README 第 41 行 |
| 加密 | 题干/选项用 AES-ECB 解密，**密钥硬编码** `ZDBmMTNiZGI3MDRhMWVhMWE3MTcwNjJiNTk0NzY0ODg`（base64） | `qm_utils/qm.py:26`、`fight.py:18` |
| 反检测 | 请求头伪装 Edge 浏览器；每题随机 `sleep(3~6)` 秒；识别到“防刷题/请选择”类题干自动跳过 | `qm_utils/qm.py:97-99,163` |

### 三个入口的差异

- `qm_cli.py`（27 行）：命令行，`-u 登录URL -i 课程ID -c 题库 -n 答题量 -a 准确度`。
- `qm_auto.py`（22 行）：交互式，先 `get_courses()` 抓课程列表再逐项 `input()`。
- `fight.py`（269 行）：自动 AI 对战 + **爬题写回 CSV**（README 推荐用它扩充题库）。参数写死在文件头第 12-14 行，需要手改源码——这是唯一需要动文件的地方，分发时建议保留原样并告知用户。

### 题库结构（决定了 UI 能否做“命中率预估”）

10 列 CSV，表头 `courseId,id,subType,optionCount,subDescript,option0..option3,answer`；
匹配逻辑是**题干文本全等**（`qm.py:102` `if sub_descript == t[4]`），答案取末列 `t[-1]`。
现有题库 **全部是单选题**，`subType` 字段没有判断题/多选题（代码支持，数据没有）。
`qmyz/info.json` 声明 15 个课程号，README 表格只列了 14 个（多出 `512`）。

### 关键限制（决定了方案形态）

1. **没有 UI**，全是 `print()` + `input()`，而且 `auto_do()` 在 `num<=0` 时是 `while True` 死循环，无法从外部停止。
2. **没有配置文件**，参数全靠命令行/源码常量。
3. `qm_auto.py` 用了 `os.listdir("qmyz")`、`"qmyz/{}.csv"` 这类**相对当前工作目录**的路径 —— 打包后如果直接复用它会因 CWD 不同而找不到题库，所以界面层必须自己解析路径（本方案已处理）。
4. `Crypto` 是顶层 import，缺它连 `import qm_utils` 都会失败。

**联网结论：客户端本身不需要梯子**（纯 HTTP 内网地址）；只有“构建阶段 `pip install`”和“你 clone 源码”需要外网，构建可用清华/阿里镜像。

---

## 二、方案选型

| 决策点 | 选择 | 理由 |
|---|---|---|
| 打包工具 | **PyInstaller 6.x，onedir 模式** | 依赖少、tkinter/requests/Crypto 都有现成 hook；onedir 启动快（<1s），onefile 每次解压到 `%TEMP%` 启动 3-5 秒且更容易被杀软误杀 |
| UI 框架 | **tkinter（标准库）** | 零额外依赖、打包体积最小、PyInstaller 支持最成熟；做“填参数 + 日志窗”完全够用 |
| 是否改上游代码 | **一个字节都不改** | 所有适配放在新增的 `app/gui.py`：路径解析、日志重定向、可停止的答题循环，全部在界面层完成 |
| 题库存放 | 内置到 `_internal/qmyz/`，同时**优先读取 exe 同级 `qmyz/`** | 用户可以自己更新题库而不必重新打包；两全 |
| 瘦身 | 关 UPX、排除 numpy/pandas/PIL 等 | 关 UPX 明显降低杀软误报率；实测 47 MB / 压缩后 19.5 MB |

---

## 三、界面设计（已实现）

单窗口，从上到下：

```
┌──────────────────────────────────────────────────────────┐
│ 登录URL [____________________________] [粘贴] [获取课程]  │
│ 课程    [9 | 马克思主义基本原理      ▼]  题库: 1217 题    │
│ 答题量 [0] (0=无限)          准确度 [100]                 │
│ [开始刷题] [停止] [打开题库目录] [清空日志]      就绪       │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ 便携版 v1.0.0 | 平台 http://112.5.88.114:31101        │ │
│ │ 题库载入 1218 条，课程 9，准确度 100%，答题量 无限     │ │
│ │ 查询到题目: 马克思主义的三个组成部分是…               │ │
│ │ 答题正确, 当前答对1道，准确率为100.0                  │ │
│ └──────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

实现要点（对应 `app/gui.py`）：

- `bank_dirs()`：按 `exe同级/qmyz` → `_internal/qmyz` → `_MEIPASS/qmyz` → 开发态顺序找题库。
- `QueueWriter`：把 `sys.stdout` 换成写队列的对象，**原代码里的 `print` 一行不改就进了日志框**；主线程 `after(100)` 抽取。
- 停止：不调用 `auto_do()`，界面自己按 `random.randint(3,6)` 的节奏循环调用 `engine.do()`，每轮检查 `threading.Event`。
- 兜底课程名：`COURSE_NAMES` 内置 15 个名字；在线 `get_courses()` 成功则用线上列表，失败则退回本地题库列表。
- `--selftest <文件>`：无人工干预自检模式，供打包后验证（见第六节实测输出）。

---

## 四、目录结构（本仓库）

```
<仓库根目录>\
├─ app\                    # 上游源码，原样（只新增 gui.py）
│  ├─ fight.py  qm_cli.py  qm_auto.py  requirements.txt  README.md  LICENSE.txt
│  ├─ qm_utils\{__init__,qm,qm_tools}.py
│  ├─ qmyz\{2,7,8,9,10,12,50,59,61,68,138,257,444,512,520}.csv + info.json
│  └─ gui.py               # ★新增：tkinter 界面 + 路径解析 + 自检
├─ qmyz.spec               # PyInstaller 打包描述
├─ pack.py                 # 组装 release/ + 打 zip
├─ docs\                    # 使用说明、本方案、源码获取说明
├─ release\                 # 构建产物（.gitignore 已排除）
│  ├─ QMYZ-v1.0.0-portable\ （47 MB，可直接运行）
│  └─ QMYZ-v1.0.0-portable.zip （19.5 MB，分发用，作为 Release 附件上传）
└─ dist\QMYZ\              （PyInstaller 原始输出，同样被忽略）
```

分发包内的最终形态：

```
QMYZ-v1.0.0-portable\
├─ QMYZ.exe              3.7 MB，无控制台窗口
├─ _internal\            运行环境（Python 3.13 + tcl/tk + requests + Crypto）
│  └─ qmyz\              内置题库
├─ LICENSE.txt           GPLv3 原文
├─ 使用说明.txt
├─ 源码获取说明.txt
└─ source\gui.py, qmyz.spec   ← GPLv3 源码对应物
```

---

## 五、可执行步骤（在正常 Windows 机器上复现）

```powershell
# 0) 取源码（保留原始目录结构）
git clone https://github.com/shibig666/QMYZ.git app
#    然后把 gui.py 放进 app\ ，把 qmyz.spec 放在 app 的同级

# 1) 环境（国内镜像加速）
python -m venv .venv
.\.venv\Scripts\python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests pycryptodome pyinstaller

# 2) 打包（onedir、无控制台）
.\.venv\Scripts\pyinstaller qmyz.spec --noconfirm --clean
#    产物： dist\QMYZ\QMYZ.exe + _internal\

# 3) 冒烟自检（不需要人点鼠标，输出写到文件）
.\dist\QMYZ\QMYZ.exe --selftest st.txt ; type st.txt

# 4) 组装发布包 + 压缩
python pack.py
#    产物： release\QMYZ-v1.0.0-portable.zip

# 5) 真机验收（重要）
#    - 在“没有装 Python 的电脑”上解压运行；
#    - 用真实登录 URL 跑 5 题，确认能取到 cookie、能答、日志正常；
#    - 关掉杀软再开，确认是否被拦截（必要时做代码签名）。
```

### 本机沙箱里遇到的两个坑（复现时先看这里）

1. **`pip install` 报 `[Errno 13] Permission denied ...whl.metadata`**：DSH 沙箱对系统 `%TEMP%` 只读。
   绕过：`set TMP=<workspace>\tmp` 并 `set TEMP=%TMP%`；或用本方案用过的“直接下 wheel 解压到 vendor 目录 + `PYTHONPATH`”方式。
2. **PyInstaller 报 `PermissionError: [WinError 5]`**（`isolated/_parent.py` 建命名管道）：沙箱禁止命名管道。
   必须在非受限环境打包（本机是通过一次 `danger-full-access` 授权完成的，构建本身约 20 秒）。

---

## 六、验证结果（本次实测）

`QMYZ.exe --selftest st.txt` 输出：

```
tk ok
bank_dirs=['...\dist\QMYZ\_internal\qmyz']
courses=2,7,8,9,10,12,50,59,61,68,138,257,444,512,520
bank9=...\_internal\qmyz\9.csv
bank9_rows=1217
requests=2.32.4
pycryptodome=ok
app_title=QMYZ 青马易战 刷题助手 v1.0.0
mainloop ok
```

即：tkinter 能起窗口、内置题库被正确定位、15 门课全部识别、requests 与 pycryptodome 在冻结环境中可用。
**唯一没有验证的是“真账号联网答题”**——需要一个真实登录 URL，且会真实改动平台数据，留给你验收。

体积实测：`QMYZ.exe` 3.7 MB，`_internal` 44 MB，整包 47 MB，zip 19.5 MB。

---

## 七、风险与合规（分发前必须决定）

1. **GPL-3.0 是硬约束**：发 exe = 分发目标代码，必须同时给对应源码（第 6 条）。已在包里放 `source/` + 上游地址 + `源码获取说明.txt`。任何人二次转发也有同样义务。**不能闭源、不能加限制性 EULA。**
2. **上游 README 写“严禁用于商业用途”**，与 GPL 的商用自由有冲突；稳妥做法：免费分发、不收费、不搞激活码/广告。
3. **使用性质**：这是给思政学习平台自动刷题的工具，平台用户协议普遍禁止自动化。技术上没有破解加密系统、没有攻击服务器（靠用户自己的合法会话发正常请求），但**公开传播=公开提供作弊工具**，可能触发学校纪律处理或平台封号；大规模传播还有被平台方主张不正当竞争/侵权的风险。自用与小范围分享风险低，挂公开 Releases 风险明显更高。
4. **脆弱性**：平台地址 `112.5.88.114:31101` 是硬编码，平台改版/换 IP/换加密密钥/加验证码，程序立刻失效；题库靠社区补，冷门课程命中率很低。
5. **杀软误报**：PyInstaller 产物在国内三大杀软下误报率不低；关 UPX 有帮助，彻底解决要买代码签名证书（约 1000-3000 元/年）。
6. **不要内置任何账号/cookie/代理**，否则分发即变成“代刷服务”，法律定性完全不同。

---

## 八、后续可选增强（不影响当前可用性）

- 界面加“题库命中率预估”：拿本地 CSV 与最近 N 题比对，提前告诉用户这课能不能刷（需在 `do()` 前拦截题干，属新增逻辑）。
- 把 `fight.py` 的爬题功能也搬进界面（同样用 `redirect_stdout` 包装，参数从界面传，避免让用户改源码）。
- 自动从仓库 `raw.githubusercontent.com` 拉最新题库（加开关，避免默认联网）。
- 加上 `--onedir` 的增量更新器（只替换 `_internal/qmyz/*.csv`），做小体积补丁包。

---

## 九、结论

**可行，且已经跑通。** 技术栈极其简单（两个第三方依赖、无浏览器、无数据库），用 PyInstaller onedir + tkinter 界面即可得到“解压双击就用”的绿色版；难点不在技术，而在 **GPLv3 的源码义务** 和 **这类工具公开传播的定性风险**——发布前需要你明确接受这两条。
