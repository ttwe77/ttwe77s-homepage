---
title: 从零搭建私人邮件服务器：我撞了十几堵墙的全过程
description: 记录我在阿里云 ECS 上从零搭建私人邮件服务器的全过程以及撞过的十几堵墙和核心教训，涵盖 Postfix、Dovecot、Let's Encrypt、阿里云邮件推送中继与 Tailscale。
date: 2026-10-12
category: 运维
readtime: 12
author: ttwe77
tags: 邮件服务器, Postfix, Dovecot, Tailscale, Let's Encrypt, 阿里云, 踩坑
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-10-14
---

# 从零搭建私人邮件服务器：我撞了十几堵墙的全过程

> 环境：Alibaba Cloud Linux 3  
> 方案：Postfix + Dovecot + Let's Encrypt + 阿里云邮件推送中继 + Tailscale  
> 目标：公网收信，Tailscale 内网登录，外发走中继  
> 时间：2026-10-11 ~ 2026-10-12
>
> 心情：从“这能有多难”到“行，你赢了，但我继续”。

## 一、为什么我要自建邮件服务器？

原因很简单：

1. 想拥有一个完全属于自己的邮箱

2. 折腾一下
3. 自己的域名好看
4. 没了

最近我买了一台阿里云 ECS。搭建网站后闲得没事干，就开始从零搭建。

本以为一两天能搞定，结果断断续续折腾了两天，撞了十几堵墙。

有些墙是技术墙，有些墙是我自己砌的，还有些墙是阿里云顺手帮我砌的。

这篇文章就把整个过程记录下来，希望能帮到同样想自建邮件服务器的你。

> [!tip]
>
> 如果你看完觉得“这人怎么这么菜”，没关系，我写的时候也这么觉得。

> [!warning]
>
> **本文为个人踩坑记录，生产环境请自行评估合规与安全风险。**作者不对因参考本文产生的任何损失负责。禁止将相关技术用于垃圾邮件、钓鱼、诈骗等违法用途。

---

## 二、Day 1：从 DNS 到认证，一路踩坑

### 1. 第一个坑：EPEL 冲突

按照教程，第一步是安装 EPEL 仓库：

```bash
sudo dnf install -y epel-release
```

结果报错，提示与 `epel-aliyuncs-release` 冲突。  
原来阿里云 Linux 已经预装了阿里云打包的 EPEL 版本，功能等价。我就没装**官方 epel-release**，直接用 `epel` 仓库。

> *“我都给你准备好了，你非要装官方的干嘛？”*

### 2. 第二个坑：25 端口出站被封

阿里云默认**封禁** TCP **25 端口**的**出方向**流量。这意味着你的服务器无法直接通过 25 端口向 Outlook、QQ 等外部邮箱发信。  

> *你想寄信？但邮局门口那条路被焊死了。*

解决方案：用 465 端口走阿里云邮件推送中继。这个后面会详细说。

### 3. 第三个坑：证书链不完整

用 Certbot 申请了 Let's Encrypt 证书，配置到 Dovecot 后，*BOOM！！！*

`openssl s_client` 测试报错：

```
unable to verify the first certificate
```

原因是 Dovecot 加载的证书文件里只有叶子证书，**没有中间证书**。  

我后来才想起来我用`OpenSSL`命令**将pem转为了crt**。

> `openssl x509 -in fullchain.pem -out cert.crt` 这个操作，**只会从 fullchain.pem 中提取出第一张证书（即服务器证书），中间证书在提取过程中被丢弃了**。而 Let's Encrypt 的 `fullchain.pem` 本身已经包含了完整的证书链（服务器证书 + 中间证书），是直接给服务器软件使用的标准文件。

我手动提取，结果把中间的信任链搞没了，就导致链不完整。

> 本来人家给你一整套乐高，我非要把说明书扔了，然后只拿一块积木说“应该能拼”。XDD

更坑的是，我的证书签发者是 Let's Encrypt YR1，一开始下载了旧版中间证书 `r10.pem`，拼上去还是错的。

