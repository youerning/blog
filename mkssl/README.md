# 一文搞定SSL证书的所有创建问题
创建SSL证书是一个很无聊的过程, 偏偏有时候它又很重要, 但是无聊的事情实在让人乏味, 以后一定会忘记, 那就写一篇比较完全的文章留作以后复制粘贴吧。
> 虽然TLS跟SSL不是同一个东西, 但是就当下的语境而言, 两者基本没有什么区别。

## CA证书
为了保证数据的完整性, 加密性, 所以设计了对称加密, 对称加密虽然可以加密, 但是密钥泄露了就全部暴露了, 并且还要保证这个密钥的传输是可靠的, 怎么保证密钥的传输是可靠呢？再次生成一个密钥? 然后就会陷入先有鸡还是先有蛋的问题.

总的来说对称加密很难保证密钥传输的可靠性, 所以又有了非对称加密.非对称加密就不止一个密钥了, 有两个一个叫做公钥, 一个叫做私钥, 公钥加密的数据只能私钥解密, 私钥加密的数据也只能公钥解密。所以密钥传输的问题就完美解决了, 小明将公钥发给小红, 小红收到之后将自己的公钥也发给小明, 然后双方就可以愉快的用对方的公钥加密数据了, 小明用小红的公钥加密数据发给小红, 反之亦然, 因为传输过程中只有公钥, 所以传输过程中的其他人得到公钥也没用, 因为他们没有私钥, 无法解密传输的内容.

问题好像解决了, 但是新的问题又诞生了, 假设小明和小红通过小王传递数据, 小王忽然很想知道两者到底传输了啥, 所以生成两份密钥对, 假设是密钥对1, 密钥对2, 小明传公钥给小红的时候, 小王将自己密钥对1的公钥给了小红, 小红传公钥给小明的时候, 小王将自己密钥对2的公钥给了小明, 小明和小红以为拿到了对方的公钥就开心的加密数据了, 但是公钥都是小王的, 小王完美的查看到了两者的传输内容, 这就是传说中的中间人攻击了。那么怎么解决呢?

因为无法保证对方的公钥合法性, 所以有一撮人成立了一个机构, 这个机构你可以叫它CA, CA专门给人签名, 并且在你们传输数据前就已经有了CA的公钥(现在的系统, 软件等都内置了一堆CA证书), 通过签名你可以知道公钥是否合法, 签了名的公钥还能叫公钥么? 嗯, 得取个新名字, 就叫做证书吧. 小明和小红就找到CA搞了一个证书, 但是小王不可以么? 当然可以. CA可不管这些, 那么怎么办呢?

所以证书里面应该包含一些东西, 是可以标识对方身份的, 比如域名, IP地址, 像我们看到的https网站里的证书里都有绑定的域名, 其对应的字段是DNS Names, 所以小明和小红申请了一个域名example.com, CA会验证小明小红是否拥有这个域名, 小明和小红需要完成CA给予的挑战, 比如域名的记录多一个TXT记录, 写个CACAwoaini之类的, 然后CA就知道对方的确拥有这个域名, 那么就可以签名了, 小明小红就拿到了证书, 至此就可以愉快的聊天了. 可是小王还是想劫持两者的对话也去CA去签名example.com, 但是CA说你也完成一些挑战吧, 给域名增加TXT记录吧, 就叫做woshigebilaowang, 但是小王没有这个域名, 所以无法完成验证, 因此拿不到example.com的证书. 因此小王就自己搞了CA证书来签名自己的证书继续劫持会话, 当故技重施的时候, 小红小明都发现证书货不对板, 因为小王的CA证书根本不在自己的受信任列表内, 所以就发现了小王的阴谋, 从此换了一个人来传递数据(换了运营商/网络接入方式等).

总的来说, CA确保了证书的可靠性. 但是面临了与对称加密时的同样问题, 怎么保证CA的传递呢? 如果有心之人给你装了自签名CA证书或者将浏览器中植入了自签名证书等, 都会导致CA的失效, 所以不能轻易的从未知网址下载软件.


## 命令行工具
下面会介绍一些我用过的命令行工具, 虽然openssl可以解决所有问题, 但是它的那些命令行参数及配置文件实在是容易忘记, 所以想完全定制自己的ssl证书我才会使用openssl, 大多数情况下我都会用其他的命令行工具代替, 人生苦短, 明明一行命令能解决的问题为啥要那么复杂呢?是吧

