---
title: 签赛博证书，过赛博人生
description: 记录一次自建 CA、签发 X.509 证书并折腾 CRL 吊销服务的完整经历，从失败放弃到重新简化流程，附 Windows 下 OpenSSL 签发客户端证书的保姆级教程。
date: 2026-11-10 17:12:15
category: 安全
readtime: 7
author: ttwe77
tags: OpenSSL, 数字证书, CA, CRL, X.509, 赛博证书
license: CC BY-NC 4.0
license_url: https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans
updated: 2026-11-10 17:12:15
---

# 签赛博证书，过赛博人生

## 引言

之前突发奇想想做个<span class="hover-hint">赛博证书<span class="hover-hint__tooltip"><span class="hint-title">赛博证书 / 赛博人生</span>“赛博”是 cyber 的音译，在网络语境中常用来给普通事物加上一层“数字世界、网络空间”的包装色彩。“赛博证书”即作者自己搭建 CA 签发的个人数字证书，“过赛博人生”是作者对自己折腾这套 PKI 流程的调侃式标题。</span></span>，然后又想到自己弄一个<span class="hover-hint">CA<span class="hover-hint__tooltip"><span class="hint-title">CA（Certificate Authority，证书颁发机构）</span>负责签发、管理和吊销数字证书的权威实体。根 CA 是整个信任链的起点，用它的私钥为下级证书或终端证书签名。</span></span>的话要开几个服务。正好现在有空来研究一下。

但是最近《崩坏：星穹铁道》的<span class="hover-hint">货币战争<span class="hover-hint__tooltip"><span class="hint-title">货币战争（《崩坏：星穹铁道》常驻玩法）</span>《崩坏：星穹铁道》于3.7版本（2025年11月5日）推出的常驻策略玩法，融合自走棋与Roguelike元素，玩家通过招募角色、激活羁绊、制定投资策略来组建队伍推进对局。作者在引言中提到它“快结束了”，指的是该玩法的某个赛季或周期接近尾声。</span></span>快结束了，所以我是<span class="hover-hint">主屏折腾、副屏挂机<span class="hover-hint__tooltip"><span class="hint-title">主屏折腾、副屏挂机</span>指一边在主显示器上做正经事（研究 CA），一边在副显示器上挂着游戏自动运行。作者以此说明自己折腾证书时处于“半摸鱼”状态。</span></span>游戏。每次在上面点一下就得照顾下面，烦诶。

## 服务？

都来搭建CA了，没有点在线服务肯定是不行的。就我之前的经历来说，之前用curl GET我的一个用自签名证书的网站时，报错说没有吊销列表。然我我就没多想，写了行绕过SSL验证的参数绕过去了。

> curl: (35) <span class="hover-hint">schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK (0x80092012)<span class="hover-hint__tooltip"><span class="hint-title">schannel: next InitializeSecurityContext failed: CRYPT_E_NO_REVOCATION_CHECK (0x80092012)</span>Windows Schannel（Windows 的 SSL/TLS 实现）在 TLS 握手时无法检查证书吊销状态而抛出的错误。常见原因是客户端访问不到证书中指定的 CRL 分发点或 OCSP 服务器（例如被防火墙拦截、地址不可达）。作者最初用 curl 访问自签名证书站点时报出此错，由此才开始研究 CRL/OCSP。</span></span> - **吊销功能无法检查证书是否吊销**。

现在来正式地了解一下到底缺了啥吧。

我还是先去找了DeepSeek，它说这分为**签名服务**、**管理与自动化服务**、**证书状态查询服务**、**密钥安全保护服务**

看着很乱，但是需要的核心服务也就是**证书状态查询服务（OCSP / <span class="hover-hint">CRL<span class="hover-hint__tooltip"><span class="hint-title">CRL（Certificate Revocation List，证书吊销列表）</span>CA 发布并维护的“黑名单”文件，列出已被吊销的证书序列号及吊销日期。客户端需要批量下载整个列表来检查证书是否被吊销，因此在大规模环境下可能网络开销较大。</span></span>）**。我只要搭建这些服务就好，而**<span class="hover-hint">OpenSSL<span class="hover-hint__tooltip"><span class="hint-title">OpenSSL</span>开源密码学工具库和命令行工具集，可以用来生成密钥、创建 CSR、签发证书、生成 CRL 等。文中几乎所有证书操作都通过 OpenSSL 完成</span></span>**要考虑的可就多了。