后来下载了对应的 **YR1** 中间证书才搞定。

> [!tip]
>
> 中间证书这玩意儿，真不是随便抓一个就能用的。

### 4. 第四个坑：SASL 认证失败

证书弄好后，IMAP 登录又失败。Dovecot 日志：

```
pam_unix(dovecot:auth): user unknown
ruser=ttwe77@ttwe77.cn
```

原因是 Dovecot 把完整用户名 `ttwe77@ttwe77.cn` 交给 PAM，但系统里只有 `user` 这个用户。  

> *“ttwe77@ttwe77.cn？这谁？我认识吗？”*

需要在 `/etc/dovecot/conf.d/10-auth.conf` 里设置：

```
auth_username_format = %Ln
```

> [!caution]
>
> 默认配置里这行是注释掉的，而且默认值是 `%Lu`，不是 `%Ln`。`%Lu` 是完整用户名转小写，`%Ln` 是只取 `@` 前面的本地部分。

### 5. 第五个坑：IMAP 命令语法错误

用 `openssl s_client` 测试 IMAP 登录时，敲：

```
a1 LOGIN ttwe77@ttwe77.cn '我的密码'
```

返回 `a1 BAD Error in IMAP command`。  
问了蓝色大肥鱼才发现：IMAP 协议不认单引号。如果要打密码的话就直接写，或者用双引号。

> *“单引号？我不熟，别套近乎。”*

### 6. 第六个坑：Shell 把密码吃了

用 `swaks` 测试 SMTP 认证时，密码里包含 `$`、`!`、`*`、`&` 等特殊字符，没有加引号，结果被 shell 解析：

- `&` 把命令放到了后台
- `$!` 被展开成了 PID
- `--tls` 被当成独立命令

666，我忘记加了。

### 7. 第七个坑：本地域没配，邮件往外投

SMTP 认证成功后，我就发了一封测试邮件到 `ttwe77@ttwe77.cn`，结果卡在队列里，日志显示：

```
connect to *.ttwe77.cn[*.*.*.*]:25: Connection timed out
```

Postfix 把 `ttwe77.cn` 当成了外部域，试图通过公网 25 端口投递到 `*.ttwe77.cn`。结果咧，阿里云封了 25 出站  

> Postfix：冲刺、冲刺、冲、冲！
>
> 阿里云：我让你往公网冲了吗你就冲？

我然后就在 `main.cf` 的 `mydestination` 里加入 `ttwe77.cn`，让它走本地投递。

### 8. 第八个坑：Maildir 不存在

即使本地投递，也会失败，因为 `/home/ttwe77/Maildir` 目录不存在。  
由于 Postfix **不会自动创建** Maildir：

```bash
sudo mkdir -p /home/user/Maildir/{cur,new,tmp}
sudo chown -R user:user /home/user/Maildir
```

然后 `sudo nano ...main.cf` 看看 `home_mailbox` 有没有 `Maildir/`。

> Postfix：*“我只负责投，不负责给你盖房子。”*
> 我：*“行，我盖。”*

---

## 三、Day 2：中继、Tailscale 与 Fail2Ban 的反复折腾

### 9. 第九个坑：阿里云邮件推送中继 SASL 失败

配置了 `relayhost = [smtpdm.aliyun.com]:465`，但 Postfix 一直报 SASL 认证失败。  
直接用 `swaks` 连 `smtpdm.aliyun.com:465` 却成功，密码没问题。

然后花了点时间排查，发现：
- `sasl_passwd` 里域名拼错了：`twe77.cn` 少了一个 `t`

*不就是漏了一个字嘛！*

> 对，程序员经典惨案：少一个字母，排查半小时。

改完后还得 `postmap` 重新生成 `.db` 文件，不然 Postfix 读的还是旧的。

> Postfix：*“你改了文件，但我不一定看。”*

### 10. 第十个坑：发件人与认证用户不一致

阿里云要求 SMTP 认证用户名必须与信封发件人一致。  
但 Postfix 默认用 `user@hostname` 作为发件人，比如 `ttwe77@ttwe77.localdomain`，而认证用户是 `ttwe77@ttwe77.cn`。