这里假设我们要创建的证书域名是example.com

### certinfo
在是用各个工具之前, 这里先介绍一个查看证书的命令行工具: certinfo

假设我们要查看baidu.com的证书, 使用以下命令即可
```shell
certinfo baidu.com:443
```
显示结果如下:
```txt
--- [baidu.com:443 TLS 1.2] ---
Version: 3
Serial Number: 11567442207000512002371158812715313681
Signature Algorithm: SHA256-RSA
Type: end-entity
Issuer: CN=DigiCert Secure Site Pro CN CA G3,O=DigiCert Inc,C=US
Validity
    Not Before: Feb 11 00:00:00 2022 UTC
    Not After : Feb 25 23:59:59 2023 UTC
Subject: CN=www.baidu.cn,O=BeiJing Baidu Netcom Science Technology Co.\, Ltd,ST=Beijing,C=CN
DNS Names: www.baidu.cn, baidu.cn, baidu.com, baidu.com.cn, w.baidu.com, ww.baidu.com, www.baidu.com.cn, www.baidu.com.hk, www.baidu.hk, www.baidu.net.au, www.baidu.net.ph, www.baidu.net.tw, www.baidu.net.vn, wwww.baidu.com, wwww.baidu.com.cn
IP Addresses:
Key Usage: Digital Signature, Key Encipherment
Ext Key Usage: Server Auth, Client Auth
CA: false

Version: 3
Serial Number: 6807354621841521274861062396893733477
Signature Algorithm: SHA256-RSA
Type: intermediate
Issuer: CN=DigiCert Global Root CA,OU=www.digicert.com,O=DigiCert Inc,C=US
Validity
    Not Before: Mar 13 12:00:48 2020 UTC
    Not After : Mar 13 12:00:48 2030 UTC
Subject: CN=DigiCert Secure Site Pro CN CA G3,O=DigiCert Inc,C=US
DNS Names:
IP Addresses:
Key Usage: Digital Signature, Cert Sign, CRL Sign
Ext Key Usage: Server Auth, Client Auth
CA: true

--- 1 verified chains ---
```
最前面的就是baidu.com自己的证书, 后面的就是证书链, 依次代表CA签发的顺序.
DNS Names代表整个证书绑定的域名
IP Address代表绑定的IP地址, 可以看到baidu.com没有, 但是一些DOT DNS协议的证书是有的, 比如dns.alidns.com


项目地址: https://github.com/pete911/certinfo
下载地址: https://github.com/pete911/certinfo/releases

### mkcert
如果你急切的想创建一个ssl证书并安装对应的根证书到当前环境的话, 用mkcert准没错, 一行命令即可.
```shell
mkcert example.com
```
然后就会发现本地生成了以下两个文件
```shell
example.com-key.pem  example.com.pem
```
example.com-key.pem是证书的私钥, example.com.pem是公钥, 有了这两个文件就可以配置对应应用的ssl证书了, 比如nginx, apache等web服务器, 又或者是自己的代码。

但是当你用浏览器访问的时候你会发现, 这个证书是不受信任的, 因为这个证书是自己的签名, 所以浏览器无法识别签名端, 如果我们用certinfo查看一下证书的详情就会发现, 签名者是本机地址, 结果如下
```txt
xxxxxxxxxxxxxxxxxx
```
可以看到Issuer那行不是浏览器信任的任何一个机构, 所以浏览器提示危险, 那么浏览器信任哪些机构呢?通过在浏览器打开`chrome://settings/security` -> 管理证书 -> 受信任的根证书颁发机构.就能看到一堆受信任的CA机构了.

当然了, 这个问题也不是一定要解决, 因为你可以"接受风险继续", 因为你知道自己在干什么, 但是你就是不爽这个风险的提示, 那么可以执行`mkcert -install`将mkcert生成的CA证书安装到当前系统中, 这样你就可以去掉那个烦人的风险提示了。
> 除了默认安装到系统中, 还可以选择java, nss等环境中

项目地址: https://github.com/FiloSottile/mkcert
下载地址: https://github.com/FiloSottile/mkcert/releases

### openssl
用mkcert很爽, 但是缺少一些更细致的处理(如果你需要的话), 比如Subject字段的设置, 密钥长度, 绑定IP地址等。如果说哪个工具可以解决ssl证书的所有问题, 那么openssl当仁不让, 无人能出其右, 独自撑起ssl证书一片天。

