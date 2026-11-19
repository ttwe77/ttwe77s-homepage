---
title: "云上搭 L2TP/IPsec 实录"
description: "在云服务器上用 SoftEther 搭 L2TP/IPsec 的全过程：strongSwan 翻车、源码编译、vpncmd 配置、Windows 事件、PPP 认证失败，以及连上就断网。"
date: 2026-11-19 21:50:44
category: 运维
readtime: 6
author: ttwe77
tags: SoftEther, L2TP, 阿里云, Windows
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-11-19 21:50:44
---

# 云上搭 L2TP/IPsec 实录

> [!warning]
>
> 提示：SoftEther 仅用于**自己拥有、有权管理的服务器 / 内网组网**。

## 开头

事情的起因很简单：***无聊，无聊，还是\*\*的无聊***。想着闲着也是闲着，我的<span class="hover-hint">Tailscale<span class="hover-hint__tooltip"><span class="hint-title">Tailscale</span>一款基于 WireGuard 协议的虚拟组网工具，不需要公网 IP，靠 P2P 打洞或 DERP 中继把设备连成一个加密的“Tailnet”。作者原本就用 Tailscale 跑业务，但觉得 <span class="hover-hint">ACL<span class="hover-hint__tooltip"><span class="hint-title">ACL（Access Control List，访问控制列表）</span>Tailscale 里的 ACL 用来精细控制哪些设备/用户能访问哪些资源。作者说“ACL 懒得维护”，指的是 Tailscale 的这套权限规则需要持续花精力管理。</span></span> 维护麻烦，又想找另一种方式组网，所以决定在阿里云 ECS 上再搭一套 L2TP/IPsec。</span></span>主要是用来跑业务，ACL懒得维护。但我又想**和别人组网打游戏**，那咋办呢？那就用下Tailscale的**同款虚拟局域网的技术**，在自己的阿里云 ECS 上搞个 <span class="hover-hint">L2TP/IPsec<span class="hover-hint__tooltip"><span class="hint-title">L2TP/IPsec</span>L2TP/IPsec 是一种将两种协议组合使用的 VPN（虚拟专用网）技术。你可以把它理解成：L2TP 负责“挖隧道”，IPsec 负责“给隧道上锁”。单独使用 L2TP 时，数据本身并不加密，必须依赖 IPsec 来提供加密和身份验证，从而保证传输安全。</span></span> 协议的虚拟专用网，方便一起联机游戏（*国内的服务器速度肯定很快！[确信]*）。

服务器长这样：

```text
NAME="Alibaba Cloud Linux"
VERSION="3 (OpenAnolis Edition)"
PLATFORM_ID="platform:al8"
PRETTY_NAME="Alibaba Cloud Linux 3****** (OpenAnolis Edition)"
```

跟 RHEL 8 / CentOS 8 基本一个生态。AI的第一反应是让我装 <span class="hover-hint">strongSwan<span class="hover-hint__tooltip"><span class="hint-title">strongSwan</span>Linux 上老牌的 IPsec VPN 实现，基于 IKE 协议做密钥协商和隧道建立。文章第一回合就是在它上面翻的车。</span></span>，Linux 上搞 IPsec 的老牌选手嘛。

## 第一回合：strongSwan 的半小时惨案

装起来确实很顺利：

```bash
sudo dnf install strongswan strongswan-sqlite
```

```text
Linux strongSwan U6.0.6/K5.10.134-19.8.al8.x86_64
```

顺手把转发写了：

```bash
sudo tee /etc/sysctl.d/99-strongswan.conf <<'EOF'
net.ipv4.ip_forward = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.default.send_redirects = 0
EOF

sudo sysctl -p /etc/sysctl.d/99-strongswan.conf
```

然后就开始不对劲了。第一个坑是配置目录：`/etc/strongswan/swanctl/conf.d/` 和 `/etc/swanctl/conf.d/` 到底用哪个？

