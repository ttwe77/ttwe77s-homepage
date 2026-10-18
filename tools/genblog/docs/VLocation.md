---
title: "虚拟定位折腾记：从 iOSRealRun 到 MuMu 模拟器的踩坑记录"
description: "记录我尝试 IOS 虚拟定位到 MuMu 安卓模拟器虚拟定位的全过程，涵盖 iOSRealRun-cli、KernelSU、LSPosed、LocationSpoofer、HMA-OSS 等工具和踩坑经验。"
date: 2026-10-13
category: 折腾
readtime: 8
author: ttwe77
tags: 虚拟定位, MuMu模拟器, KernelSU, LSPosed, LocationSpoofer, HMA-OSS, 踩坑
license: CC BY-NC 4.0
license_url: "https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans"
updated: 2026-10-16
---

# 虚拟定位折腾记

## 开端

最初的开始在今天（2026/10/13），我听人提到一个需要留下轨迹的小任务，按周期统计里程。我第一反应不是去走，而是好奇：如果位置能变，是不是就能“坐地日行八万里”？

> [!warning]
>
> 本文仅为个人经验记录，操作过程中产生的任何损失由操作者自行负责。

## 摸索

于是带着好奇，我打算先去打听它大概用什么类型的应用：

> 应用商店搜XXXX
>
> *欸没搜到？【截图】*
>
> 第一个

我然后就上网搜“位置模拟”的通用思路。答案五花八门：手机端虚拟定位、电脑模拟器、系统模块、传感器伪造……emmm越看越觉得，这不是改一个坐标那么简单。

## 实践

### 虚拟定位