创建自签名证书大致分为三步, 创建CA证书, 创建自签名请求, CA签名。

#### 创建CA证书
```shell
# 创建ca证书的私钥
openssl genrsa -out ca.key 3072

# 创建ca证书的自签名请求
openssl req -new -key ca.key -out ca.csr

# 基于自签名请求创建ca证书
openssl x509 -req -in ca.csr -signkey ca.key -out ca.crt
```
通过上面三个命令你就得到了三个文件, ca.key, ca.csr, ca.crt. 其中ca.csr属于中间文件, 只在申请创建证书时有用.

签名请求文件的作用在于解耦了密钥与签名的操作, 私钥自然不能直接给CA, 所以通过私钥创建一个签名请求给CA, 这个请求中包含许多东西, 比如Subject字段, DNS Names, IP Addresses字段(默认情况下不会设置. 设置需要一个额外的配置文件)

> 证书的IP Address字段在ip认证的时候很有用, 比如直接通过ip进行连接, 这样就跳过了域名的解析, 那么怎么知道这个证书是否绑定了对方呢? 那就需要IP Address这个字段了。

#### 创建自签名请求
```shell
# 创建证书本身的私钥
openssl genrsa -out server.key 3072

# 创建证书的签名需求
openssl req -new -out server1.csr -key server.key
```
如果不指定任何配置文件, 创建的自签名请求文件只包含域名和主体信息, 如果我们需要设置一些额外的值, 比如IP Address, 可以创建一个下面的文件来完成
```txt
[ req ]
default_bits = 4096
distinguished_name = req_distinguished_name
req_extensions = req_ext

[ req_distinguished_name ]
countryName                 = Country Name (2 letter code)
countryName_default         = cn
stateOrProvinceName         = State or Province Name (full name)
stateOrProvinceName_default = gd
localityName                = Locality Name (eg, city)
localityName_default        = sz
organizationName            = Organization Name (eg, company)
organizationName_default    = self
organizationalUnitName            = Organizational Unit Name (eg, section)
organizationalUnitName_default    = as
commonName                  = Common Name (e.g. server FQDN or YOUR name)
commonName_max              = 64
commonName_default          = example.com

[ req_ext ]
subjectAltName = @alt_names

[alt_names]
IP.1 = 192.168.31.11
DNS.1 = example.com
DNS.2 = *.example.com
```
然后通过以下命令创建自签名请求
```shell
openssl req -new  -out server2.csr -key server.key -config ssl.conf
```

#### CA签名
上一节我们创建了两个签名请求, 接下来看看两者创建的证书有何不同
```shell
# 基于csr创建证书
openssl x509 -req -days 365 -in server1.csr -signkey ca.key -out server1.crt

# 通过额外指定配置文件创建
openssl x509 -req -days 365 -in server2.csr -signkey ca.key -out server2.crt --extensions req_ext -extfile ssl.conf
```
通过certinfo查看证书内容, 会发现server2.crt的IP Address字段多了IP地址。

### 小结
mkcert很快, 但是定制型相比于openssl会少很多, openssl很全很强大, 但是相较于mkcert会复杂一些.
如果你想找一个介于两者之间的工具, 可以看看cfssl, 但是这个本人玩得不是很懂。cfssl还额外的提供了许多有用的命令, 比如通过`cfssl certinfo -csr xxx.csr`查看证书签名请求。


## 免费证书
免费的ssl证书已经有很多了, 但是在本人的记忆中是let's encrypt极快的推动的免费ssl证书的进程。

值得注意的是证书分为三种, 域名验证型（DV）证书, 组织验证（OV）, 扩展验证（EV）, 而let's encrypt提供的是第一种, 对于个人而言, 三者没有太大的区别, 因为个人一般要求很低, 能够加密数据就行, 如果有更高的要求还是需要额外花费一笔钱去购买证书的。还有就是免费证书一般时间不会很长, 60天,90天不等, 不同的机构不一样, 所以需要额外的处理续期的问题, 当然了, 续期也是免费的。

要获得免费证书需要完成一些挑战, 大致分为两类, 访问挑战, DNS挑战。

访问挑战指以约定的方式防止指定的内容, 比如你的域名需要能够提供http://<你的域名>/.well-known/acme-challenge/<TOKEN>地址的访问.

