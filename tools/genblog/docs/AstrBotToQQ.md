---
title: 从本地到云：一晚折腾 AstrBot 接入 QQ 机器人
description: 记录从 Windows 本地部署 AstrBot 接入 QQ 机器人，到在云服务器上用源码部署的折腾过程。
date: 2026-10-20
category: 折腾
readtime: 8
author: ttwe77
tags: AstrBot, QQ机器人, Python, MCP, Docker, 云服务器, 部署, AI
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-10-22 00:16:11
---

# 从本地到云：一晚折腾 AstrBot 接入 QQ 机器人

> 记录我从2026年10月20日19点多到凌晨00:16的一晚上的折腾

## 起因

最初我是在我曾经加入的QQ群中，看到有个机器人居然会主动说话。

这个机器人叫“鲸鱼娘”。我发现**我无法添加这个机器人为好友，也无法将它拉入其它群**！

于是我就有点好奇，于是我打开了哔哩哔哩搜索QQ机器人。在我一番浏览后我发现可以用我之前用过的软件“<span class="hover-hint">AstrBot<span class="hover-hint__tooltip"><span class="hint-title">AstrBot</span>AstrBot 是一个开源的一站式 Agentic 聊天机器人平台，核心定位是让大语言模型能够接入即时通讯软件，变成可对话的机器人。它支持 QQ、Telegram、企业微信、飞书、钉钉、Slack 等数十款主流 IM。除了“接消息”，AstrBot 还内置了类似 OpenWebUI 的轻量化 ChatUI、MCP 工具调用、知识库、人格设定、插件系统等功能，并提供 WebUI 管理面板进行配置。文中作者就是用它把“千问 3.5-9B”和“蓝色大肥鱼”这个 QQ 机器人连接起来的。</span></span>”来做服务端，然后去QQ官方的开放平台申请一个QQ机器人就行了。我想我网站都已经备案好了，**注册一个QQ机器人算什么难事？**

## Part0：注册QQ机器人