```text
[ttwe77@ttwe77-server ~]$ cat /etc/strongswan/swanctl/conf.d/site-to-site.conf
cat: No such file or directory
[ttwe77@ttwe77-server conf.d]$ sudo nano /etc/strongswan/swanctl/conf.d/roadwarrior.conf
[ttwe77@ttwe77-server conf.d]$ sudo nano /etc/swanctl/conf.d/roadwarrior.conf
```

两个路径来回试，配置写完加载：

```bash
sudo swanctl --load-all
```

```text
connecting to 'unix:///run/strongswan/charon.vici' failed: No such file or directory
error: connecting to 'default' URI failed: No such file or directory
```

vici 接口连不上，说明 daemon 根本没按我预期起来。重启服务再来：

```bash
sudo systemctl restart strongswan
sudo systemctl status strongswan --no-pager -l
```

状态是 `active (running)`，`ExecStartPost=/usr/sbin/swanctl --load-all --noprompt` 也是 `SUCCESS`。看着一切正常嘛。

客户端也确实连上来了：

```text
parsed IKE_AUTH request 1 [ IDi N(INIT_CONTACT) IDr AUTH CPRQ(ADDR DNS) SA TSi TSr ... ]
looking for peer configs matching 1**.***.***.***[4*.***.***.***]...4*.***.***.***[client.example.com]
no matching peer config found
generating IKE_AUTH response 1 [ N(AUTH_FAILED) ]
```

关键就是这一行：

```text
no matching peer config found
```

服务端收到请求了，但没有一个 peer 配置能匹配上这个身份。配置写进去了，但没被正确识别——典型的多路径配置错位加上身份字段不匹配。

试了几轮之后我算是看明白了，继续跟 <span class="hover-hint">swanctl<span class="hover-hint__tooltip"><span class="hint-title">swanctl</span>strongSwan 现代的命令行管理工具，用来加载配置、查看状态、发起连接。它和新的 swanctl.conf 配置体系配套使用。</span></span> 的加载规则和身份匹配纠缠下去不划算：

```bash
sudo dnf remove strongswan strongswan-sqlite
```

然后放弃，拥抱 <span class="hover-hint">SoftEther VPN<span class="hover-hint__tooltip"><span class="hint-title">SoftEther VPN</span>日本筑波大学的研究项目，一个开源、跨平台、多协议的 VPN 服务器，单一线程即可同时提供 L2TP/IPsec、OpenVPN、SSTP、L2TPv3 等多种 VPN 协议。名字来自 “Software Ethernet”，因为它用软件虚拟出以太网设备来建隧道。作者从 strongSwan 转投 SoftEther，核心原因就是 SoftEther 内置 L2TP/IPsec，不需要自己拼装 IKE peer / conn / secret 那一套。</span></span>。XDDDD

 这个软件我之前在我的Windows系统上搭建过，但是没有公网IP不好搞穿透

> *不是，你都组网了还要再套一层虚拟专用网？你跑在哪层啊？*
>
> AI：L2TP在数据链路层
>
> *Tailscale管网络层的，在它前面再套一个L2TP就有点魔幻了*
>
> 内心OS：*你就直说这样行不行吧？*
>
> *那也不是不行，就是有点繁琐，Wireguard我觉得已经够安全了*
>
> *你就直说这样行不行吧？*

现在回头看，这个决定是对的。SoftEther 内置 L2TP/IPsec，不用理解那一套 <span class="hover-hint">peer / conn / secret<span class="hover-hint__tooltip"><span class="hint-title">peer / conn / secret</span>strongSwan 的配置概念：<br>conn（connection）：一条 IPsec 连接的完整定义，包含本端、对端、认证方式、加密算法等。<br>peer：对端的身份标识。IKE 协商时需要根据对端的身份去匹配一个 conn，匹配不上就会报 no matching peer config found，也就是文章卡住的地方。<br>secret：预共享密钥（PSK）或证书私钥等凭据。</span></span> 的体系，也不用nano配置文件。它的麻烦只在于"功能默认全关，要自己一个个打开"。

## 第二回合：编译 SoftEther