## 选择吊销证书服务

然后我就去了解了下这两个服务是个啥玩意。

| 对比维度           | CRL（证书吊销列表）                    | OCSP（在线证书状态协议）                       |
| :----------------- | :------------------------------------- | :--------------------------------------------- |
| **查询模式**       | **批量下载**：下载整个黑名单文件       | **按需查询**：实时请求单个证书状态             |
| **实时性**         | 较低，取决于CRL的更新频率              | 高，接近实时状态                               |
| **效率与开销**     | 文件可能持续增长，**网络开销大**       | 单次响应小，但**每次查询都有延迟和服务器负载** |
| **隐私性**         | **较好**，客户端不直接向CA暴露访问目标 | **较差**，CA的OCSP服务器会记录用户的查询行为   |
| **明确“良好”状态** | **不提供**，仅表示“不在黑名单中”       | **提供**，明确返回“good”状态                   |

嗯CRL是**黑名单**，<span class="hover-hint">OCSP<span class="hover-hint__tooltip"><span class="hint-title">OCSP（Online Certificate Status Protocol，在线证书状态协议）</span>按需实时查询单个证书状态的协议。相比 CRL，它不需要下载整个列表，请求响应更小，但每次查询都会产生延迟和服务器负载，且 OCSP 服务器会记录客户端的查询行为，隐私性弱于 CRL。文中作者最终放弃 OCSP，只保留了 CRL 方案。</span></span>是**按需查询证书状态的服务**。我就那几个证书，不想搞得那么大，就用CRL吧，直接用Nginx分发黑名单就好了。

## 生成根证书

CRL已经选好了，然后就是弄一个<span class="hover-hint">根证书<span class="hover-hint__tooltip"><span class="hint-title">根证书（Root CA Certificate）</span>CA 体系中最高层级的自签名证书，其 basicConstraints 中标记为 CA:TRUE。客户端信任某个根证书，就等于信任由它签发出的整条证书链。</span></span>了。

为了搭建 CA 中心，我还得现在我的工作目录拉<span class="hover-hint">依托大的<span class="hover-hint__tooltip"><span class="hint-title">依托大的</span>“依托答辩”的变体或口语化缩写。“依托答辩”是“一坨大便”的谐音梗，源于B站鬼畜区对主播otto（电棍）相关二创视频的调侃，后来泛化为对低质量、拼凑感强、没有营养的内容的贬义标签。文中“拉依托大的”即“拉了一大坨”的戏谑说法，形容在工作目录里建了一堆目录和文件。</span></span>：

```cmd
# 创建主目录和子目录
mkdir C:\lab-ca\certs, C:\lab-ca\crl, C:\lab-ca\newcerts, C:\lab-ca\private, C:\lab-ca\conf -Force
cd C:\lab-ca
```

然后继续：

```powershell
# 创建索引文件（CA的“账本”）
New-Item -ItemType File -Path index.txt -Force
# 创建序列号文件
"1000" | Out-File -FilePath serial -Encoding ascii
# 创建CRL编号文件
"1000" | Out-File -FilePath crlnumber -Encoding ascii
```

然后就是新建一个`openssl.cnf`文件，填入：

```ini
[ ca ]
default_ca = CA_default

[ CA_default ]
dir               = C:/lab-ca
certs             = $dir/certs
crl_dir           = $dir/crl
new_certs_dir     = $dir/newcerts
database          = $dir/index.txt
serial            = $dir/serial
crlnumber         = $dir/crlnumber
private_key       = $dir/private/ca.key.pem
certificate       = $dir/certs/ca.cert.pem
default_md        = sha256
policy            = policy_loose
default_days      = 365
default_crl_days  = 30

[ policy_loose ]
countryName             = optional
stateOrProvinceName     = optional
localityName            = optional
organizationName        = optional
organizationalUnitName  = optional
commonName              = supplied

[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
string_mask        = utf8only
default_md         = sha256
x509_extensions    = v3_ca

[ req_distinguished_name ]
commonName = Common Name

[ v3_ca ]
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints       = critical, CA:true
keyUsage               = critical, digitalSignature, cRLSign, keyCertSign

# ⬇️ 关键：这里填你 Nginx 将来发布 CRL 的地址
[ server_cert ]
basicConstraints       = CA:FALSE
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid,issuer
keyUsage               = critical, digitalSignature, keyEncipherment
extendedKeyUsage       = serverAuth
crlDistributionPoints  = URI:http://localhost:8080/crl/ca.crl.pem
authorityInfoAccess    = OCSP;URI:http://localhost:8080/ocsp
```