DNS挑战指在域名的记录中加入指定的内容, 比如在你的域名下创建一天TXT记录, 值是_acme-challenge.<YOUR_DOMAIN>.

当然了, 官方不是这么命名的, 分别是HTTP-01验证, DNS-01验证, 还有TLS-SNI-01验证, TLS-ALPN-01验证. 各个验证详情参考: https://letsencrypt.org/zh-cn/docs/challenge-types/


### lego
lego是一个用golang写的工具, 所以有很好的一致性, 没有依赖, 基本可以下载到各个平台的二进制执行文件.个人建议使用dns验证, 如果你拥有这个域名的话。下面的命令是dns提供商是cloudflare的情况。

由let's encrypt颁发私钥及证书.
```shell
CLOUDFLARE_EMAIL="you@example.com" \
CLOUDFLARE_API_KEY="yourprivatecloudflareapikey" \
lego --email "you@example.com" --dns cloudflare --domains "example.org" run
```

如果你信不过let's encrypt颁发的私钥, 或者对私钥的加密等级有更高的请求, 可以通过创建一个签名请求来创建证书
```shell
CLOUDFLARE_EMAIL="you@example.com" \
CLOUDFLARE_API_KEY="yourprivatecloudflareapikey" \
lego --email="you@example.com" --dns cloudflare --csr="/path/to/csr.pem" run
```
证书签名请求(csr.pem)可以参考使用上文的openssl段落创建.

值得注意的是, let's encrypt不支持在证书签名请求中设置IP, 这意味着只能通过域名访问才能验证证书的合法性, 这对于大多数人没啥影响, 但是你想做一个可以IP访问的DOT DNS服务的时候会有影响....当然了, 只是直接IP访问不行而已, 通过域名还是阔以滴。

项目地址: https://github.com/go-acme/lego
下载地址: https://github.com/go-acme/lego/releases

### 其他工具
acme.sh 一个超级长的脚本, 但是相较于二进制文件会占用空间小很多, 功能很全, 可以选择不同的证书机构.   
certbot let's encrypt的亲儿子, 挺好的就是没用过, 不评价     
caddy 如果你不想使用nginx, 需要一个自动搞定证书申请及续期的web服务器, caddy值得依赖.    

## 其他渠道
值得注意的是一些云厂商会提供免费的ssl证书, 比如腾讯云会提供时间一年的免费证书。


## 编程语言
最后是使用编程语言来完成证书的创建工作, 这里选择的编程语言是golang. 命令行工具很好, 但是编程语言有时更棒.

### 创建私钥
一般来说加密算法选择RSA, ECC即可.而通过golang创建是很简单的.
```go
package main

import (
	"crypto"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/pem"
	"flag"
	"io/ioutil"
	"log"
)

var ecc bool
var out string

func generateKey() (crypto.PrivateKey, error) {
	if ecc {
		return ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
	}
	return rsa.GenerateKey(rand.Reader, 2048)
}

func main() {
	flag.BoolVar(&ecc, "ecdsa", false, "创建ecdsa算法创建密钥")
	flag.StringVar(&out, "out", "server.key", "密钥输出路径")
	flag.Parse()

	priv, err := generateKey()
	checkErr(err)
	privDER, err := x509.MarshalPKCS8PrivateKey(priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "PRIVATE KEY", Bytes: privDER}), 0640)
	checkErr(err)
}

func checkErr(err error) {
	if err != nil {
		log.Fatal(err)
	}

}
```
然后通过下面命令即可在当前目录创建一个名字是server.key的密钥.
```go 
go run src/cmd/new_key/main.go
```
>  默认使用RSA算法, 当然了, 还可以指定是否用ecc算法。

