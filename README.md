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
- [博客系统](#博客系统)
- [构建与编译](#构建与编译)
- [部署（Nginx）](#部署nginx)
- [设计规范与资源](#设计规范与资源)
- [开发约定](#开发约定)
- [许可证](#许可证)

---

## 项目概览

本项目由三部分组成，彼此解耦、可独立运行：

| 模块 | 目录 | 说明 |
| --- | --- | --- |
| **静态站点** | 仓库根目录 | 单文件 `index.html` 为主页（含首页、文章列表两屏），`ttwe77.html` 为「关于我」页；纯静态，无构建步骤。 |
| **状态服务端** | 服务端 | 提供 `GET/POST /api/status` 接口，把状态原子写入 JSON 文件，供 Nginx 静态托管。有两种实现：Python(Flask) 与 C++(cpp-httplib)。 |
| **状态客户端** | 客户端     | Windows 托盘程序，探测前台程序与键鼠空闲状态，定时向服务端推送。 |

站点通过 `status/index.html` 每 10 秒轮询 `/status/data/device-01.json`，实时展示我的在线状态。

---

## 功能特性

### 静态站点（主页）

- **仿蔚蓝档案风格**

- **双屏分页**：首页（Masthead 展示）+ 文章列表页，圆点导航 / 页内滑动切换，带 `--page-duration` 过渡动画。
- **文章清单动态生成**：文章列表由 `blog/index.ini` 的分页向导 + `blog/pages/` 分页清单驱动，前端按需加载、分页器按页数渲染。
- **仿游戏化 UI**：顶栏含体力(AP) / 金币 / 青曜石等资源展示、体力恢复弹窗、`toast` 提示。
- **自建音乐播放器**：浮动播放器支持播放列表、进度拖动、音量、播放模式切换（资源见 `src/ShootingStars.*`）。
- **点击特效**：引入 `libs/ba-click-fx.js`，实现点击/拖尾粒子特效。
- **自定义光标**：普通 / 链接 / 帮助三种 `.cur` 光标（`src/cursors/`）。
- **响应式与无障碍**：适配移动端、支持 `prefers-reduced-motion` 动效降级、语义化标签与 ARIA。
- **资源多格式**：图片提供 `avif / webp / png(jpg)` 多格式回退，音频提供 `opus / ogg / mp3 / m4a`。

### 状态系统

- 实时状态展示：在线 / 离开 / 忙碌 / 离线 + 自定义文案。
- 展示当前前台程序名与窗口标题（支持黑 / 白名单过滤，保护隐私）。
- 基于键鼠空闲时长自动在「在线 / 离开」间切换。
- 服务端数据**原子写入 + 文件锁**，避免 Nginx 读到半截 JSON；Token 常量时间比较防时序攻击。
- 客户端常驻系统托盘，可手动切换状态、立即推送、双击刷新。

---

## 目录结构

```text
ttwe77s-homepage/
├── index.html                 # 站点主页（首页 + 文章列表两屏）
├── ttwe77.html                # 「关于我」页面
├── ttwe77old.html             # 旧版「关于我」页面备份
├── LICENSE                    # MIT 许可证
├── .gitignore
│
├── blog/                      # 博客清单（INI 格式）
│   ├── index.ini              # 分页向导：只写 #include
│   └── pages/
│       ├── page1.ini          # 分页清单（每行一篇文章）
│       └── page*.ini
│
├── status/                    # 状态展示页
│   ├── index.html             # 轮询 JSON 展示状态（主卡片）
│   └── data/
│       └── device-01.json     # 状态数据（nginx 静态托管）
│
├── src/                       # 站点静态资源
│   ├── head.*  ttwe77.*       # 头像 / logo（avif/webp/png）
│   ├── ap.* gold.* pyroxene.* # 资源图标
│   ├── favicon.* og-cover.jpg # 站点图标 / 分享封面
│   ├── cursors/               # 自定义光标（normal/link/help）
│   └── kei/                   # 角色立绘与互动语音
│
├── libs/
│   └── ba-click-fx.js         # 点击粒子特效库
│
├── 服务端/                    # 状态 API 服务端
│   ├── main.py                # Python Flask 实现（不推荐，跨平台）
│   ├── status_server.cpp      # C++ 实现（cpp-httplib，支持 HTTPS）
│   └── libs/
│       ├── httplib.h          # 头文件依赖
│       ├── json.hpp           # 头文件依赖
│       └── *-LICENSE.txt      # 引用库许可证
│
├── 客户端/                    # Windows 状态客户端（托盘）
│   ├── main.cpp               # 源码（WinHTTP + Win32 托盘）
```

---

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | 原生 HTML / CSS（CSS 变量设计令牌）/ 原生 ES Module，无框架、无打包 |
| 状态服务端（Python） | Python 3 + Flask + 标准库文件锁（`msvcrt` / `fcntl`） |
| 状态服务端（C++） | C++17 + cpp-httplib + nlohmann/json，可选 OpenSSL(HTTPS) |
| 状态客户端 | C++17 + WinHTTP + Win32 API（托盘、DPI 感知、UWP 适配） |
| 托管 | Nginx 静态托管 |

---

## 快速开始

### 1. 启动静态站点

站点是纯静态文件，任意静态服务器即可。

### 2. 启动状态服务端

**方式 A：C++（推荐）**

```bash
# 仅 HTTP
g++ -std=c++17 -O2 -pthread -o status_server status_server.cpp -I .

# HTTPS（需要 OpenSSL）
g++ -std=c++17 -O2 -pthread -DCPPHTTPLIB_OPENSSL_SUPPORT -o status_server status_server.cpp -I . -lssl -lcrypto

./status_server
# 首次运行会在同目录生成 status_server.ini 模板
```

> 首次运行会自动生成 Token 文件 `.api_token`，并打印 Token 前缀。

**方式 B：Python（不推荐）**

```powershell
pip install flask
cd 服务端
python main.py
```

默认监听 `127.0.0.1:5000`，并把状态写入
`device-01.json`。

### 3. 运行状态客户端

编译（MinGW-w64）：

```powershell
g++ -std=c++17 -O2 -o client.exe client.cpp -lwinhttp -lshell32 -luser32 -lgdi32
```

首次运行会生成 `client.ini` 模板并弹窗提示，至少填写 `[server] url`、`[server] api_key`、`[status] name` 后再次运行即可常驻托盘。

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

**Python 版**通过环境变量配置：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `STATUS_FILE` | `device-01.json` | 状态文件绝对路径（须与 Nginx root 一致） |
| `STATUS_API_KEY` | 空 | 可选静态 API Key |
| `STATUS_TOKEN_FILE` | 同目录 `.api_token` | Token 文件位置 |
| `STATUS_BIND` | `127.0.0.1` | 监听地址 |
| `STATUS_PORT` | `5000` | 监听端口 |
| `STATUS_CORS` | `0` | 是否启用 CORS（`1` 开启） |

**C++ 版**通过 `status_server.ini` 配置，启动时若不存在会生成模板：

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
status_file =          # status.json 绝对路径（须与 nginx root 一致）
token_file =           # 留空使用可执行文件同目录 .api_token

[auth]
api_key =              # 可选静态 Key
```

命令行：`status_server -c <config> | --init | -h`

### 客户端配置

`client.ini`（UTF-8 带 BOM）主要字段：

```ini
; ============================================================
; status-client 配置文件
; 首次运行由程序自动生成，请按需修改后保存
; 编码: UTF-8（带 BOM）
; ============================================================

[server]
; 状态接口地址（必填）
url = https://ttwe77-server:5000/api/status

; 健康检查地址，留空则根据 url 自动推导
health_url =https://ttwe77-server:5000/api/health

; API Key（必填）；留空则尝试读取同目录 .api_token
api_key = E6brdl7pFZgxRTvytITY_IbT5Bt4ZvHTYTZjgu9y8eY

; 请求超时（毫秒）
timeout_ms = 5000

; 持续推送间隔（秒）
;   >0 : 每隔该秒数推送一次（托盘常驻，可在托盘菜单退出）
;   <=0: 只推送一次后退出
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
; 例：chrome,firefox,code,windowsterminal
program_whitelist =explorer,ShellExperienceHost,ShellHost

; 程序名黑名单：命中时 program_name 变为「黑名单」，program_title 置空
; 黑名单优先级高于白名单
; 例：wechat,kpassword,1password
program_blacklist =zhuiyun

[since_rules]
; 规则：当 program_name 命中左侧模式时，覆盖右侧列出的字段
; 左值：普通程序名（不区分大小写、可省略 .exe），或以 re: / regex: 开头的正则
; 右值：一个或多个 "字段=值"，用分号分隔；只应用第一条命中的规则
; 提示：since 字段必须是 ISO 8601 时间，详见 [since_rules] 段说明。
;
; 可覆盖字段：
;   status         online / away / busy / offline
;   status_text    状态文案（摸鱼中 / 开会中 …… 用这个字段，不要塞进 since）
;   program_name   上报的程序名（可用来隐藏真实程序名）
;   program_title  窗口标题
;   since          状态起始时间，必须是 ISO 8601 时间，例如 2026-10-04T22:17:21+08:00
;                  也可以写 now 让客户端用“当前时间”
;                  注意：不能写“现在”“摸鱼中”这类文案，否则服务端会返回 400
;   name           上报的名称
;
; 示例：
;   chrome                = status=busy; status_text=摸鱼中
;   re:^code$             = status=busy; status_text=码代码中; program_title=
;   re:^(devenv|rider64)$ = status=busy; status_text=IDE 中
;   wechat                = status=busy; status_text=聊天中; program_name=通讯工具
;
; 如果需要固定 since 为一个具体时间（必须为 ISO 8601）：
;   chrome                = status=busy; status_text=摸鱼中; since=2026-10-04T12:00:00+08:00
;
; 如果需要 since 跟随当前时间动态刷新（每次切换程序时重置），留空即可：
;   chrome                = status=busy; status_text=摸鱼中
;
; ⚠ 常见错误：
;   错误：chrome = since=现在            （“现在”不是 ISO 时间，服务端 400）
;   错误：chrome = since=摸鱼中          （同理）
;   正确：chrome = status=busy; status_text=摸鱼中
;   正确：chrome = since=2026-10-04T12:00:00+08:00
;   正确：chrome = since=now             （客户端会替换成当前时间）
LockApp=status=away;program_title=主人的电脑开锁屏了~

[presets]
; 托盘菜单「设置状态」子菜单里的常用状态
; 格式：显示名称 = 状态|文案；文案可省略（自动用默认文案）
; 状态只能是 online / away / busy / offline
; 例：
会议中 = busy|开会
午休 = away|午休
专注中 = busy|请勿打扰
;

[power]
; 电源事件：睡眠/休眠前与恢复后自动推送
; 状态只能是 online / away / busy / offline；留空表示不推送
; 例：suspend_status = offline  （睡眠前标记为离线）
;     resume_status  = online   （恢复后自动回到在线）
; 若 resume_status 留空，则恢复后推送当前状态
suspend_status = offline
resume_status  = online

```

**过滤规则**：黑名单优先级高于白名单。

- 命中黑名单 → `program_name` 显示为「黑名单命中，不予显示」，标题置空；
- 命中白名单 → 抓取前台窗口标题填入 `program_title`；
- 其余 → `program_title` 置空。

### 客户端命令行

```text
main.exe [选项]
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

## 博客系统

文章列表**不写死在 HTML 里**，而是通过 INI 清单动态加载，便于维护。

### 分页向导：`blog/index.ini`

只声明分页顺序，每行一个 `#include`：

```ini
#include pages/page1.ini
#include pages/page2.ini
#include pages/page*.ini
```

### 分页清单：`blog/pages/page*.ini`

每行一篇文章，字段以 `|` 分隔：

```text
文件 | 标题 | 日期 | 分类 | 标签(逗号分隔) | 描述 | 内嵌SVG图标
```

示例：

```ini
css-variables.html | CSS 变量实战 | 2026-03-18 | 前端 | CSS,设计系统 | 用变量统一管理设计令牌的实践笔记 | <svg ...></svg>
```

字段说明：

| 列 | 字段 | 说明 |
| --- | --- | --- |
| 0 | `file` | 文章文件名，**必须以 `.html`/`.htm` 结尾**，否则该行忽略 |
| 1 | `title` | 标题，缺省时由文件名推导 |
| 2 | `date` | 日期字符串（原样展示） |
| 3 | `category` | 分类，缺省「未分类」 |
| 4 | `tags` | 标签，逗号 / 中文逗号分隔，最多展示 3 个 |
| 5 | `desc` | 摘要描述 |
| 6+ | `icon` | 内嵌 SVG（原样注入），缺省使用兜底图标 |

> 以 `#` 或 `;` 开头的行视为注释；文章详情页需放在 `blog/` 目录下，卡片链接为 `blog/<file>`。

---

## 构建与编译

| 产物 | 命令 |
| --- | --- |
| 状态客户端 `main.exe` | `g++ -std=c++17 -O2 -o main.exe main.cpp -lwinhttp -lshell32 -luser32 -lgdi32` |
| 状态服务端（HTTP） | `g++ -std=c++17 -O2 -pthread -o status_server status_server.cpp -I .` |
| 状态服务端（HTTPS） | `g++ -std=c++17 -O2 -pthread -DCPPHTTPLIB_OPENSSL_SUPPORT -o status_server status_server.cpp -I . -lssl -lcrypto` |
| 静态站点 | 无需构建，直接托管即可 |

静态站点无依赖、无打包，修改后刷新浏览器即可（可能需要清缓存）。

---

## 部署（Nginx）

站点 + 状态 JSON 建议由 Nginx 统一托管：

1. 配置好你的Nginx服务器。
2. 将除了`服务端/`、`客户端/`、`.gitignore`上传到Nginx的html目录或Nginx配置文件中的root指定目录。
3. 启动状态服务端。
4. 确保 `storage.status_file`（服务端）与 Nginx 的静态路径**指向同一个文件**。

> 需自行准备 Nginx 发行版。

---

## 设计规范与资源

- **设计令牌**：所有颜色、圆角、阴影、字体统一定义在 `:root` CSS 变量中（主色 `#21a5e3`），站点内多处复用（如 `status/index.html` 复用 `/index` 的变量）。
- **降级动效**：`@media (prefers-reduced-motion: reduce)` 下关闭动画。
- **多格式资源**：`<picture>` + `<source>` 按 `avif → webp → png/jpg` 回退。
- **自定义光标**：`src/cursors/{normal,link,help}.cur`。
- **点击特效**：`libs/ba-click-fx.js` 提供 `BAClickFX` 类（可配置拖尾、合成模式）。

---

## 开发约定

- 站点为纯静态、零依赖，新增页面尽量保持单文件风格与既有设计令牌一致。
- 隐私相关：来源程序信息受白 / 黑名单控制，敏感程序请加入 `program_blacklist`。
- 降低前后端占用的资源

---

## 许可证

本项目基于 MIT License发布，Copyright (c) 2026 ttwe77。

第三方依赖许可见 `服务端/libs/*-LICENSE.txt`（cpp-httplib、nlohmann/json）。