> *这个可以https吗？用的Let's Encrypt的证书放在公网 crlDistributionPoints  = URI:http://localhost:8080/crl/ca.crl.pem*
>
> **不可以**
>
> *可以设置location 修改使用的ssl证书吗*
>
> **不可以**

算了不想弄了，放弃了。

## 生成根证书 2

好了这次简单点，直接出根证书，不要CRL了。

### 生成私钥

```cmd
openssl genrsa -aes256 -out rootCA.key 4096
```

> *密码最长多长？*
>
> 看你OpenSSL版本

我啊，直接扔了128位的密码进去，然后：

```cmd
>openssl genrsa -aes256 -out rootCA.key 4096
Enter PEM pass phrase:

Verifying - Enter PEM pass phrase:
```

啊也是设置成功了，那1024位的呢？

```cmd
>openssl genrsa -aes256 -out rootCA.key 4096
Enter PEM pass phrase:

Verifying - Enter PEM pass phrase:


>openssl rsa -check -in rootCA.key
Enter pass phrase for rootCA.key:

Could not find private key from rootCA.key
503E0000:error:1C800064:Provider routines:ossl_cipher_unpadblock:bad decrypt:providers\implementations\ciphers\ciphercommon_block.c:107:
503E0000:error:11800074:PKCS12 routines:PKCS12_pbe_crypt_ex:pkcs12 cipherfinal error:crypto\pkcs12\p12_decr.c:92:maybe wrong password

>openssl rsa -check -in rootCA.key
Enter pass phrase for rootCA.key:

RSA key ok
writing RSA key
-----BEGIN PRIVATE KEY-----
......
-----END PRIVATE KEY-----
```

看来1024位的密码也是支持的。

### 生成证书签名请求（CSR）

```cmd
openssl req -new ^
  -key rootCA.key ^
  -sha256 ^
  -out rootCA.csr
```

```cmd
>openssl req -new ^
More?   -key rootCA.key ^
More?   -sha256 ^
More?   -out rootCA.csr
Enter pass phrase for rootCA.key:

You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Country Name (2 letter code) [AU]:CN
State or Province Name (full name) [Some-State]:Guangxi
Locality Name (eg, city) []:
Organization Name (eg, company) [Internet Widgits Pty Ltd]:TTWE77 Root Authority
Organizational Unit Name (eg, section) []:Security
Common Name (e.g. server FQDN or YOUR name) []:ttwe77-homepage Root CA
Email Address []:ttwe77@yeah.net

Please enter the following 'extra' attributes
to be sent with your certificate request
A challenge password []:
An optional company name []:
```

这就是交互式流程了，有很多的英文，我给你们翻译一下：

```cmd
你即将被要求输入将纳入你的证书请求中的信息。
你将要输入的内容称为可分辨名称（Distinguished Name）或DN。
这里有不少字段，但你可以将某些留空。
对于某些字段，会有默认值。
如果你输入“.”，该字段将留空。

国家名（2字母代码）[AU]：
州或省名（全名）[Some-State]： #省/州名称。可以填英文或拼音，建议不要用中文
地区名（例如城市）[]： #城市/地区名称
组织名（例如公司）[Internet Widgits Pty Ltd]： #组织/公司名称。根 CA 证书建议填你的公司名、项目名或组织名。
组织单位名（例如部门）[]： #部门名称，例如：IT
通用名称（例如服务器FQDN或你的名字）[]： #你的昵称
电子邮件地址[]：

请输入以下“额外”属性
以随你的证书请求一起发送
挑战密码[]： #明文告诉CA你请求操作证书的操作密码
可选的公司名[]：
```

批注我打在上面了，现在证书请求也弄到手了。接下来就是用私钥自签名证书了

### 自签名公钥

