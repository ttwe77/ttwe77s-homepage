# 七七的折腾笔记 (ttwe77s-homepage)

> 一个仿蔚蓝档案风格的个人主页 + 博客站点，附带一套「个人在线状态」采集与展示系统。
> 记录代码、设计与生活，同时把自己的实时状态（在线 / 离开 / 忙碌 / 离线、当前前台程序）同步到网页上。

---

## 目录

- [项目概览](#项目概览)
- [功能特性](#功能特性)
- [目录结构](#目录结构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
  - [1. 启动静态站点](#1-启动静态站点)
  - [2. 启动状态服务端](#2-启动状态服务端)
  - [3. 运行状态客户端](#3-运行状态客户端)
- [状态系统详解](#状态系统详解)
  - [数据文件](#数据文件)
  - [HTTP API](#http-api)
  - [鉴权](#鉴权)
  - [服务端配置](#服务端配置)
  - [客户端配置](#客户端配置)
  - [客户端命令行](#客户端命令行)
- [博客与发布工具链](#博客与发布工具链)
  - [内容生产流程](#内容生产流程)
  - [页面清单](#页面清单)
  - [字体子集与订阅](#字体子集与订阅)
  - [发布 Skill](#发布-skill)
- [辅助工具](#辅助工具)
- [构建与编译](#构建与编译)
- [部署（Nginx）](#部署nginx)
- [设计规范与资源](#设计规范与资源)
- [开发约定](#开发约定)
- [许可证](#许可证)

---

## 项目概览

项目的核心由三部分组成，彼此解耦、可独立运行；另有一套内容生成与运维工具链负责把 Markdown 烤成可发布的站点：

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| **静态站点** | 仓库根目录 | `index.html` 为主页（含首页、文章列表两屏），`ttwe77.html` 为「关于我」页，`links.html` 为链接页；纯静态，无构建步骤。 |
| **状态服务端** | `服务端/` | 提供 `GET/POST /api/status` 接口，把状态原子写入 JSON 文件，供 Nginx 静态托管。当前使用 C++ (cpp-httplib) 实现；同目录另有一份已淘汰的 Python (Flask) 实现，仅供历史参考。 |
| **状态客户端** | `客户端/` | Windows 托盘程序，探测前台程序与键鼠空闲状态，定时向服务端推送。 |
| **生成工具链** | `tools/`、`skills/` | Markdown → 页面、字体子集、RSS、链接页的生成器与一键发布 Skill；只在开发机上运行，不参与站点运行时。 |

站点通过 `status/index.html` 每 10 秒轮询 `/status/data/device-01.json`，实时展示我的在线状态。

---

## 功能特性

### 静态站点（主页）

- **仿蔚蓝档案风格**：以游戏 UI 为灵感的视觉语言，含主题切换与深色模式。
- **双屏分页**：首页（Masthead 展示）+ 文章列表页，圆点导航 / 页内滑动切换，带 `--page-duration` 过渡动画。
- **文章清单动态生成**：列表由 `blog/index.ini` 的分页向导 + `blog/pages/` 的分页清单驱动，前端按需加载、分页器按页数渲染。
- **仿游戏化 UI**：顶栏含体力 (AP) / 金币 / 青曜石等资源展示、体力恢复弹窗、`toast` 提示。
- **自建音乐播放器**：浮动播放器，歌单以网易云歌曲 ID 配置，支持播放列表、进度拖动、音量、播放模式切换。
- **点击特效**：引入 `libs/ba-click-fx.js`，实现点击 / 拖尾粒子特效。
- **自定义光标**：普通 / 链接 / 帮助三种 `.cur` 光标（`src/cursors/`）。
- **响应式与无障碍**：适配移动端、支持 `prefers-reduced-motion` 动效降级、语义化标签与 ARIA。
- **资源多格式**：图片提供 `avif / webp / png(jpg)` 多格式回退，音频提供 `opus / ogg / mp3 / m4a`。

### 博客系统

- **内容用 Markdown 写**：文章源文件统一放在 `tools/genblog/docs/`，带 YAML front matter。
- **一键发布**：从 Markdown + SVG 卡片图标到页面、清单、字体子集、RSS 全链路自动化（见 [发布 Skill](#发布-skill)）。
- **代码高亮**：生成器基于 Pygments，支持多种语言与行号 / 复制按钮等增强。
- **字体子集**：按实际用字裁剪自建圆体，减小体积（见 [字体子集与订阅](#字体子集与订阅)）。
- **内嵌 SVG 图标**：每篇文章在清单中登记一枚内联 SVG，作为卡片封面。

### 状态系统

- 实时状态展示：在线 / 离开 / 忙碌 / 离线 + 自定义文案。
- 展示当前前台程序名与窗口标题（支持黑 / 白名单过滤，保护隐私）。
- 基于键鼠空闲时长自动在「在线 / 离开」间切换。
- 服务端数据**原子写入 + 文件锁**，避免 Nginx 读到半截 JSON；Token 常量时间比较防时序攻击。
- 客户端常驻系统托盘，可手动切换状态、立即推送、双击刷新。
- 支持电源事件（睡眠 / 休眠前、恢复后自动推送）与按程序匹配的状态规则。

---

## 目录结构

```text
ttwe77s-homepage/
├── index.html                 # 站点主页（首页 + 文章列表两屏）
├── ttwe77.html                # 「关于我」页面
├── ttwe77old.html             # 旧版「关于我」页面备份
├── links.html                 # 链接页（由 tools/links 生成）
├── rss.xml                    # 站点订阅源（由 tools/rss 生成）
├── LICENSE                    # MIT 许可证
├── README.md
├── .gitignore
│
├── blog/                      # 博客内容目录
│   ├── index.ini              # 分页向导：只写 #include
│   ├── pages/
│   │   └── page*.ini          # 分页清单（每行登记一篇博文）
│   ├── fonts/
│   │   ├── *.woff2            # 子集化后的自建圆体
│   │   ├── charset-used.txt   # 实际用字集合
│   │   └── subset.json        # 子集生成状态
│   └── *.html（生成的页面文件，由清单登记并随站点部署）
│
├── status/                    # 状态展示页
│   ├── index.html             # 轮询 JSON 展示状态（主卡片）
│   └── data/
│       └── device-01.json     # 状态数据（运行时生成，被 .gitignore 忽略）
│
├── src/                       # 站点静态资源
│   ├── head.*  ttwe77.*       # 头像 / logo（avif/webp/png）
│   ├── ap.* gold.* pyroxene.* # 资源图标
│   ├── favicon.* og-cover.jpg # 站点图标 / 分享封面
│   ├── cursors/               # 自定义光标（normal/link/help）
│   ├── kei/                   # 角色立绘与互动语音（ogg/opus/avif）
│   ├── links/                 # 友链页配图
│   └── ttf/                   # 字体源文件与 to_woff2.py 转换脚本
│
├── libs/
│   └── ba-click-fx.js         # 点击粒子特效库
│
├── errorpage/                 # 自定义错误页
│
├── tools/                     # 生成与运维工具链（开发机运行）
│   ├── genblog/               # 博客生成器
│   │   ├── md2page.py         # Markdown → 页面（依赖 Pygments）
│   │   ├── split_page.py      # 从样板页拆分模板片段到 parts/
│   │   ├── subset_fonts.py    # 字体子集化
│   │   ├── hover-hint.py      # 术语悬浮提示编辑 GUI（PyQt5）
│   │   ├── docs/              # Markdown 文章源文件
│   │   ├── parts/             # 页面模板片段
│   │   ├── data/              # 字表等中间数据
│   │   └── sample.html        # 样板页
│   ├── links/                 # 链接页生成器（build.py / links.json / linkseditor.pyw）
│   ├── rss/                   # 订阅生成器（genrss.py）
│   ├── app/                   # 独立 Web 应用 / PWA（证书查看、考试、聊天等）
│   ├── analyze163music.py     # 网易云歌单分析
│   ├── deal-png-jpg.py        # 图片批量处理
│   └── minify_html.py         # HTML 压缩
│
├── skills/
│   └── genblog-publish/       # 一键博客发布 Skill
│       ├── SKILL.md
│       ├── scripts/           # publish_blog.py（单入口确定性构建）
│       └── references/        # 工作流 / front matter / 悬浮提示规范
│
├── 服务端/                    # 状态 API 服务端
│   ├── status_server.cpp      # C++ 实现（cpp-httplib，支持 HTTPS，当前使用）
│   ├── status_server.py       # Python Flask 实现（已淘汰，仅供历史参考）
│   └── libs/
│       ├── httplib.h          # 头文件依赖
│       ├── json.hpp           # 头文件依赖
│       └── *-LICENSE.txt      # 引用库许可证
│
└── 客户端/                    # Windows 个人状态记录器（托盘）
    ├── client.cpp             # 源码（WinHTTP + Win32 托盘）
    ├── PersonalStatusRecorder.exe  # 当前可执行文件（个人状态记录器）
    ├── appicon.svg            # 图标源（SVG）
    ├── appicon.ico            # 图标（由 SVG 转换，多尺寸）
    ├── appicon.rc / .res      # 图标资源脚本与编译产物
    └── client.ini             # 运行配置（由程序自动生成，被 .gitignore 忽略）
```

> 开发工具产生的中间目录（`.git/`、`.workbuddy/`、`.trae/`、`.screenshots/` 等）未在上表展开，其中若干已加入 `.gitignore`。

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | 原生 HTML / CSS（CSS 变量设计令牌）/ 原生 JavaScript，无框架、无打包 |
| 博客生成 | Python 3 + Markdown 渲染 + Pygments（代码高亮）+ 字体子集脚本 |
| 状态服务端 | C++17 + cpp-httplib + nlohmann/json，可选 OpenSSL (HTTPS) |
| 状态客户端 | C++17 + WinHTTP + Win32 API（托盘、DPI 感知、UWP 适配） |
| 托管 | Nginx 静态托管 |

---

## 快速开始

### 1. 启动静态站点

站点是纯静态文件，用任意静态服务器托管即可，例如：

```bash
python -m http.server 8080
# 浏览器打开 http://127.0.0.1:8080
```

### 2. 启动状态服务端

服务端当前使用 C++ 实现，在 `服务端/` 目录下编译运行（头文件位于同目录 `libs/`）：

```bash
cd 服务端

# 仅 HTTP
g++ -std=c++17 -O2 -pthread -o status_server status_server.cpp -I .

# HTTPS（需要 OpenSSL）
g++ -std=c++17 -O2 -pthread -DCPPHTTPLIB_OPENSSL_SUPPORT -o status_server status_server.cpp -I . -lssl -lcrypto

./status_server
```

> 首次运行若找不到配置，会在同目录生成 `status_server.ini` 模板；编辑后重新运行。
> 同时会自动生成 Token 文件 `.api_token` 并打印 Token 前缀。

> `status_server.py`（Python / Flask 实现）**已淘汰，仅供历史参考**，不再维护；实际部署请使用上面的 C++ 版本。服务端默认监听 `127.0.0.1:5000`，状态文件路径在 `status_server.ini` 的 `[storage] status_file` 中配置（生产环境指向站点目录下的 `status/data/device-01.json`）。

### 3. 运行状态客户端

编译（MinGW-w64，在 `客户端/` 目录下）：

```cmd
cd 客户端

# 1. SVG 图标转 ICO（ImageMagick）
magick -background none appicon.svg -define icon:auto-resize=256,128,64,48,32,16 appicon.ico

# 2. 编译图标资源（windres）
windres --use-temp-file appicon.rc -O coff -o appicon.res

# 3. 编译主程序（g++，图标已内嵌，单文件分发）
g++ -std=c++17 -O2 -o PersonalStatusRecorder.exe client.cpp appicon.res -lwinhttp -lshell32 -luser32 -lgdi32
```

首次运行会生成 `client.ini` 模板并弹窗提示，至少填写 `[server] url`、`[server] api_key`、`[status] name` 后再次运行即可常驻托盘。软件名为「个人状态记录器」，托盘图标与 exe 图标均为内嵌的 `appicon.ico`。

---

## 状态系统详解

### 数据文件

服务端写入的 `status/data/device-01.json` 结构示例：

```json
{
  "name": "用户名",
  "status": "online",
  "status_text": "在线",
  "program_name": "WindowsTerminal",
  "program_title": "命令提示符",
  "since": "2026-10-02T23:17:00+08:00",
  "server_updated": "2026-10-02T23:17:00+08:00"
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `name` | string | 名称（≤32 字符，不能为空） |
| `status` | enum | `online` / `away` / `busy` / `offline` |
| `status_text` | string | 状态文案（≤32 字符），留空按状态自动填「在线/离开/忙碌/离线」 |
| `program_name` | string | 当前前台程序名（≤64 字符） |
| `program_title` | string | 前台窗口标题（≤64 字符，仅白名单命中时上报） |
| `since` | ISO8601 | 当前状态开始时间，不传则取服务端当前时间 |
| `server_updated` | ISO8601 | 服务端最后写入时间（由服务端生成，客户端不可控） |

> 前端在 `server_updated` 超过 **5 分钟** 未更新时，会将其显示为「离线（数据已过期）」。

### HTTP API

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| `GET` | `/api/status` | 否 | 读取当前状态，返回 `{ok, status}` |
| `POST` | `/api/status` | 是 | **全量覆盖**状态；未提供的字段回落默认值 |
| `GET` | `/api/health` | 否 | 健康检查，返回 `{ok, time}` |
| `OPTIONS` | `/api/*` | 否 | CORS 预检（204） |

请求体示例：

```json
{
  "name": "ttwe77",
  "status": "online",
  "status_text": "在线",
  "program_name": "WindowsTerminal",
  "program_title": "命令提示符",
  "since": "2026-10-02T23:17:00+08:00"
}
```

请求体上限 **64KB**；非 JSON 对象、非法状态值、超长字段会返回 `400`。

### 鉴权

写操作（`POST`）需携带 Token，支持三种传递方式（优先级从高到低）：

1. `X-API-Key: <token>`
2. `Authorization: Bearer <token>`
3. `?key=<token>`

Token 来源：环境变量 / 配置里的静态 `api_key`，或自动生成的 `.api_token` 文件（首次运行生成，权限 0600）。比较使用常量时间算法，防时序侧信道。

### 服务端配置

服务端通过 `status_server.ini` 配置，启动时若不存在会生成模板：

```ini
[server]
bind = 127.0.0.1
port = 5000
cors = false

[https]
enabled = false
cert_file =
key_file =

[storage]
status_file =          # 状态文件绝对路径（须与 nginx root 一致）
token_file =           # 留空使用可执行文件同目录 .api_token

[auth]
api_key =              # 可选静态 Key
```

命令行：`status_server -c <config> | --init | -h`

> 已淘汰的 `status_server.py` 曾通过环境变量配置（`STATUS_FILE` / `STATUS_API_KEY` / `STATUS_TOKEN_FILE` / `STATUS_BIND` / `STATUS_PORT` / `STATUS_CORS`），仅供历史参考，不再维护。

### 客户端配置

`client.ini`（UTF-8 带 BOM）主要字段：

```ini
[server]
; 状态接口地址（必填）
url = https://your-server:5000/api/status

; 健康检查地址，留空则根据 url 自动推导
health_url =

; API Key（必填）；留空则尝试读取同目录 .api_token
api_key = <你的 API Key>

; 请求超时（毫秒）
timeout_ms = 5000

; 持续推送间隔（秒）；>0 常驻定时推送，<=0 只推送一次后退出
interval_seconds = 10

[status]
; 你的名称（必填，用于服务端识别身份）
name = ttwe77

[auto]
; 是否自动探测前台程序名并写入 program_name
detect_program = true

; 是否根据键鼠空闲时长自动切换 away / online
; 注意：在托盘菜单手动选择状态后，本次运行不再被自动检测覆盖
detect_status = true

; 判定离开的空闲分钟数
idle_minutes = 3

[filter]
; 程序名白名单：命中时才抓取前台窗口标题（program_title）
; 逗号 / 分号 / 竖线分隔；不区分大小写；可省略 .exe 后缀
program_whitelist = explorer,ShellExperienceHost

; 程序名黑名单：命中时脱敏处理，优先级高于白名单
program_blacklist =

[since_rules]
; 当 program_name 命中左侧模式时，覆盖右侧列出的字段
; 左值：普通程序名（不区分大小写、可省略 .exe），或 re: / regex: 开头的正则
; 右值：一个或多个 "字段=值"，用分号分隔；只应用第一条命中的规则
; 可覆盖字段：status / status_text / program_name / program_title / since / name
;   since 必须是 ISO 8601 时间（如 2026-10-04T22:17:21+08:00）或 now
;   status_text 用来写文案（摸鱼中 / 开会中），不要塞进 since
; 示例：chrome = status=busy; status_text=摸鱼中
LockApp=status=away;program_title=主人的电脑开锁屏了~

[presets]
; 托盘菜单「设置状态」子菜单里的常用状态：显示名称 = 状态|文案
会议中 = busy|开会
午休 = away|午休

[power]
; 电源事件：睡眠/休眠前与恢复后自动推送；留空表示不推送
suspend_status = offline
resume_status = online
```

**过滤规则**：黑名单优先级高于白名单。

- 命中黑名单 → `program_name` 显示为「黑名单命中，不予显示」，标题置空；
- 命中白名单 → 抓取前台窗口标题填入 `program_title`；
- 其余 → `program_title` 置空。

### 客户端命令行

```text
PersonalStatusRecorder.exe [选项]
  -c, --config <文件>   指定 INI 配置文件（默认 exe 同目录 client.ini）
      --url <地址>      覆盖接口地址
      --key <token>     覆盖 API Key
      --timeout <毫秒>  覆盖超时

      --name <名称>     覆盖 name
      --status <状态>   online / away / busy / offline
      --text <文案>     覆盖 status_text
      --program <程序>  覆盖 program_name
      --since <时间>    覆盖 since（ISO8601，或 now）

      --interval <秒>   持续推送间隔；0 表示只推送一次
      --once            只推送一次后退出（覆盖 interval_seconds）

      --get             查询当前状态
      --health          健康检查
  -v, --verbose         输出完整响应
  -q, --quiet           只输出错误
  -h, --help            显示帮助
```

退出码：`0` 成功 / `1` 请求或接口失败 / `2` 参数或配置错误。

托盘功能：右键菜单可切换状态（在线/离开/忙碌/离线）、立即推送、退出；双击托盘图标立即刷新。

---

## 博客与发布工具链

博客页面、清单、字体与订阅都由 `tools/` 下的脚本生成；本节的清单与字段只说明机制，不罗列具体文章内容。

### 内容生产流程

```text
Markdown（tools/genblog/docs/，带 YAML front matter）
  → md2page.py 渲染为页面（Pygments 代码高亮、目录、字体模态框等）
  → 登记到 blog/pages/ 的分页清单
  → subset_fonts.py 按实际用字重建 blog/fonts/
  → genrss.py 更新根目录 rss.xml
```

`tools/genblog/parts/` 存放从样板页 `sample.html` 拆出的模板片段（head、style、文章正文、目录、顶栏、页脚等），`build.bat` 可重新拆分并烧录示例文章。`hover-hint.py` 是一个 PyQt5 编辑 GUI，用于给术语加悬浮解释。

### 页面清单

`blog/index.ini` 只声明分页顺序，每行一个 `#include`：

```ini
#include pages/page1.ini
#include pages/page2.ini
```

`blog/pages/page*.ini` 每行登记一篇博文，字段以 `|` 分隔：

```text
文件 | 标题 | 日期 | 分类 | 标签(逗号分隔) | 描述 | 内嵌SVG图标
```

| 列 | 字段 | 说明 |
| --- | --- | --- |
| 0 | `file` | 页面文件名，须以 `.html` / `.htm` 结尾，否则该行忽略 |
| 1 | `title` | 标题，缺省时由文件名推导 |
| 2 | `date` | 日期字符串（原样展示） |
| 3 | `category` | 分类，缺省「未分类」 |
| 4 | `tags` | 标签，逗号 / 中文逗号分隔，最多展示 3 个 |
| 5 | `desc` | 摘要描述 |
| 6+ | `icon` | 内嵌 SVG（原样注入），缺省使用兜底图标 |

> 以 `#` 或 `;` 开头的行视为注释；生成的页面与清单配套使用，卡片链接指向 `blog/` 下对应文件。

### 字体子集与订阅

- `tools/genblog/subset_fonts.py` 扫描站点实际用字，把自建圆体裁剪为 `blog/fonts/*.woff2`，并写出 `charset-used.txt` 与 `subset.json`。新增文章后应重跑，否则生僻字会回退到系统字体。
- `tools/rss/genrss.py` 依据清单生成订阅数据：先写 `tools/rss/rss.xml` 供人工核对，终端输入 `y` 后才覆盖根目录 `rss.xml`。

### 发布 Skill

`skills/genblog-publish/` 把上述流程封装为一步：提供 Markdown 路径 + SVG 图标，即可完成 front matter 检查 / 补全、悬浮提示插入、渲染、清单登记、字体子集与 RSS 更新。要点：

- 调用 `scripts/publish_blog.py`，可用 `--dry-run` 预演、`--skip-fonts` / `--skip-rss` 跳过阶段；
- 生成器会用当前 Python 解释器拉起所有子步骤，需确保该解释器已安装 `pygments`；
- 优先使用项目内副本；若用用户目录副本需显式传 `--root <项目根目录>`；
- **该 Skill 不执行任何 git 写操作**（不 add / commit / push），结束后会列出变更文件供人工审阅。

---

## 辅助工具

| 工具 | 位置 | 用途 |
| --- | --- | --- |
| 链接页生成器 | `tools/links/build.py` | 由 `links.json` 生成 `links.html`；`linkseditor.pyw` 提供可视化编辑 |
| 订阅生成器 | `tools/rss/genrss.py` | 生成 `rss.xml` |
| 歌单分析 | `tools/analyze163music.py` | 分析网易云「我喜欢的音乐」，产出音乐偏好画像 |
| 图片处理 | `tools/deal-png-jpg.py` | 图片批量转换 / 处理 |
| HTML 压缩 | `tools/minify_html.py` | 压缩发布用 HTML |
| 字体转换 | `src/ttf/to_woff2.py` | TTF → WOFF2 |
| 独立应用 | `tools/app/` | 证书查看、在线考试、聊天等可独立部署的 Web 应用 / PWA |

---

## 构建与编译

| 产物 | 命令 |
| --- | --- |
| 个人状态记录器 `PersonalStatusRecorder.exe` | 见 [快速开始 · 3](#3-运行状态客户端)：`windres` 编译图标资源，再用 `g++` 编译 `client.cpp` |
| 状态服务端（HTTP） | `cd 服务端 && g++ -std=c++17 -O2 -pthread -o status_server status_server.cpp -I .` |
| 状态服务端（HTTPS） | `cd 服务端 && g++ -std=c++17 -O2 -pthread -DCPPHTTPLIB_OPENSSL_SUPPORT -o status_server status_server.cpp -I . -lssl -lcrypto` |
| 博客页面 / 清单 / 字体 / RSS | 见 [发布 Skill](#发布-skill)，由 `scripts/publish_blog.py` 串起 |
| 静态站点 | 无需构建，直接托管即可 |

静态站点无依赖、无打包，修改后刷新浏览器即可（可能需要清缓存）。

---

## 部署（Nginx）

站点 + 状态 JSON 建议由 Nginx 统一托管：

1. 配置好你的 Nginx 服务器。
2. 将静态产物上传到 Nginx 的 `root` 目录：`index.html`、`ttwe77.html`、`links.html`、`rss.xml`、`blog/`（含生成的页面与 `fonts/`）、`status/`、`src/`、`libs/`、`errorpage/`。源码与开发配置（`服务端/`、`客户端/`、`tools/`、`skills/`、`.git/` 等）无需上传。
3. 启动状态服务端，并开放 `/api/status`（可用反向代理或独立端口）。
4. 确保服务端的 `status_file`（`status_server.ini` 的 `[storage]`）与 Nginx 静态路径**指向同一个文件**，即 `root/status/data/device-01.json`。
5. 确认 `status/data/` 目录对服务端可写，且 `.api_token` / `status_server.ini` 等敏感文件不在 Nginx 可访问路径下。

> 需自行准备 Nginx 发行版。

---

## 设计规范与资源

- **设计令牌**：所有颜色、圆角、阴影、字体统一定义在 `:root` CSS 变量中（主色 `#21a5e3`），站点内多处复用（如 `status/index.html` 复用 `/index` 的变量）。
- **降级动效**：`@media (prefers-reduced-motion: reduce)` 下关闭动画。
- **多格式资源**：`<picture>` + `<source>` 按 `avif → webp → png/jpg` 回退。
- **自定义光标**：`src/cursors/{normal,link,help}.cur`。
- **点击特效**：`libs/ba-click-fx.js` 提供 `BAClickFX` 类（可配置拖尾、合成模式）。
- **图标与分享封面**：`src/favicon.*`、`src/apple-touch-icon.png`、`src/og-cover.jpg`。

---

## 开发约定

- 站点为纯静态、零依赖，新增页面尽量保持单文件风格与既有设计令牌一致。
- 博客新增内容走 `tools/genblog/` 生成链，不要手写页面或手改清单；发布交由 `skills/genblog-publish/` 处理，并人工检查变更后再决定是否提交。
- 隐私相关：来源程序信息受白 / 黑名单控制，敏感程序请加入 `program_blacklist`。
- 密钥相关：API Key、Token 不要写进 README 或提交到仓库；`client.ini`、`.api_token`、`status/data/` 均已在 `.gitignore` 中排除。
- 降低前后端占用的资源。

---

## 许可证

本项目基于 MIT License 发布，Copyright (c) 2026 ttwe77。

第三方依赖许可见 `服务端/libs/*-LICENSE.txt`（cpp-httplib、nlohmann/json）。