### 创建证书签名请求
用代码, 其实这一步可以省略, 因为代码自由度比较高, 直接设置请求的各个熟悉即可, 但是可能用得到, 所以写上这一步.
```go
package main

import (
	"crypto"
	"crypto/rand"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"os"
)

var out string
var key string

var (
	country       = "china"
	stateProvince = "GD"
	locality      = "SZ"
	org           = "self"
	orgUnit       = "self"
	commonName    = "example.com"
)

func loadPrivateKey(key string) (crypto.PrivateKey, error) {
	file, err := os.Open(key)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	data, err := ioutil.ReadAll(file)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(data)
	if block == nil || block.Type != "PRIVATE KEY" {
		return nil, fmt.Errorf("解码私钥失败")
	}

	priv, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	return priv, nil
}

func newCSR(key crypto.PrivateKey) ([]byte, error) {
	subject := pkix.Name{Country: []string{country}, Province: []string{stateProvince}, Locality: []string{locality},
		Organization: []string{org}, OrganizationalUnit: []string{orgUnit}, CommonName: commonName}

	template := x509.CertificateRequest{Subject: subject, DNSNames: []string{commonName}}
	return x509.CreateCertificateRequest(rand.Reader, &template, key)
}

func main() {
	flag.StringVar(&out, "out", "server.csr", "证书签名请求输出路径")
	flag.StringVar(&key, "key", "server.key", "私钥路径")
	flag.Parse()
	priv, err := loadPrivateKey(key)
	checkErr(err)
	csr, err := newCSR(priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "CERTIFICATE REQUEST", Bytes: csr}), 0640)
	checkErr(err)

}

func checkErr(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
```
然后通过下面命令即可在当前目录创建一个名字是server.csr的证书签名文件.
```go 
go run src/cmd/new_csr/main.go
```

### 创建CA证书
在创建创建证书前, 自然需要CA证书, 所以首先创建CA证书, 为了简单起见就不单独创建CA的私钥了, 直接使用上文创建的server.key
```go
package main

import (
	"crypto"
	"crypto/rand"
	"crypto/sha1"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/asn1"
	"encoding/pem"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"math/big"
	"os"
	"time"
)

var key string
var out string

func randomSerialNumber() *big.Int {
	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	checkErr(err)
	return serialNumber
}

func loadPrivateKey(key string) (crypto.PrivateKey, error) {
	file, err := os.Open(key)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	data, err := ioutil.ReadAll(file)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(data)
	if block == nil || block.Type != "PRIVATE KEY" {
		return nil, fmt.Errorf("解码私钥失败")
	}

	priv, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	return priv, nil
}

func main() {
	flag.StringVar(&out, "out", "ca.crt", "证书输出路径")
	flag.StringVar(&key, "key", "server.key", "私钥路径")
	flag.Parse()

	priv, err := loadPrivateKey(key)
	checkErr(err)

	pub := priv.(crypto.Signer).Public()

	spkiASN1, err := x509.MarshalPKIXPublicKey(pub)
	checkErr(err)

	var spki struct {
		Algorithm        pkix.AlgorithmIdentifier
		SubjectPublicKey asn1.BitString
	}
	_, err = asn1.Unmarshal(spkiASN1, &spki)
	checkErr(err)

	skid := sha1.Sum(spki.SubjectPublicKey.Bytes)

	tpl := &x509.Certificate{
		SerialNumber: randomSerialNumber(),
		Subject: pkix.Name{
			Organization:       []string{"golang deployment CA"},
			OrganizationalUnit: []string{"youerning"},

			// The CommonName is required by iOS to show the certificate in the
			// "Certificate Trust Settings" menu.
			// https://github.com/FiloSottile/mkcert/issues/47
			CommonName: "youerning.org",
		},
		SubjectKeyId: skid[:],

		NotAfter:  time.Now().AddDate(10, 0, 0),
		NotBefore: time.Now(),

		KeyUsage: x509.KeyUsageCertSign,

		BasicConstraintsValid: true,
		IsCA:                  true,
		MaxPathLenZero:        true,
	}
	// 根证书的parent证书是自己
	cert, err := x509.CreateCertificate(rand.Reader, tpl, tpl, pub, priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "CERTIFICATE", Bytes: cert}), 0644)
	checkErr(err)

}

func checkErr(err error, msg ...string) {
	if err != nil {
		log.Fatal(msg)
	}
}
```

然后通过下面命令即可在当前目录创建一个名字是ca.crt的CA证书文件.
```go 
go run src/cmd/new_ca_cert/main.go
```