```cmd
#生成临时 ext 文件
echo basicConstraints=critical,CA:TRUE,pathlen:0> ca-ext.tmp
echo keyUsage=critical,keyCertSign,cRLSign>> ca-ext.tmp
echo subjectKeyIdentifier=hash>> ca-ext.tmp

#自签名
openssl x509 -req ^
  -in rootCA.csr ^
  -signkey rootCA.key ^
  -sha256 ^
  -days 3650 ^
  -out rootCA.crt ^
  -extfile ca-ext.tmp

#删除临时文件
del ca-ext.tmp
```

然后就是查看刚刚生成的根证书了：

```cmd
openssl x509 -in rootCA.crt -noout -text
```

主要看这一段是不是CA（`CA:TRUE`）：

```cmd
            X509v3 Basic Constraints: critical
                CA:TRUE, pathlen:0
```

## 用途？

然后就是要看给你们签发什么类型的证书了，就我所知的证书类型有：**<span class="hover-hint">SSL证书<span class="hover-hint__tooltip"><span class="hint-title">SSL 证书</span>用于网站 HTTPS 加密的证书，扩展密钥用法通常为 serverAuth。与客户端证书相对，它证明的是服务器的身份。</span></span>**、<span class="hover-hint">客户端证书<span class="hover-hint__tooltip"><span class="hint-title">客户端证书（Client Certificate）</span>用于验证客户端身份的 X.509 证书，扩展密钥用法通常为 clientAuth。在双向 TLS（mTLS）中，服务器可以要求客户端出示该证书来替代用户名密码认证。</span></span>、<span class="hover-hint">S/MIME证书<span class="hover-hint__tooltip"><span class="hint-title">S/MIME 证书</span>Secure/Multipurpose Internet Mail Extensions 证书，主要用于电子邮件签名和加密，确保邮件来源真实、内容未被篡改，并可对邮件正文加密。</span></span>和<span class="hover-hint">代码签名证书<span class="hover-hint__tooltip"><span class="hint-title">代码签名证书</span>用于对软件、可执行文件或脚本进行数字签名的证书。接收方可以通过它验证代码发布者身份，并确认代码在签名后没有被篡改。</span></span>。如果我希望签发一个没有用途的证书该怎么办呢？

> *如何使用openssl签发什么用途也没有的证书?*
>
> *“什么用途也没有的证书”在 <span class="hover-hint">X.509<span class="hover-hint__tooltip"><span class="hint-title">X.509</span>数字证书的国际标准格式。它定义了证书中应包含哪些字段（主题、签发者、公钥、有效期、扩展等），以及这些字段的编码方式。无论是 SSL 证书、客户端证书还是代码签名证书，都遵循 X.509 标准。</span></span> 标准里，指的是**不包含密钥用法（Key Usage）和扩展密钥用法（Extended Key Usage）扩展的证书**。当这两个可选扩展缺失时，OpenSSL 等库会将其解释为**对密钥的使用方式不施加任何限制**，而不是“禁止使用”。*

行，那就弄个客户端证书

## 签发客户端证书

先把私钥弄出来：

```cmd
openssl genrsa -aes256 -out client.key 4096
```

然后写一个扩展配置文件`client.ext`，明确用途：

```ini
[ client_ext ]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature, keyEncipherment
extendedKeyUsage       = clientAuth
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid, issuer
# 如需绑定 email 或主机名，可加 SAN：
# subjectAltName       = email:client@example.com
```

嗯然后把<span class="hover-hint">证书签名请求<span class="hover-hint__tooltip"><span class="hint-title">CSR（Certificate Signing Request，证书签名请求）</span>向 CA 申请证书时提交的文件，包含申请者的公钥和身份信息（DN），并由申请者用对应私钥签名。CA 验证 CSR 后，用 CA 私钥对其中的公钥进行签名，生成正式证书。</span></span>弄出来：

```cmd
openssl req -new -key client.key -out client.csr
```

OK然后就用刚刚生成的根证书给证书签名请求里面的公钥签名：

```cmd
openssl x509 -req -in client.csr ^
  -CA rootCA.crt -CAkey rootCA.key -CAcreateserial ^
  -out client.crt -days 365 -sha256 ^
  -extfile client.ext -extensions client_ext
```

OK啊，那个`client.crt`就是签完名后的证书了。

## 在线证书验证

都是证书了，那肯定要做防伪吧？那就让我们做一个吧：

> 写一个HTML页面，下载/src/rootCA.crt，对用户上传的crt文件进行校验