### 装依赖

```bash
sudo dnf install -y gcc make wget tar \
  openssl-devel readline-devel ncurses-devel zlib-devel
```

### 下源码

```bash
wget https://github.com/SoftEtherVPN/SoftEtherVPN_Stable/releases/download/v4.44-9807-rtm-2025.04.16/softether-vpnserver-v4.44-9807-rtm-2025.04.16-linux-x64-64bit.tar.gz
```

诶GitHub依旧连不上，我手动去镜像站下了再上传

```bash
tar xzf softether-vpnserver-*.tar.gz
cd vpnserve
```

### 编译

```bash
make
```

> *Just make it.*

先弹一大段许可协议，输入 `1` 表示同意，后面直接回车。编译完它自己会跑一遍环境自检：

```text
Checking 'Kernel System'...              Pass
Checking 'Memory Operation System'...    Pass
Checking 'ANSI / Unicode string processing system'... Pass
Checking 'File system'...                Pass
Checking 'Thread processing system'...   Pass
Checking 'Network system'...             Pass

All checks passed.
The preparation of SoftEther VPN Server is completed !
```

看到六个 Pass 的时候还挺爽的。`vpnserver` 和 `vpncmd` 都出来了，同时也提示我管理员密码还没设。

```bash
sudo ./vpnserver start
```

```text
The SoftEther VPN Server service has been started.
Let's get started by accessing to the following URL from your PC:
https://127.0.0.1:5555/
```

这是Web UI？那我要访问一下看看，但是你为什么只监听了127.0.0.1。

### 监听

`vpncmd` 改不了监听 IP，只能改配置文件。先停服：

```bash
sudo .../SoftEtherVPN/vpnserver/vpnserver stop
sudo nano .../SoftEtherVPN/vpnserver/vpn_server.config
```

在 `declare ServerConfiguration { ... }` 里面加一行：

```text
string ListenIP 0.0.0.0
```

确认写进去了：

```bash
sudo grep -n "ListenIP" .../SoftEtherVPN/vpnserver/vpn_server.config
```

```text
72:             string ListenIP 0.0.0.0
```

结果重启后启动提示还是 `127.0.0.1`，我当场就懵了。后来用 `ss` 一看：

```bash
sudo ss -tlnp | grep 5555
```

```text
LISTEN 0 128    0.0.0.0:5555    0.0.0.0:*    users:(("vpnserver",pid=1254048,fd=36))
LISTEN 0 128       [::]:5555       [::]:*    users:(("vpnserver",pid=1254048,fd=38))
```

`0.0.0.0`，明明已经绑到所有接口了。原来启动提示只是随便挑一个网卡地址来显示，纯属假象。

前面打印出来的这个内网 IP 居然是**展示用**的，不代表它只监听这个地址。依旧踩坑。

> 顺便把 systemd 单元补了，不然后面老是 `Unit vpnserver.service not found`：
>
> ```bash
> sudo tee /etc/systemd/system/vpnserver.service << 'EOF'
> [Unit]
> Description=SoftEther VPN Server
> After=network.target
> 
> [Service]
> Type=forking
> ExecStart=.../SoftEtherVPN/vpnserver/vpnserver start
> ExecStop=.../SoftEtherVPN/vpnserver/vpnserver stop
> Restart=on-failure
> RestartSec=10
> 
> [Install]
> WantedBy=multi-user.target
> EOF
> 
> sudo systemctl daemon-reload
> sudo systemctl enable --now vpnserver
> ```

然后我在 Windows 上测管理端口：

```text
C:\Users\ttwe77>curl http://1**.***.***.***:5555/
curl: (52) Empty reply from server
```

端口在监听，但就是没响应。查了一下才知道——**5555 是 HTTPS 专用端口，不吃明文 HTTP**，收到 HTTP 直接就掐了。换协议：

```bash
curl -k -i https://1**.***.***.***:5555/
```

终于通了，然我我就用浏览器打开了这个页面。结果啥也没有

## 配它

