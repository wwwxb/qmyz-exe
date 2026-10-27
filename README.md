# QMYZ 便携版（Windows）

> 基于 [shibig666/QMYZ](https://github.com/shibig666/QMYZ) 二次打包的 Windows 绿色便携版：**内置 Python 运行环境与题库，解压双击即用**，并额外提供了一个图形界面。

**与上游的关系**：本仓库以上游代码为基础做修改（新增 `app/gui.py`、打包脚本和文档，业务代码未改动）。上游采用 GPL-3.0，版权归原作者所有；本仓库的修改部分同样以 GPL-3.0 发布。修改内容见 [CHANGES.md](CHANGES.md)。

## 特性

| 特性 | 说明 |
|---|---|
| 解压即用 | 目标电脑**不需要安装 Python**，双击 `QMYZ.exe` 即可 |
| 图形界面 | tkinter：粘贴登录 URL、下拉选课程、设答题量/准确度、实时日志、随时停止 |
| 内置题库 | 15 门课、约 1.2 万道题，随包分发 |
| 可换题库 | 把新的 `<课程ID>.csv` 放到 `QMYZ.exe` 同级的 `qmyz\` 目录即可覆盖内置题库，无需重新打包 |
| 不污染系统 | 纯绿色版，删除文件夹即卸载，不写注册表 |

## 下载

到 [Releases](../../releases) 下载 `QMYZ-v1.0.0-portable.zip`（约 19.5 MB，解压后 47 MB）。

## 使用

1. 解压到任意目录（如 `D:\QMYZ`），**不要只拷贝 exe**，`_internal\` 必须一起保留；
2. 双击 `QMYZ.exe`；
3. 浏览器登录「易班 - 青马易战」，进入课程答题页，把地址栏里的**整段 URL**（含 `JSESSIONID`）复制下来；
4. 回到程序：`粘贴` → `获取课程` → 选课程 → 设置答题量与准确度 → `开始刷题`。

详细步骤、常见问题、免责声明见 [docs/使用说明.txt](docs/使用说明.txt)。

> 程序不包含登录功能，只复用你浏览器里已登录的会话，所以**每次都要自己提供 URL**；请勿把自己的 URL 分享给他人（等同交出账号）。

## 从源码构建

需要 Windows + Python 3.10+（实测 3.13）。构建机上要能访问 PyPI（可换国内镜像）。

```powershell
# 1. 虚拟环境 + 依赖
python -m venv .venv
.\.venv\Scripts\python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple requests pycryptodome pyinstaller

# 2. 打包（onedir 模式，无控制台）
.\.venv\Scripts\pyinstaller qmyz.spec --noconfirm --clean

# 3. 冒烟自检（不弹窗、不联网，结果写入 st.txt）
.\dist\QMYZ\QMYZ.exe --selftest st.txt

# 4. 组装发布包并压缩
.\.venv\Scripts\python pack.py
```

产物：

- `dist\QMYZ\QMYZ.exe` + `dist\QMYZ\_internal\`（可直接运行的目录）
- `release\QMYZ-v1.0.0-portable.zip`（分发用，**属于构建产物，已被 .gitignore 排除**）

### 自检输出示例

```
tk ok
bank_dirs=['...\_internal\qmyz']
courses=2,7,8,9,10,12,50,59,61,68,138,257,444,512,520
bank9_rows=1217
requests=2.32.4
pycryptodome=ok
mainloop ok
```

## 目录结构

```
app/                    上游源码（业务代码原样）
├── fight.py            自动 AI 对战 / 爬题写回 CSV
├── qm_cli.py           命令行入口
├── qm_auto.py          交互式命令行入口
├── qm_utils/           核心：题库匹配、AES 解密、请求封装
├── qmyz/*.csv          题库
├── gui.py              ★ 新增：图形界面 + 路径解析 + 自检模式
└── README.md           上游原始说明
qmyz.spec               PyInstaller 打包描述（onedir）
pack.py                 组装 release/ 并打 zip
docs/                   使用说明、构建方案、开源合规说明
LICENSE.txt             GPL-3.0 全文
```

## 已知限制

- 平台地址**硬编码**为 `http://112.5.88.114:31101`，平台改版 / 换 IP / 换加密密钥即失效；
- 题库只覆盖 **15 门课**（2/7/8/9/10/12/50/59/61/68/138/257/444/512/520），冷门课程命中率很低；
- PyInstaller 产物在部分杀软（360/火绒/Defender）下会误报，需自行加信任；彻底解决需代码签名证书；
- 答题间隔 3~6 秒随机、请求头伪装浏览器，但无法保证不被平台风控识别。

## 许可证

[GPL-3.0](LICENSE.txt)。分发二进制时必须同时提供对应的完整源代码（本仓库即源码）。

## 免责声明

本项目仅供编程学习与技术交流。请遵守所在学校与平台的使用规定，**严禁商业用途**。使用本程序产生的一切后果（账号异常、成绩异常、纪律处分等）由使用者自行承担。
