---
title: 从立项到上线：我的个人网站搭建记录
description: 记录从虚拟主机、内网穿透到 Nginx、阿里云 ECS、域名备案与网站上线的建站经历。
date: 2026-10-07
category: 建站
readtime: 6
author: ttwe77
tags: 个人网站, 阿里云, 记录
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-10-13
---

> [!note]
>
> 写于 10月7日晚自习 19:32；10 月 13 日更新备案与上线部分。
> *太久没写字已经不会写字了*

# 立项之前

在立项之前呢，我曾经试过搭建网站。
## 第一次建站经历
记得那还是在 GPT 还没普及的时候，我一时兴起就想试着建个站玩玩。按照网上的教程，我注册了一个<span class="hover-hint">虚拟主机<span class="hover-hint__tooltip"><span class="hint-title">虚拟主机</span>一种共享服务器资源的建站方式，多个网站共用同一台服务器的环境。</span></span>的提供商（我记得是 `HostFree`），然后去某某二级域名分发网站上拿了一个域名，又去某模板网站上下了一个看起来还行的模板。当时还是古法编程，我用手机软件 <span class="hover-hint">AIDE Web<span class="hover-hint__tooltip"><span class="hint-title">AIDE Web</span>Android 上的网页 IDE/编辑器，可在手机上编写 HTML、CSS、JS。</span></span> (一些基础知识我是在这学的） 照着模板改，最终上传到虚拟主机上完成建站了（就是速度慢了点）。

## 第二次建站经历

感觉这不算第二次。第二次我是用内网穿透做的。这次就是本地<span class="hover-hint">**KSWEB**<span class="hover-hint__tooltip"><span class="hint-title">KSWEB</span>Android 上的 Web 服务器套件，可运行 Apache/Nginx/PHP/MySQL 等。</span></span> + <span class="hover-hint">**ngrok**<span class="hover-hint__tooltip"><span class="hint-title">ngrok</span>内网穿透工具，可将本地端口暴露到公网。</span></span>部署的，缺点就是这样做手机耗电量极大，而且后台进程容易被Kill。之后因为虚拟主机国内连接困难，内网穿透要实名（花生壳、Sakura FRP），就没怎么折腾网站了。

## 之后

之后配了电脑，有条件了。我第一个和现在用的就是 <span class="hover-hint">**Nginx**<span class="hover-hint__tooltip"><span class="hint-title">Nginx</span>高性能 Web 服务器和反向代理，常用于静态托管与负载均衡。</span></span>，因为它简洁、轻量。

得益于之前的经验，我萌生了搭建网站的想法。嗯不对，我建站之初纯纯是为了好奇。<br>我当初是好奇<span class="hover-hint">蔚蓝档案<span class="hover-hint__tooltip"><span class="hint-title">蔚蓝档案</span>Blue Archive，一款二次元手游，以清新 UI 和学园都市风格著称。</span></span>的 UI 设计风格是啥，就问了下<span class="hover-hint">蓝色大肥鱼<span class="hover-hint__tooltip"><span class="hint-title">蓝色大肥鱼</span>“蓝色大肥鱼”是 DeepSeek 在中文互联网上最出圈的拟人化爱称，指代一只贪吃、爱摸鱼、有“活人感”的蓝色鲸鱼少女形象。</span></span>。感觉它说的不是很详细，之后我用另一个 AI 生成了风格介绍，又用 <span class="hover-hint">DeepSeek<span class="hover-hint__tooltip"><span class="hint-title">DeepSeek</span>深度求索推出的人工智能大模型与助手。</span></span>整合，总结了一篇 <span class="hover-hint">Markdown<span class="hover-hint__tooltip"><span class="hint-title">Markdown</span>轻量级标记语言，用纯文本编写结构化文档。</span></span> 文档……要不生成一篇 UI 设计规范？就是这么巧，在一步一步地我就让 DeepSeek 生成了我的个人主页。

# 项目成立

哎呀都做出来了怎能不做版本控制，用版本控制怎能不连接远程仓库。OK 干它！于是从军训后几天到昨天没一天是闲着的（昨天是 2026-10-06），*我的国庆假期啊*……

## 网页开发
### 个人主页
这个没什么好讲的。我只要复制粘贴就好了，而蓝色大肥鱼要考虑的可就多了。主页界面我参考了下游戏 UI 和一些模仿项目，做了一套还看得过去的 UI。当时思考如何布局时就和我现在写水文一样深思熟虑。但最终还是做出来了，不是吗？因为服务器成本原因，PNG 素材被压成 <span class="hover-hint">WebP<span class="hover-hint__tooltip"><span class="hint-title">WebP</span>Google 推出的图片格式，通常比 PNG/JPG 更小。</span></span>，又被压成 <span class="hover-hint">AVIF<span class="hover-hint__tooltip"><span class="hint-title">AVIF</span>基于 AV1 的图片格式，压缩率高。</span></span>，图标干脆重画成 <span class="hover-hint">SVG<span class="hover-hint__tooltip"><span class="hint-title">SVG</span>可缩放矢量图形，适合图标，放大不失真。</span></span>。<span class="hover-hint">ICO<span class="hover-hint__tooltip"><span class="hint-title">ICO</span>图标文件格式，网站 favicon 常用。</span></span> 的网页图标直接换为 SVG 了。

### 七七的折腾笔记
再想想，我还是往里面写点内容吧，我看你们都这样。*才……才不是备案不让这么起名呢*。我依旧仿游戏风格让 AI 生成网页，因为没后端，我就静态配置了每个页面。DeepSeek 说如果需要切换页面（不新建标签页）而不停止音乐播放，需要重构网页。呃，就这样挺好的。

### 笔记页面
我啊，依旧延续用静态页面的传统。写好 Markdown 就让 Python 处理成 html，可方便了（但后期维护不方便）。因为是静态页面，点赞、评论是没有的。就连账号都注册不了（SSH 除外）。

# 服务器购置
我之前用过阿里云的 <span class="hover-hint">**云解析 DNS**<span class="hover-hint__tooltip"><span class="hint-title">云解析 DNS</span>阿里云提供的 DNS 域名解析服务。</span></span> 中的 <span class="hover-hint">**移动解析HTTPDNS**<span class="hover-hint__tooltip"><span class="hint-title">移动解析HTTPDNS</span>通过 HTTP/HTTPS 协议进行 DNS 解析，绕过本地 DNS。</span></span>（<span class="hover-hint">DoH<span class="hover-hint__tooltip"><span class="hint-title">DoH</span>DNS over HTTPS，用 HTTPS 加密 DNS 查询。</span></span>），所以建站时我用的阿里云。在我稍微了解方法后，我开始考虑是用**虚拟主机**还是**<span class="hover-hint">云服务器 ECS<span class="hover-hint__tooltip"><span class="hint-title">ECS</span>阿里云弹性计算服务，可弹性配置的云主机。</span></span>**。结果我发现在**虚拟主机**、**<span class="hover-hint">轻量应用服务器<span class="hover-hint__tooltip"><span class="hint-title">轻量应用服务器</span>面向轻量场景的云服务器，套餐固定、易用。</span></span>**和 **ECS** 中，就 **ECS** 最便宜。在选购期间，阿里云客服居然还给我来电了，只因为我跟在线人工客服咨询过（就发了一句话），它向我推荐了一年 **99 元**的 ECS。很快啊，我就放弃了之前考虑的 ECS 配置，拥抱了便宜套餐。

# 域名备案
买了服务器，怎能少了域名呢？在朋友的推荐下，我从更便宜的 `.top` 和便宜的 `.cn` 域名中选择了 `.cn` 域名，并以我的网名注册为域名前缀。注册域名时的速度很快啊，不到一天就注册下来了。之后就是 <span class="hover-hint">**ICP 备案**<span class="hover-hint__tooltip"><span class="hint-title">ICP 备案</span>中国大陆网站必须完成的工信部备案。</span></span>了。听阿里云客服说我们这边备案可能要 20 天左右。我的天啊，为什么这么慢。但令我惊讶的是，**10 月 3 日提交的到 10 月 10 日就通过了**。

# 网站上线

收到邮件那晚，我直接说如果网站没上线我就不睡了。可结果实际上我睡觉的时间是 1:40（*还有早八呢，可爽了呢~*）。

上线用了 10%、配置服务器用了 90% 的时间。我差点被阿里云的 **<span class="hover-hint">边缘安全加速 ESA<span class="hover-hint__tooltip"><span class="hint-title">ESA</span>阿里云边缘安全加速服务，提供 CDN、WAF、SSL 等能力。</span></span>** 整破防了（*强者抱怨环境；但我是弱者，我不仅抱怨环境，我还抱怨强者。*）。设置了一堆东西，甚至这个功能还免费帮我从 **<span class="hover-hint">Let's Encrypt<span class="hover-hint__tooltip"><span class="hint-title">Let's Encrypt</span>免费、自动化的开放 CA，签发 SSL/TLS 证书。</span></span>** 那申请了**<span class="hover-hint">SSL证书<span class="hover-hint__tooltip"><span class="hint-title">SSL 证书</span>用于 HTTPS 加密的数字证书。</span></span>**用于ESA。就是有个缺点：SSL证书无法导出啊，我还得自己再申请。

ESA 这东西，说好听点叫边缘安全加速，说难听点叫“我明明只想上线，你却让我重新学一遍网络”。
域名接入、<span class="hover-hint">CNAME<span class="hover-hint__tooltip"><span class="hint-title">CNAME</span>DNS 记录类型，把一个域名指向另一个域名。</span></span>、回源、缓存、SSL/TLS、强制 HTTPS、<span class="hover-hint">HSTS<span class="hover-hint__tooltip"><span class="hint-title">HSTS</span>HTTP 严格传输安全，强制浏览器只用 HTTPS 访问。</span></span>……每一项看起来都能默认，每一项默认完都可能有惊喜。

还好有点经验，至少看控制台不像飞机的仪表盘。

------

之后实际去访问，又出岔子了。访问[https://www.ttwe77.cn](https://www.ttwe77.cn)可以，但是访问[https://ttwe77.cn](https://ttwe77.cn)却不行。之后又是几小时的排查（中途爬去上课了），结果我发现好像就只有我电脑不能访问。*哎罢了不管*了。

> 结果后面一看是我的`DoH`设置的<span class="hover-hint">权威解析<span class="hover-hint__tooltip"><span class="hint-title">权威解析</span>由域名权威 DNS 服务器给出的最终解析记录。</span></span>的问题



至此，网站从文件夹里的 HTML，变成了互联网上的一个地址。
虽然它还很简陋，但至少，它活了。



**xdm，快来恭喜我！**啊对哦，静态网页发不了评论。