图形管理器在 Windows 上跑，直接经过Tailscale远程管理，超方便的。

这里的配置GUI已经说得很详细了，这里不再展开。

## 连不上

这一段是重头戏，错误一层套一层。

### 事件 734：隧道通了，IP 没发下来

Windows 事件日志：

```xml
<Provider Name="RasClient" />
<EventID Qualifiers="0">20227</EventID>
<Data>ttwe77.cn</Data>
<Data>734</Data>
```

尝试连接-报错，系统设置里面没给具体报错原因，还得去事件查看器看报错。这个的意思是 **IPsec 已经过了，但 <span class="hover-hint">PPP<span class="hover-hint__tooltip"><span class="hint-title">PPP（Point-to-Point Protocol，点对点协议）</span>L2TP 隧道里承载的协议，负责在客户端和服务端之间建立链路、分配 IP 地址、进行用户认证。文章里“PPP 认证失败”就是这一层出了问题。</span></span> 层分配 IP 失败**。也就是虚拟 DHCP 没应答。

回头去看 <span class="hover-hint">SecureNAT<span class="hover-hint__tooltip"><span class="hint-title">SecureNAT</span>SoftEther 虚拟 Hub 内置的虚拟 NAT + 虚拟 DHCP 功能，用纯用户态模拟宽带路由器的 NAT 和 DHCP 行为。客户端连接后，SecureNAT 负责给它分配 IP（文章里是 172.0.0.100-200），并做 NAT 让它能访问外网。文章排查“事件 734 / IP 没发下来”时，先检查的就是 SecureNAT 的 DHCP 池。</span></span>——DHCP 池设置得挺正常，`172.0.0.100 - 200`，虚拟主机 IP 是 `172.0.0.1`，<span class="hover-hint">默认网关<span class="hover-hint__tooltip"><span class="hint-title">默认网关</span>Windows 连上 VPN 后默认会把 VPN 设为默认网关，所有流量都走 VPN。如果服务端 NAT 没配好，本来能上网的流量反而被送进黑洞，表现就是“连上就断网”。取消“在远程网络上使用默认网关”后，只有访问 VPN 内网的流量才走隧道，其他流量仍走本地网络，立刻恢复。</span></span>和 DNS 是空的。

> *我寻思这也没问题啊*

### 真正的凶手：PPP 认证

改完还是不行，于是把服务端日志翻出来看：

```text
IPsec IKE Session (IKE SA) 1: This IKE SA is established between the server and the client.
IPsec ESP Session (IPsec SA) 1: This IPsec SA is established between the server and the client.
IPsec Client 1: The L2TP Server Module is started.
L2TP PPP Session [*.*.*.*:1701]: A new PPP session (Upper protocol: L2TP) is started.
L2TP PPP Session: The client denied to accept both the "PAP" and MS-CHAP v2 Protocol.
L2TP PPP Session: A PPP protocol error occurred, or the PPP session has been disconnected.
```

翻译一下：隧道全通了，L2TP 也起来了，但客户端把 <span class="hover-hint">PAP<span class="hover-hint__tooltip"><span class="hint-title">PAP（Password Authentication Protocol）</span>PPP 的一种认证方式，用户名和密码以明文发送，极不安全。SoftEther 的 L2TP 默认可能启用 PAP 作为备选，但 Windows 客户端默认拒绝 PAP。</span></span> 和 <span class="hover-hint">MS-CHAP v2<span class="hover-hint__tooltip"><span class="hint-title">MS-CHAP v2（Microsoft Challenge Handshake Authentication Protocol version 2）</span>微软的 PPP 认证协议，支持双向认证（客户端和服务端互相验证），比 PAP 安全得多。文章解决“事件 734”的办法就是在 Windows VPN 属性里手动勾选 MS-CHAP v2，因为客户端默认可能没选它。</span></span> 全拒了，PPP 认证过不去。

