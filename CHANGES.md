# 修改记录（相对上游 shibig666/QMYZ）

依 GPL-3.0 §5(a) 声明：**本程序修改过**，修改内容如下。

## v1.0.0

### 新增
- `app/gui.py`：tkinter 图形界面
  - 粘贴登录 URL → 抓取 `JSESSIONID`，在线获取课程列表（失败时回退到本地题库课程）
  - 课程下拉框、答题量、准确度设置
  - 日志框：把 `sys.stdout` 重定向到 UI 队列，上游所有 `print` 直接进入界面
  - 可停止的答题循环（上游 `qm_auto.auto_do()` 在 `num<=0` 时是 `while True`，无法外部停止）
  - 题库查找顺序：exe 同级 `qmyz\` → `_internal\qmyz\` → `_MEIPASS\qmyz\` → 开发态 `app\qmyz\`
  - `--selftest <file>`：无人工干预的自检模式（验证 tkinter、题库、依赖是否在冻结环境中可用）
- `qmyz.spec`：PyInstaller onedir 打包描述（无控制台、排除 numpy/pandas/PIL 等无用依赖）
- `pack.py`：组装回发布目录并打 zip
- `docs/`：使用说明、构建方案、源码获取说明
- `LICENSE.txt`：GPL-3.0 全文（同时保留在 `app/` 内）

### 未改动
- `app/fight.py`、`app/qm_cli.py`、`app/qm_auto.py`、`app/qm_utils/*`、`app/qmyz/*.csv` 与上游完全一致。

### 分发说明
- 仓库只包含源码；二进制（`QMYZ.exe` 与 `_internal`）以 Release 附件形式提供，构建脚本可完整复现。
- 按 GPL-3.0，分发二进制时必须同时提供对应完整源码。