### 证书签名
至此可以基于上面创建的文件创建CA签名的证书了
```go
package main

import (
	"crypto"
	"crypto/rand"
	"crypto/x509"
	"encoding/pem"
	"flag"
	"fmt"
	"io/ioutil"
	"log"
	"math/big"
	"os"
	"time"
)

var csr string
var key string
var out string
var cacert string

func randomSerialNumber() *big.Int {
	serialNumberLimit := new(big.Int).Lsh(big.NewInt(1), 128)
	serialNumber, err := rand.Int(rand.Reader, serialNumberLimit)
	checkErr(err)
	return serialNumber
}

func loadPrivateKey(key string) (crypto.PrivateKey, error) {
	file, err := os.Open(key)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	data, err := ioutil.ReadAll(file)
	if err != nil {
		return nil, err
	}
	block, _ := pem.Decode(data)
	if block == nil || block.Type != "PRIVATE KEY" {
		return nil, fmt.Errorf("解码私钥失败")
	}

	priv, err := x509.ParsePKCS8PrivateKey(block.Bytes)
	if err != nil {
		return nil, err
	}
	return priv, nil
}

func main() {
	flag.StringVar(&csr, "csr", "server.csr", "证书签名请求文件路径")
	flag.StringVar(&cacert, "ca", "ca.crt", "ca证书文件路径")
	flag.StringVar(&out, "out", "server.crt", "证书输出路径")
	flag.StringVar(&key, "key", "server.key", "私钥路径")
	flag.Parse()

	priv, err := loadPrivateKey(key)
	checkErr(err)
	csrPEMBytes, err := ioutil.ReadFile(csr)
	checkErr(err)
	csrPEM, _ := pem.Decode(csrPEMBytes)
	if csrPEM == nil {
		log.Fatalln("加载证书签名失败")
	}
	if csrPEM.Type != "CERTIFICATE REQUEST" &&
		csrPEM.Type != "NEW CERTIFICATE REQUEST" {
		log.Fatalln("未知的证书签名类型, 期望的值是CERTIFICATE REQUEST, 得到的却是 " + csrPEM.Type)
	}
	csr, err := x509.ParseCertificateRequest(csrPEM.Bytes)
	checkErr(err)
	certPEMBlock, err := ioutil.ReadFile(cacert)
	checkErr(err)
	certDERBlock, _ := pem.Decode(certPEMBlock)
	if certDERBlock == nil || certDERBlock.Type != "CERTIFICATE" {
		log.Fatalln("读取CA证书失败")
	}
	ca, err := x509.ParseCertificate(certDERBlock.Bytes)
	checkErr(err)

	expiration := time.Now().AddDate(2, 3, 0)
	tpl := &x509.Certificate{
		SerialNumber:    randomSerialNumber(),
		Subject:         csr.Subject,
		ExtraExtensions: csr.Extensions,
		NotBefore:       time.Now(), NotAfter: expiration,
		DNSNames:    []string{csr.Subject.CommonName},
		KeyUsage:    x509.KeyUsageKeyEncipherment | x509.KeyUsageDigitalSignature,
		ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
	}
	cert, err := x509.CreateCertificate(rand.Reader, tpl, ca, csr.PublicKey, priv)
	checkErr(err)
	err = ioutil.WriteFile(out, pem.EncodeToMemory(
		&pem.Block{Type: "CERTIFICATE", Bytes: cert}), 0644)
	checkErr(err)

}

func checkErr(err error) {
	if err != nil {
		log.Fatal(err)
	}
}
```

然后通过下面命令即可在当前目录创建一个名字是server.crt的证书文件.
```go 
go run src/cmd/new_cert/main.go
```

## 小结
这些代码都是借鉴自mkcert的源代码. 这里之所以分这么多步是为了对其上文创建证书的步骤, 如果个人使用代码创建的话, 一般一步到位, 不需要这么复杂, 就像mkcert那样, 默认的创建了CA证书, 只需要指定一个域名即可创建对应的证书及密钥了.


## 总结
如果使用openssl创建证书, 你可能需要创建6个文件才能完成工作, 会很抓狂, 如果你还不懂各个步骤的意义就会对证书的创建望而生畏(我以前就是...), 所以出现了极傻瓜式的工具mkcert, 无脑创建证书很快很有用, 它甚至还能帮你安装根证书, 从此世界安静了, 可是随着对证书的深入发现还是会需要openssl来完成更细致的需求, 所以openssl yyds, 自签名证书的一个问题就是无法让所有人接受, 所以需要购买CA机构签名的证书, 但是小网站, 个人而言根本不需要那种专业性的证书, 所以出现大量的免费证书颁发机构, 从此https流量高歌猛进. 


**代码及文章地址**: https://github.com/youerning/blog/tree/master/mkssl