解决在客户端：`Win + R` → `ncpa.cpl` → <span class="hover-hint">VPN<span class="hover-hint__tooltip"><span class="hint-title">VPN（Virtual Private Network，虚拟专用网）</span>在公共网络上建立加密隧道，让不同地点的设备像在同一个局域网里一样通信。文章的核心目的就是“和别人组网打游戏”，VPN 是手段。</span></span> 属性 → **安全**：

- 取消"自动使用我的 Windows 登录名和密码"
- 勾上 **Microsoft CHAP 版本 2 (MS-CHAP v2)**

中间还收到一个 **20223**，看着挺吓人，其实是 `ROUTERLOG_DEVICE_CONNECTED`，正常连接成功日志，不用管。它反而印证了链路早就通了，卡的是认证。

## 连上就断网

VPN 连上之后，本地直接断网。

原因很直白：Windows 默认把 VPN 当默认网关，**所有流量都往 VPN 里送**；服务端 <span class="hover-hint">NAT<span class="hover-hint__tooltip"><span class="hint-title">NAT（Network Address Translation，网络地址转换）</span>把内网私有 IP 映射到公网 IP 的技术。文章里“服务端 NAT 没处理好，就是有去无回”，指的是 VPN 客户端把流量发给服务端后，服务端需要做 NAT 才能把回程流量正确送回客户端；NAT 配错就会出现“连上 VPN 就断网”。</span></span> 没处理好，就是有去无回。

客户端改比较快：

```text
Win + R → ncpa.cpl
→ 右键 VPN 连接 → 属性
→ 网络 → Internet 协议版本 4 (TCP/IPv4) → 高级
→ 取消勾选「在远程网络上使用默认网关」
```

改完立刻恢复正常。

## 安全

我还是有点赛博洁癖的，所以在折腾的最后弄一下安全。

### 阿里云安全组

对于公网的限制，我第一个就想到的就是阿里云的安全组。我最初是设置阻止所有TCP和UDP连接，优先级是100（最低优先级），然后再手动允许特定协议的特定端口。但是我实际测试发现我的设置居然一点用都没有。之后我把优先级改成2，居然也不行。唉哟我最终回退到手动拒绝的模式了。不过阿里云的安全组有一个很神奇的一点就是我手动拒绝了我的VPN的端口（入站），但是我居然还能连上是怎么回事？！

之后手动禁止<span class="hover-hint">UDP 500和UDP 4500端口<span class="hover-hint__tooltip"><span class="hint-title">UDP 500 / UDP 4500</span>IPsec 的标准端口：500 用于 IKE 协商，4500 用于 NAT-T（NAT 穿越）。文章最后在阿里云安全组里“手动禁止 UDP 500 和 UDP 4500”，才真正切断了 L2TP/IPsec 连接，说明之前的安全组规则没有正确生效。</span></span>，成功地连不上了

### 密钥

这个协议的预共享密钥最多只能设置8位，而用户密码似乎没有这些限制。

于是我就用了64位账号密码。

## 测试

在我手机上连接成功之后呢，我开始叫上别人来一起测试。我叫了2个人，把详细的操作图片依次发给了他们。然后我不理解的地方就来了。一个人成功连上，而且能ping通，另一个连不上，提示：

> 不能建立到远程计算机的连接。你可能需要更改此连接的网络设置。

然后还是老方法，叫他去看Windows的事件查看器，结果这个操作居然没写进系统日志，真是奇了怪了。

然后我就将之前我让AI写的Python延迟测试和测速......嗯阿里云的pip镜像下载速度好慢

最后看了一下测试结果，延迟在`69-73ms`内，很不错。

---

## 后话

困了不写了，我想说GUI是对的。

下次试试用<span class="hover-hint">WireGuard<span class="hover-hint__tooltip"><span class="hint-title">WireGuard</span>新一代 VPN 协议，代码量极小（约 4000 行，OpenVPN 是 40 万行），性能高、配置简单，Linux 内核原生支持。文章结尾作者说“下次试试用 WireGuard 吧”，就是因为 WireGuard 比 L2TP/IPsec 更现代、更简洁。</span></span>吧，这个协议过时了。