我打算先从虚拟定位下手，我去 <span class="hover-hint">GitHub<span class="hover-hint__tooltip"><span class="hint-title">代码托管平台</span>全球最大的代码托管与协作平台，文章中的项目、Issues、Releases 都来自这里。</span></span> 上找了点虚拟定位的项目 **[iOSRealRun-cli-17](https://github.com/iOSRealRun/iOSRealRun-cli-17)** 。略微折腾了一下：

1. Clone项目
2. 安装 <span class="hover-hint">iTunes<span class="hint-title"></span><span class="hover-hint__tooltip"><span class="hint-title">苹果设备管理软件</span>苹果官方媒体与设备管理软件，提供 iPhone 连接所需的驱动/服务，常被 iOS 虚拟定位工具依赖。</span></span>
3. 安装脚本依赖
4. 在地图中标记路径点并导出为 <span class="hover-hint">JSON<span class="hover-hint__tooltip"><span class="hint-title">数据交换格式</span>JavaScript Object Notation，一种轻量数据格式；文中用于保存地图上标记的路径点并导入虚拟定位工具。</span></span>
5. 插上线，信任电脑
6. 报错

程序说我**没有连接设备**，但是我已经插上了数据线，<span class="hover-hint">爱思助手<span class="hover-hint__tooltip"><span class="hint-title">iOS 设备管理工具</span>第三方 iOS 设备管理软件，可识别设备、刷机、备份、安装应用等。</span></span>也成功识别到了我的手机。就连 <span class="hover-hint">蓝色大肥鱼<span class="hover-hint__tooltip"><span class="hint-title">DeepSeek（蓝色大肥鱼）</span>“蓝色大肥鱼”是人工智能公司 DeepSeek 的二次元拟人形象，也是中文互联网社区给它起的爱称。</span></span> 都无能为力。emmm，于是我去看了下项目的 **<span class="hover-hint">Issues<span class="hover-hint__tooltip"><span class="hint-title">GitHub 问题反馈区</span>GitHub 仓库的问题反馈区，用于报告 Bug、提问和讨论项目问题。</span></span>** ，有人 **Fork** 了这个项目，做了一个**兼容 <span class="hover-hint">iOS 18<span class="hover-hint__tooltip"><span class="hint-title">苹果移动操作系统</span>苹果 iPhone 的操作系统版本，文中因原工具不兼容而改用社区 Fork 版本。</span></span> 的脚本 [iOSRealRun-cli-18](https://github.com/BiancoChiu/iOSRealRun-cli-18)** 。

> *哎呀骇似我力，怎么还不兼容这个版本*

我依旧：

1. Clone项目
2. 安装依赖
3. python main.py
4. 插上手机，信任电脑
5. 打开地图看到位置变了
6. 打开软件测试

结果发现：地图动了，但是结果没动。

> *GPS 变了不意味着你动了*

我推测是软件访问了“<span class="hover-hint">运动与健身<span class="hover-hint__tooltip"><span class="hint-title">iOS 健康数据权限</span>iOS“健康”中的运动与健身数据权限，应用可能读取步数、运动记录；文中推测测试应用依赖该权限。</span></span>”，但是**不给访问权限就不让用**。

### 安卓模拟器

根据教程所述（现在教程视频已失效力），我需要装一个**<span class="hover-hint">MuMu模拟器<span class="hover-hint__tooltip"><span class="hint-title">安卓模拟器</span>网易推出的安卓模拟器，可在电脑上运行 Android 应用，并自带虚拟定位功能。</span></span>**来**模拟安卓系统**。起初我还是对 MuMu模拟器 比较抗拒的（毕竟是国产的嘛），但是真正用起来感觉还好（教程视频里展示的居然是**假官网**！！装软件的时候记得看着点哦。）。跟着视频上展示的软件一个一个装（评论区里的企鹅群没了）。

1. 开启 <span class="hover-hint">Root<span class="hover-hint__tooltip"><span class="hint-title">Android 超级用户权限</span>Android 系统中的最高权限，允许修改系统、安装模块和绕过部分限制。</span></span> 附赠的<span class="hover-hint">[KernelSU](https://kernelsu.org/zh_CN/)<span class="hover-hint__tooltip"><span class="hint-title">Android Root 方案</span>基于内核的 Android Root 与权限管理方案，用于获取超级用户权限并管理模块。</span></span>
2. 模拟位置的[Fake Location](https://github.com/Lerist/FakeLocation)（实际使用的时候感觉并不是很好用）
3. 超级虚拟定位软件**[LocationSpoofer](https://github.com/HuangZhuoRui/LocationSpoofer)** [v2.6.13](https://github.com/HuangZhuoRui/LocationSpoofer/releases/tag/v2.6.13)
4. **<span class="hover-hint">LSPosed<span class="hover-hint__tooltip"><span class="hint-title">Android Hook 框架</span>基于 Xposed 的 Android 运行时 Hook 框架，可通过模块修改应用行为；文中使用 v2.2.0。</span></span>** 模块 v2.2.0
5. <span class="hover-hint">**[ZygiskNext](https://github.com/LSPosed/ZygiskNext)**<span class="hover-hint__tooltip"><span class="hint-title">Zygisk API 模块</span>为 KernelSU 等非 Magisk 环境提供 Zygisk API 的模块，使 LSPosed 等 Zygisk 模块可以运行。</span></span> 模块
6. 隐藏应用列表的<span class="hover-hint">**[HMA-OSS](https://github.com/frknkrc44/HMA-OSS)**<span class="hover-hint__tooltip"><span class="hint-title">隐藏应用列表</span>Hide My Applist 的开源版本，用于隐藏应用列表、Root 管理器、LSPosed 模块等，规避应用检测。</span></span>
7. 用于测试效果的**<span class="hover-hint">高德地图<span class="hover-hint__tooltip"><span class="hint-title">地图导航应用</span>国内常用的地图导航应用，文中用于测试虚拟定位是否生效。</span></span>**
8. 测试软件
9. 还有我最后加的去广告软件**AdGuard**

> *无视风险，继续安装！*

在我安装软件的时候居然意外地轻松？除了在我安装 `LSPosed` 的时候装成了旧版以外就没什么问题了。

事后发现LSPosed的官方开发团队在2024年1月8日正式宣布**停止维护**，怪不得官方仓库里的只有旧版。

#### 净化环境

我看教程中用了 `HMA-OSS` 软件，我点进去看了看。随便点了点隐藏了Root管理器（`KernelSU`）和 `LSPosed` 模块、<span class="hover-hint">开发者选项<span class="hover-hint__tooltip"><span class="hint-title">Android 调试菜单</span>Android 隐藏的设置菜单，用于 USB 调试、模拟位置等开发调试功能。</span></span>和不可见的应用。也不知道这样做有没有用。

> 这里是后期，有用。它拦截了软件3k+次。

#### 模拟定位

之后就是自己摸索，我最初先尝试了 `Fake Location` ，结果说Root模式需要开通专业版。

> *毕竟......作者还是要吃饭的嘛*

哎算了，大不了就换软件。于是我在<span class="hover-hint">[BiliBili](https://www.bilibili.com)<span class="hover-hint__tooltip"><span class="hint-title">视频分享平台</span>哔哩哔哩，国内视频分享平台。</span></span> Deep diving（DeepSeek Harness思考标志）了下，发现了一个更好用的软件：`LocationSpoofer`。

起初我是看其它（其他）UP主都在用，于是我就想下下来试试（因为有成功案例嘛）。然后我就去官方仓库的 **<span class="hover-hint">Releases<span class="hover-hint__tooltip"><span class="hint-title">GitHub 发布页面</span>GitHub 仓库的发布页面，提供各个版本的安装包和更新说明。</span></span>** 上下了最新版的安装包。

> *欸咋还分全局和非全局呢？复制 Releases 信息喂给 DeepSeek 看看~*
>
> *好，那我就选全局了。*

结果一装下来还要注册登录。弄完后进入软件发现地图加载不出来。提示需要付费。作者原话是：[链接](https://github.com/HuangZhuoRui/LocationSpoofer/issues/83)

我又去翻了几个 `Issues` ，发现**只有旧版才能免费用地图**。

好吧，软件卸了又装。最终下到了能用的版本 v2.6.13

这个软件还挺方便的，支持在地图中选择位置。然后我简单地添加了下地图标点，开始模拟。按下后弹窗提示我了一些复杂的功能，这些功能还挺强的：

- 巡航（跑步）速度
- 步频与记步模拟
- 伪造 <span class="hover-hint">Wi-Fi<span class="hover-hint__tooltip"><span class="hint-title">无线局域网</span>Wireless Fidelity，无线局域网技术；文中虚拟定位工具可伪造 Wi-Fi 数据辅助定位。</span></span> 数据
- 模拟<span class="hover-hint">基站<span class="hover-hint__tooltip"><span class="hint-title">移动通信基站</span>移动网络中的通信基站，可通过模拟基站数据辅助定位。</span></span>数据
- 模拟<span class="hover-hint">蓝牙<span class="hover-hint__tooltip"><span class="hint-title">短距离无线通信</span>Bluetooth，短距离无线通信技术；文中虚拟定位工具可模拟蓝牙数据。</span></span>数据
- GPS轻微漂移

> *？！强强！？*

我打开软件测试了一下，虽然有一部分（一点点）不完美。但是这起码有用。

> *OK啊，软件也是被我拿捏了XD。*

#### 自带的虚拟定位

其实还有后续。我继续在网上 Deep Diving 后发现有一个更简单的方法：MuMu模拟器**自带虚拟定位**，点击一个位置再确认就能瞬移到特定位置。就是如果瞬移太快容易“不完美”。

> 这个方法还挺吃操作的？