寄。

> 阿里云：*“你谁？”*
> Postfix：*“我是 ttwe77@ttwe77.localdomain。”*
> 阿里云：*“不，你不是。”*

解决方案：配置 `sender_canonical_maps`，把所有本地发件人重写为 `ttwe77@ttwe77.cn`。

### 11. 第十一个坑：25 端口收不到外部邮件

外部邮件（Outlook、yeah.net）发过来，服务器杳无音信。  
排查后发现 25 端口根本没有监听。`master.cf` 里 25 端口的 smtpd 行被注释掉了。  

>  *不是我记得我没注释啊。哦，忘记取消注释了*

取消注释，重启 Postfix，25 端口开始监听，外部邮件成功投递。

### 12. 第十二个坑：Tailscale 方案把 25 端口也关进了内网

为了让 IMAP/SMTP 只允许 Tailscale 内网访问，我把 Postfix 的 `inet_interfaces` 改成了 `loopback-only`。  
结果 25 端口也只监听 127.0.0.1，公网收不到邮件了。

> 我：*“我要安全。”*
> 25 端口：*“那我呢？”*
> 我：*“你也是。”*
> 公网邮件：*“那我走？”*

然后：
- `inet_interfaces = all`
- 25 端口监听公网
- 587/465 通过 `master.cf` 绑定 `127.0.0.1`，交给 Tailscale Serve 转发

*不能一刀切，切完容易把自己也切了。*

### 13. 第十三个坑：OpenDKIM milter 导致 smtpd 崩溃

配置了 OpenDKIM 的 milter，但 OpenDKIM 没运行，Postfix 报：

```
fatal: host/service localhost/8891 not found
```

而且 chroot 环境下无法解析 `localhost`。  

> chroot：`local`啥啊？
>
> 我：`localhost`啊。
>
> chroot：什么`host`啊？
>
> 我：行了你一边凉快去吧。

把 `inet:localhost:8891` 改成 `inet:127.0.0.1:8891`。

### 14. 第十四个坑：Fail2Ban 的反复折腾

为了给服务器叠层甲，尝试配置 Fail2Ban。结果踩了一堆坑：
- `__prefix_line` 未定义，炸
- `datepattern` 与 backend 不匹配，炸
- `jail.d` 下的旧文件覆盖了 `jail.local`，炸
- 正则不匹配实际日志格式，炸
- 正则加了 `^` 导致失配，炸
- 127.0.0.1 被 `ignoreip` 和 `ignoreself` 忽略，没炸
- `polling` 后端不读新行，切到 `pyinotify`，继续炸

> 我本来是装 Fail2Ban 来防别人的，结果它先把我防住了。

最后意识到：在 Tailscale 架构下，IMAP/SMTP 端口根本不暴露公网，Fail2Ban 对它们意义不大。真正需要保护的是公网 25 和 SSH。  
于是干脆卸载了 Fail2Ban，用 Tailscale 作为安全边界。

> Tailscale：边界我来。
>
> Fail2Ban：那我走？
>
> 我：走吧，不送。

### 15. 第十五个坑：Thunderbird 自动配置失败

Thunderbird 自动检测服务器配置，但服务器在 Tailscale 内网，公网探测不到，一直失败。  

> Thunderbird：*“我找不到你的服务器。”*
> 我：*“它在 Tailscale 里。”*
> Thunderbird：*“那是什么次元？”*

没辙，只能手动配置，填入 Tailscale IP 和端口。

刚以为这样就好了，结果Thunderbird告诉我SSL证书不匹配：用 IP `100.x.x.x` 连接，但证书签给域名。  
于是决定：新建一个内部DNS解析，你们都得给我用同一个证书。

---

## 四、最终状态