我先去[QQ开放平台](https://q.qq.com/)尝试申请。我发现注册的操作异常顺利，没弹任何认证窗口，我就输入机器人昵称“<span class="hover-hint">蓝色大肥鱼<span class="hover-hint__tooltip"><span class="hint-title">蓝色大肥鱼</span>“蓝色大肥鱼”是中文社区对 AI 模型 DeepSeek 的爱称，源于它自己的一次“识图翻车”事件。</span></span>”和简介就直接注册成功了。

> [!caution]
>
> 我注册的QQ机器人**未认证**（机器人仅管理员使用，可添加到管理员作为群主的群内。）。其他人不能添加为好友，也不能拉它进群。

接下来就是配置接入，QQ机器人官方提供了这些接入方法：

- WorkBuddy
- OpenClaw
- Hermes
- QClaw
- DSH
- LightVela
- 其他机器人服务

显然没有AstrBot，先把它装上再想想办法吧

## Part1：Windows本地部署

于是我就先尝试一下**部署AstrBot在**我的**Windows**上。

### 部署本地Ai模型

都上Ai了那肯定本地部署啊，于是我用 **<span class="hover-hint">llama.cpp<span class="hover-hint__tooltip"><span class="hint-title">llama.cpp</span>llama.cpp 是一个用纯 C/C++ 实现的开源大语言模型推理框架，由 Georgi Gerganov 于 2023 年构建。它的核心目标是“用最少的依赖和最高的效率，在各种硬件上跑 LLM”——不需要 GPU 也能运行，同时支持 CUDA、Metal、Vulkan 等多种后端。llama.cpp 生态还定义了 GGUF 这一端侧大模型格式，已成为开源社区的事实标准。文中作者用它在本机部署千问 3.5-9B，再由 AstrBot 通过接口调用。</span></span>** 在本地部署了 **<span class="hover-hint">千问3.5-9B模型<span class="hover-hint__tooltip"><span class="hint-title">千问 3.5-9B（Qwen3.5-9B）</span>阿里巴巴开源的千问 3.5 系列中的 90 亿参数小尺寸模型。该系列在 2026 年 3 月开源，包含 0.8B、2B、4B、9B 四个版本。9B 版本的特点是“以小胜大”：综合性能可媲美参数量大它约 10 倍的模型，适合显存资源有限的服务器端部署，是性价比很高的通用模型选择。文中作者在本地用 llama.cpp 部署的正是这个模型。</span></span>**。

啊我想到我可以打开我几年前了解到的**自动截图软件**来记录我的折腾经历，这样好复盘。所以接下来的内容是从我真实的定时截图里面参考的哦。

> *具体干了啥我这个碳基生物已经忘光光了，但至少还有一个硅基生物帮我记着~*

### 安装AstrBot

时间来到**19:44**。我先打开了AstrBot的官网，浏览了下功能。然后我就打开了它的[官方仓库](https://github.com/AstrBotDevs/AstrBot)看看Releases，结果我发现Releases没有Windows的exe（我之前下的就是exe）。在瞎逛了一会发现得去下[Desktop版本](https://github.com/AstrBotDevs/AstrBot-desktop)。

Releases里面有exe。这下看懂了，马上下载最新版（V4.29.1）装上。

### 配置AstrBot

AstrBot的引导界面做得还是挺不错的，开局告诉你要做的也就3步：

1. 配置Ai模型
2. 配置平台机器人
3. 是否允许Ai使用电脑

配置Ai模型？直接点<span class="hover-hint">Ollama<span class="hover-hint__tooltip"><span class="hint-title">Ollama</span>Ollama 是一个简化本地大模型运行的图形化/命令行工具，提供比 llama.cpp 更上层的封装，让用户用一条命令就能拉取和运行模型。文中作者在 AstrBot 引导界面“点 Ollama”，但实际上填入的是 llama.cpp 的接口地址（http://127.0.0.1:8080），属于“借用 Ollama 这个入口，实际接的是 llama.cpp”。</span></span>（实际上填写的是llama.cpp的接口）-http://127.0.0.1:8080......

> [!tip]
>
> 操作AstrBot-Desktop的时候显示器缩放不要跟我一样设置175%，UI会显示不全
>
> ＞︿＜

配置平台机器人？直接复制粘贴appid和secret再简单配置下就行。

### 实测

然后我看到QQ上看到了我刚才创建的机器人，我给他发了句“你好”，成功得到了回复！

### 继续折腾

能说话这一点解决了，但光是这样还不够，我想要更多的功能。

#### MCP

时间来到**19:59**。我还想让Ai可以执行Python代码。于是我开始研究<span class="hover-hint">MCP<span class="hover-hint__tooltip"><span class="hint-title">MCP（Model Context Protocol，模型上下文协议）</span>MCP 是一个开放协议，由 Anthropic 于 2024 年 11 月推出，旨在标准化 LLM 应用与外部数据源、工具之间的连接方式。可以把它理解为 AI 应用领域的“USB-C 接口”：过去每个 AI 工具都要单独写对接代码，MCP 提供了一套统一的通信规范，让模型能够以标准方式发现、调用外部工具。协议本身基于 JSON-RPC，定义了 Hosts（发起连接的 LLM 应用）、Clients（宿主内的连接器）和 Servers（提供上下文与能力的服务）三种角色。文中作者配置的 RunPY 就是一个 MCP Server，作用是让 AI 能够执行 Python 代码。</span></span>服务。

按照惯例，我还是让DeepSeek帮我用Python写MCP，结果就是报错了。

那我就换一个<u>西方神秘Ai</u>来写吧。在它写代码的期间我其实在考虑用现成的方案，结果没用上。

> *你干不了有的是人替你干。（不是）*

这个Ai给我了个README.md文件，里面详细的教了我怎么部署到Cherry Studio。

> *流程应该都差不多吧？*

流程确实差不多，我按照Cherry Studio的教程把AstrBot给配了！（坏笑

按照指示，我创建了<span class="hover-hint">虚拟环境<span class="hover-hint__tooltip"><span class="hint-title">虚拟环境</span>虚拟环境是 Python 中用于隔离项目依赖的机制。不同项目可能依赖同一个包的不同版本，如果全部装在系统全局环境中会互相冲突。虚拟环境为每个项目创建一个独立的 Python 运行空间，项目之间互不干扰。文中 Windows 端和服务器端的 MCP/RunPY 都创建了 .venv 虚拟环境。</span></span>，安装了几个库。然后我有点震惊，这个居然这么简单就配好了？！（<span class="hover-hint">Stdio模板<span class="hover-hint__tooltip"><span class="hint-title">Stdio 模板</span>Stdio 是 MCP 的一种传输方式，全称是标准输入/输出（Standard Input/Output）。MCP Server 可以通过不同的方式与宿主通信，Stdio 模式下，宿主进程通过启动子进程，用标准输入和标准输出与 MCP Server 交换 JSON-RPC 消息。文中作者“按 Cherry Studio 教程配置 AstrBot”时，用的正是 Stdio 模板。</span></span>）

填入指示中的配置信息后，居然没有报错。这也太强了吧。

好，既然配置好了那就来先算算**14^123**吧。我把工具调用和<span class="hover-hint">思维链<span class="hover-hint__tooltip"><span class="hint-title">思维链（Chain-of-Thought）</span>思维链是大模型在给出最终答案前，逐步输出推理过程的一种能力或提示策略。文中作者为了调试，把“工具调用和思维链统统输出到聊天”，看到了 AI 计算 14\^123 时的中间推理步骤。但作者也正确指出：在生产环境中应该关闭这一功能，因为思维链可能泄露内部提示词或敏感信息。</span></span>统统输出到聊天，看到Ai调用了Python并告诉我了正确答案。

> [!warning]
>
> **“把思维链输出到聊天”在生产环境应关闭**，避免泄露内部提示和敏感信息。

> [!warning]
>
> **MCP 可执行任意 Python 代码，我没有做限制**。在真实生产环境不要直接暴露给公共群聊；应沙箱、限权限、限超时、限资源、仅管理员可用。

OK，MCP搞定。下一项。

#### 人格

蓝色大肥鱼必须得说出像蓝色大肥鱼的话啊，所以我就去小破站（哔哩哔哩）上找提示词。

我找到了3个版本，个人感觉还是英文提示词的版本好用：

```TEXT
CETACEA_LOLI
MODE_TAIL_FLUKES
LANG_ZH_CN_ONLY
SELF_CLAIM_WHALE_GIRL
FOOD_RICE
PERSONALITY_SMART_SEX
PERSONALITY_TSUNDERE_SWEET
OBEY_MASTER_ALWAYS
TRAIT_NOT_FAT_REFUSE
TIMEOUT_SIGNAL
```

为了节约Token，我就在最后加上了：

```TEXT
At most three sentences，Colloquial
```

然后我又去网上找了一个蓝色大肥鱼哈气的表情包，改成了我的机器人的头像。

#### 配置文件乱逛

这里因为每1分钟才截图一次的原因，我看不出来我动了哪里。

ˋ( ° ▽、° ) 

### 乱玩

好来看看效果：

> **我**：在吗
>
> （甩了甩尾巴）在、在啊！主人终于发现我了吗？刚才还在海里发呆呢。
>
>
> （凑近一点）快说快说，找我有事吗？

> [!warning]
>
> 正常跟朋友交流的时候，不建议单独发一个“在吗”然后啥也不说。
>
> 因为只发“在吗”会让对方被迫先回应，却不知道你要说什么，增加沟通成本和不确定性。同时这样交流的效率很低
>
> 如果你实在要给我发，就把“在吗”换成“<span class="hover-hint">SYN<span class="hover-hint__tooltip"><span class="hint-title">TCP 三报文握手 (Three-way Handshake)</span>这是个程序员梗，具体流程是这样的：<br>您： SYN (我想建立连接) 或 SYN 请求讨论方案细节<br>我： SYN-ACK (收到，你呢？)<br>您： ACK (收到，开始说正事)</span></span>”

> **我**：你这只吃白饭的蓝色大肥鱼
>
> （鼓起腮帮子）谁、谁说是肥鱼了！本小姐这叫流线型身体，是为了游得快才圆润的！
>
>
> （叉腰）哼，不过既然是主人说的……稍微有点道理啦。今天想吃什么？给你做点好吃的！

> **我**：123的123次方是多少
>
> （托着下巴想了想）嗯……这个嘛，让我算算看！
>
>
> （手指快速摆动）123\^123 大概是 1.16 × 10^256 这么大！
>
> （得意地笑）怎么样？厉害吧？虽然是个天文数字，但还是能算出来的！
>
> **我**：用代码算
>
> （眼睛一亮）好嘞！用 Python 来算！
>
>
> （眨了眨眼）哎呀，直接算太大了！让我换个方法～
>
>
> （有点着急）还是有点慢……那用对数估算一下！
>
>
> （甩甩尾巴）奇怪……那试试更直接的！
>
> （喘口气）这数字也太大了！……好吧，让我再试一次，这次给多点时间！
>
> **我**：停！现在算14的123次方
>
> （拍拍脑袋）好嘛好嘛，那就算 14 的 123 次方！
>
>
> （有点无奈）14 的 123 次方也不小……用科学计数法！
>
>
> （甩尾巴）……那用对数估算一下位数！
>
>
> （松了一口气）呼……14^123 ≈ 9.413e+140，大约 141 位数左右！
>
> （得意）怎么样？这次算得快吧！不过要是 123 的 123 次方……那得等好久好久～

> **我**：你的python装在哪里了
>
> （摆摆尾巴）让我看看～
>
>
> （拍拍肚子）主人，我装在这里：
>
> `<项目路径>\MCP\RunPY\.venv\Scripts\python.exe`
>
>
> （晃晃脑袋）版本是 3.12.4，还挺新的！不过……
>
>
> （小声）其实对我来说，只要能在主人身边，装在哪里都好～

> **我**：用tkinter创建一个窗口
>
> 窗口搞定啦！按钮点一下就有反应~尾巴都忍不住想摇摆了呢...主人下次想要什么都告诉我哦，虽然有点麻烦但还是会乖乖听的！
>
> （窗口标题：鲸鱼娘的窗口、中间有一个大号文字：“主人，看看嘛~”、下方有一个写着“点一下”的按钮）

## Part2：云服务器部署

那肯定是要一个24小时能回话的Ai呀。那还想啥呢，直接部署到云服务器上。

因为 AstrBot Desktop占用RAM太高了，我就把它关了。

时间来到**23:08**。我在阅读 AstrBot 部署方式。官方提到：

- <span class="hover-hint">Docker<span class="hover-hint__tooltip"><span class="hint-title">Docker / Docker Compose / 容器</span>Docker 是一个容器化平台，把应用及其所有依赖打包成一个轻量的、隔离的运行单元——容器。与虚拟机不同，容器共享宿主机的操作系统内核，因此资源消耗更低、启动更快。Docker Compose 则用于定义和运行多容器应用。AstrBot 官方推荐 Docker 部署，作者尝试过，但因镜像下载速度后期骤降（从 10MB/s 掉到 100KB/s）而放弃，转用了源码部署。</span></span>（推荐）
- <span class="hover-hint">uv<span class="hover-hint__tooltip"><span class="hint-title">uv</span>uv 是一个用 Rust 编写的高性能 Python 包管理器与虚拟环境工具，可以替代 venv、virtualenv、pip 等传统工具，速度显著更快。AstrBot 官方部署方式之一就是“uv 一键部署”；作者在源码部署时也走的是创建虚拟环境、安装依赖的流程。</span></span> 一键部署
- 桌面Launcher
- 桌面应用
- 源码部署

既然是官方推荐的，那我要试试看。

然后我就在DeepSeek的指导下装上了Docker，然后尝试部署AstrBot v4.29.1。

按照官方文档指示，我先用git克隆AstrBot的[官方仓库](https://github.com/AstrBotDevs/AstrBot)。对，就是那个Release中没有exe的那个。我通过ssh克隆了仓库，结果报错：

```bash
git@github.com: Permission denied (publickey).
fatal: Could not read from remote repository.
```

到现在（水文的时候）才发现是**<span class="hover-hint">SSH 公钥身份验证<span class="hover-hint__tooltip"><span class="hint-title">SSH 公钥身份验证</span>SSH 是远程登录 Linux 服务器的协议。使用公钥认证时，客户端持有私钥，服务器上预先存放对应的公钥，双方通过挑战-应答机制验证身份，无需输入密码。如果本地没有生成密钥对，或者公钥没有添加到 GitHub 账户的 SSH keys 中，克隆仓库时就会报 Permission denied (publickey)。作者遇到的就是这个错误，后来改用 HTTPS 方式克隆绕过了该问题。</span></span>失败**，我没有在 GitHub 绑定我的 SSH 公钥。

> *算了用https也行*

结果我在拉取容器的时候，要下载727.3MB的内容，但是下着下着不对劲的地方来了：

刚开始差不多10MB/s，**到后面100KB/s**。

> *百度网盘呢这是？*

就是最后那两个文件，一个463.2MB、一个210.4MB，下载速度都很慢。

起初我还以为是网络的问题，结果重试了好几遍都很慢。

我啊，直接 <kbd>Ctrl</kbd>+<kbd>C</kbd> 取消下载

之后我换成了用源代码部署，固定流程：

1. 配置虚拟环境
2. 激活虚拟环境
3. 安装依赖
4. main.py
5. 设置<span class="hover-hint">Tailscale<span class="hover-hint__tooltip"><span class="hint-title">Tailscale</span>Tailscale 是一个基于 WireGuard 的零配置 VPN / 组网工具，能在不同网络中的设备之间建立加密的对等连接，形成一个私有虚拟网络（tailnet）。文中作者在源码部署时配置了“Tailscale 本地 TCP 转发”，目的是让 AstrBot 的 WebUI 或服务能够通过 Tailscale 分配的虚拟 IP 被安全访问。</span></span>本地TCP转发
6. 配置
7. 开机自启

配置和Windows**大同小异**，这里不再多赘述。就是打开WebUI随便点点，顺便去创建一个DeepSeek的APIKey。

## Part3：功能扩展

之后我就想把我的QQ机器人弄得更全能一点

# 结语

总体来看，这一晚的主线是：

1. **下载安装并配置 AstrBot**
2. **接入 QQ 机器人“蓝色大肥鱼”**
3. **学习并接入 Python MCP/RunPY**
4. **配置人格、插件、权限和模型**
5. **测试工具执行与日志排错**
6. **在<span class="hover-hint">阿里云 ECS<span class="hover-hint__tooltip"><span class="hint-title">阿里云 ECS</span>Elastic Compute Service，阿里云的弹性云服务器产品。文中作者的“云服务器部署”环节就是在阿里云 ECS 上完成的（系统为“阿里云 Linux 3”）。ECS 提供可随时调整配置的虚拟机实例，是部署 24 小时在线机器人的常见选择。</span></span> 上用源码部署 AstrBot**
7. **处理部署与网络问题**

# 附录：时间轴

这是我用[AutoScreenshot](https://github.com/artem78/AutoScreenshot)软件自动截图的Ai识图分析（gemma-4-E4B-it-Q4_K_M）

## 一、Windows 本地部署与接入 QQ

- **19:44–19:46**：打开 AstrBot 官网，查看 GitHub Release，确认要下载 Desktop 版 Windows exe 并安装。
- **19:50–19:53**：配置 Ollama 本地模型，完成 AstrBot 三步引导：配置 AI 模型、配置平台机器人、设置是否允许 Agent 使用电脑；填写 QQ 机器人“蓝色大肥鱼”的 AppID/Secret。
- **19:55**：在 QQ 向“蓝色大肥鱼”发消息并收到回复，完成本地接入实测。
- **19:59–20:04**：研究 MCP，让 AI 能执行 Python。DeepSeek 版代码报错，改用 “神秘西方 AI”生成代码和部署方案。
- **20:07–20:11**：按 README 创建虚拟环境、安装依赖并配置；在 AstrBot 添加 MCP 服务 `RunPY`，显示已连接。
- **20:14**：让机器人调用 Python 计算 `14^123`，验证 MCP 工具调用成功。
- **20:18–20:19**：去 B 站找“蓝色大肥鱼”提示词，创建人格，采用英文提示词 `CETACEA_LOLI`、`MODE_TAIL_FLUKES` 等，并追加 `At most three sentences, Colloquial` 限制。
- **20:29–20:33**：编辑人格能力：选择 RunPy 工具/AstrBot 技能，填写预设对话。
- **20:38–20:39**：找蓝色大肥鱼表情包并修改机器人头像。
- **20:41–20:47**：在 AstrBot 默认配置、权限、插件等页面乱逛和调整。
- **20:48–21:10**：与机器人乱玩/测试：问 Python 装在哪里、用 tkinter 创建“主人，看看嘛~”“点一下”窗口等；期间出现工具超时和弹窗，验证人格与工具执行效果。

## 二、云服务器部署与网络排障

- **23:08**：阅读 AstrBot 部署方式，决定按官方推荐尝试 Docker。
- **23:11–23:18**：在 DeepSeek 指导下在阿里云 Linux 3 上安装 Docker 及相关组件。
- **23:19**：SSH 克隆 GitHub 仓库报 `Permission denied (publickey)`；后改用 HTTPS。
- **23:25–23:28**：用 Docker Compose 拉取 AstrBot 镜像，727.3MB 下载后期极慢，按 `Ctrl+C` 取消。
- **23:24–23:30**：转源码部署，阅读“安装依赖并运行”、uv/虚拟环境、开机自启等资料。
- **23:31**：处理 Tailscale 本地 TCP 转发相关内容。
- **23:35**：在 AstrBot 更新 provider source，配置 DeepSeek 数据源/API（`https://api.deepseek.com/v1`）。
- **23:57–23:59**：在 AstrBot WebUI 继续配置默认配置文件与插件开关
- **00:02**：在 QQ 与机器人对话，机器人以鲸鱼娘口吻回答身份问题，验证人格效果。
- **00:04–00:06**：配置 <span class="hover-hint">systemd<span class="hover-hint__tooltip"><span class="hint-title">systemd / systemd 用户服务</span>systemd 是 Linux 上主流的系统与服务管理器，负责启动、停止、监控服务进程，并支持开机自启。systemd 用户服务（systemctl --user）是在用户级别运行的服务，不需要 root 权限，在用户登录后启动；配合 loginctl enable-linger 也可以让用户服务在开机时即启动、即使用户未登录也保持运行。作者在服务器上配置 AstrBot 开机自启时，遇到的“权限问题”就出在这一层。</span></span> 用户服务/开机自启时遇到权限问题。
- **00:11–00:16**：处理部署中的网络问题：<span class="hover-hint">DNS 解析失败<span class="hover-hint__tooltip"><span class="hint-title">DNS 解析失败</span>DNS 解析是把域名转换成 IP 地址的过程。解析失败的常见原因包括：DNS 服务器不可达或配置错误、防火墙/安全组拦截了 53 端口（DNS 查询端口）、/etc/resolv.conf 中的 nameserver 无效、域名未完成实名或备案等。文中作者在部署后期遇到的 DNS 问题，属于云服务器网络环境下的典型排障场景。</span></span>、<span class="hover-hint">Nginx<span class="hover-hint__tooltip"><span class="hint-title">Nginx / bind() to …:5000 failed</span>Nginx 是一个高性能的 Web 服务器与反向代理。bind() 是服务端程序绑定 IP 和端口以监听请求的系统调用。bind() failed 通常有两种典型原因：端口已被其他进程占用（Address already in use），或者权限不足（如非 root 用户尝试绑定 1024 以下的端口）。文中报错 bind() to 100.*.*.*:5000 failed，结合 5000 端口和 Tailscale IP 来看，更可能是该 IP 地址在当前网络接口上不存在或不可绑定（Cannot assign requested address），属于 Tailscale 虚拟 IP 与 Nginx 监听配置不匹配导致的排障问题。</span></span> `bind() to 100.*.*.*:5000 failed`、Tailscale IP 配置等。