> `.../tools/app/cyber-cert.html` 1.主体 Subject和签发者用列表呈现。2."01根证书"放在最底部 3.logo用 `.../tools/index.html` 的logo。4.合并“02”和“03”，用户点击按钮可以重新上传。5.`<div class="verdict verdict--pass">`不够大，弄得大一点

> 参考`...\tools\index.html`做1.深色模式 2.左上角圆形返回按钮

> 添加一个免责声明。证书免费签发，不向公众签发，并且给新手解释什么是客户端和X.509证书，没有法律效力

> 备案号

原理就是从服务器下载我的根证书，客户端

为了让这个赛博证书更有真实感，我又去弄了一个可视化的页面：

> 写一个html页面，用纸质证书的形式可视化X.509的客户端证书

然后就是丢到公网上，[链接](https://www.ttwe77.cn/tools/app/cyber-cert.html)

OK也弄完了，然后教你们怎么弄证书：

## 你的证书

原理就是用OpenSSL命令生成一个证书，这里以Windows为例

先去下Windows版本的OpenSSL：[https://slproweb.com/products/Win32OpenSSL.html](https://slproweb.com/products/Win32OpenSSL.html)

> *分发这个软件的人也是一个赛博<span class="hover-hint">活菩萨<span class="hover-hint__tooltip"><span class="hint-title">活菩萨</span>网络用语，字面是菩萨，实际用来调侃无私奉献、做利他之事的人。文中指分发 Windows 版 OpenSSL 的 slproweb 网站——让 Windows 用户不用自己编译就能用上 OpenSSL。</span></span>*

然后跟前面类似：

1. 生成私钥

```cmd
openssl genrsa -aes256 -out client.key 4096
```

然后会提示你输入你的私钥密码

> Enter <span class="hover-hint">PEM<span class="hover-hint__tooltip"><span class="hint-title">PEM 与 DER</span>数字证书和密钥的两种常见编码格式。PEM 是 Base64 编码的文本格式，以 -----BEGIN ...----- 开头；DER 是二进制格式。OpenSSL 默认输出 PEM，而某些场景（如 Nginx 读取 CRL）可能需要格式转换。</span></span> pass phrase:
>
> Verifying - Enter PEM pass phrase:

> 输入PEM密码：
>
> 请重新输入PEM密码：

2. 然后写一个扩展配置文件`client.ext`

在你的工作目录下创建一个文件，名字和后缀名为`client.ext`（新建文本文档.txt，然后改名为client.ext。没有显示后缀的话Win+E、查看-显示-文件扩展名）

```ini
[ client_ext ]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature, keyEncipherment
extendedKeyUsage       = clientAuth
subjectKeyIdentifier   = hash
authorityKeyIdentifier = keyid, issuer
# 把client@example.com换成你的邮箱地址
subjectAltName       = email:client@example.com
```

3. 然后生成证书签名请求：

```cmd
openssl req -new -key client.key -out client.csr
```

然后OpenSSL会让你写一堆信息，翻译为中文就是：

```cmd
你即将被要求输入将纳入你的证书请求中的信息。
你将要输入的内容称为可分辨名称（Distinguished Name）或DN。
这里有不少字段，但你可以将某些留空。
对于某些字段，会有默认值。
如果你输入“.”，该字段将留空。

国家名（2字母代码）[AU]： #例如CN
州或省名（全名）[Some-State]： #省/州名称，比如Guangdong。可不填。可以填英文或拼音，建议不要用中文
地区名（例如城市）[]： #城市/地区名称，可不填。例如Shenzhen
组织名（例如公司）[Internet Widgits Pty Ltd]： #组织/公司名称，可不填。建议填你的公司名、项目名或组织名。
组织单位名（例如部门）[]： #部门名称，可不填，例如：IT
通用名称（例如服务器FQDN或你的名字）[]： #你的昵称
电子邮件地址[]：

请输入以下“额外”属性
以随你的证书请求一起发送
挑战密码[]： #明文告诉CA你请求操作证书的操作密码，可不填
可选的公司名[]： #可不填
```

之后把生成的`client.csr`发给我就可以了

之后你会收到我发给你的`client.crt`，这就是你的证书了。

你们可以去[链接](https://www.ttwe77.cn/tools/app/cyber-cert.html)验证你的证书是否有效