| 功能                 | 状态                       |
| -------------------- | -------------------------- |
| 公网收信 25          | ✅                          |
| IMAP 993 / Tailscale | ✅                          |
| SMTP 587 / Tailscale | ✅                          |
| 本地投递 Maildir     | ✅                          |
| 外发中继阿里云 465   | ✅                          |
| SPF / DKIM / DMARC   | ✅ 全 pass                  |
| 公网拒绝 993/587/465 | ✅                          |
| Thunderbird 手动配置 | ✅                          |
| Fail2Ban             | 已卸载，Tailscale 作为边界 |

最终这套架构比普通自建邮件服务器更安全：**公网只开 25 收信，所有客户端登录都藏在 Tailscale 内网里。**

> 外面看：一台只收信的服务器。
> 自己用：全套邮箱服务。

这种感觉，还挺爽。

---

## 五、核心教训总结

1. **阿里云 Linux 自带 `epel-aliyuncs-release`**，不要强装官方 `epel-release`。
2. **阿里云默认封 25 出站**，外发必须走 465/587 中继。
3. **证书链必须用 `fullchain.pem`**，不要手动提取单证书。
4. **Dovecot 用户名映射**：`auth_username_format = %Ln` 才能把 `user@domain` 映射到系统用户。
5. **IMAP 不用单引号**，密码直接写或用双引号。
6. **Shell 特殊字符密码**：命令行里一律单引号包住。
7. **本地域要进 `mydestination`**，否则 Postfix 会尝试公网投递。
8. **Maildir 要手动建**：`cur/new/tmp` 三个子目录缺一不可。
9. **25 端口容易被注释/改监听地址**：`master.cf` 和 `inet_interfaces` 是重点检查项。
10. **`sasl_passwd` 改完必须 `postmap`**，否则 `.db` 陈旧。
11. **发件人必须与阿里云认证用户一致**，用 `sender_canonical_maps` 修正。
12. **Tailscale Serve 用 TCP 透传**，IMAP/SMTP 不能用 HTTPS 模式。
13. **不要用 IP 连接邮件服务；Let's Encrypt 不签发 IP 证书，应使用域名或 Tailscale MagicDNS。**
14. **Tailscale 架构下 Fail2Ban 对 IMAP/SMTP 意义有限**，安全边界交给 Tailscale。
15. **全局改 `inet_interfaces = loopback-only` 会坑到 25 收信**，要分离监听。

---

## 六、结语

自建邮件服务器确实不容易，尤其是国内云环境还有各种限制。  

你会遇到 DNS、证书、认证、中继、防火墙、chroot、Fail2Ban、客户端配置**轮番上阵**。
有时候**不是技术难，是坑太密**。

但折腾完之后，看到 Outlook 发来的邮件成功投递到自己的服务器，Thunderbird 弹出通知的那一刻，还是很有成就感的。

> *这破服务器，居然真跑起来了？！*

如果你也在自建邮件服务器，希望这篇文章能帮你少撞几堵墙。  
记住：**公网只开 25 收信，登录端口全走 Tailscale，外发走中继，证书用 fullchain，密码用单引号。**  
剩下的，就是耐心排查了。

祝折腾愉快！🚀



> [!warning] 
> 本文仅为个人在特定时间、特定云环境下的自建邮件服务器踩坑记录，**不是完整教程，也不构成生产环境部署建议、安全建议或法律意见**。文中配置、命令、第三方服务策略均可能随版本、地区和时间变化，请以官方文档和实际环境为准。
>
> 自建邮件服务器涉及 DNS、证书、端口暴露、反垃圾、数据备份、隐私与合规等风险。请在操作前做好快照与备份，并在测试环境验证。因参考本文导致的邮件丢失、数据泄露、服务中断、账号封禁、费用损失、法律合规问题等，作者不承担任何责任。
>
> 请勿将相关技术用于发送垃圾邮件、钓鱼邮件、诈骗信息、骚扰他人或任何违法违规用途。在中国大陆等地区部署邮件服务，请自行确认备案、邮件服务许可、反垃圾要求及云厂商条款。
>
> 文中域名、IP、用户名等仅用于说明；公开发布前建议自行脱敏。阿里云、Let's Encrypt、Tailscale、Postfix、Dovecot 等名称归各自权利人所有，本文与其无隶属或背书关系。