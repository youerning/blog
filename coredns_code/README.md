# CoreDNS粗解

如果你厌倦了那些老古董的DNS服务，那么可以试试Coredns, 因为Caddy出色的插件设计, 所以Coredns的骨架基于caddy构建, 也就继承了良好的扩展性, 又因为Go语言是一门开发效率比较高的语言，所以开发一个自定义的插件是比较简单的事情，但是大多数使用都不需要自己编写插件，因为默认的插件以及外部的插件足够大多数场景了。

本文主要分为四个部分

- 源码阅读
- 自定义插件编写
- 一些非常有用的工具函数



## 源码阅读

如果你不确定，那就阅读源代码吧，代码中存在准确无误的答案。



这里假设启动命令为

```powershell
./coredns
```

并且当前工作目录有一个名称是Corefile的文本文件, 内容如下

```
. {
  forward . 8.8.8.8 1.1.1.1
  log
  errors
  cache
}
```



首先看看coredns的函数入口

```go
// coredns.go
func main() {
	coremain.Run()
}

// coremain\run.go
func Run() 
	flag.StringVar(&conf, "conf", "", "Corefile to load (default \""+caddy.DefaultConfigFile+"\")")
	// 注册一个加载配置文件函数, 如果指定了-conf参数, confLoader就能加载参数对应的配置文件
	caddy.RegisterCaddyfileLoader("flag", caddy.LoaderFunc(confLoader))
    // 如果不指定，自然也没关系, 那就在注册一个默认的配置文件加载函数
	caddy.SetDefaultCaddyfileLoader("default", caddy.LoaderFunc(defaultLoader))

	if version {
		showVersion()
		os.Exit(0)
	}
	if plugins {
		fmt.Println(caddy.DescribePlugins())
		os.Exit(0)
	}
	// Get Corefile input
	corefile, err := caddy.LoadCaddyfile(serverType)
	// Start your engines
	instance, err := caddy.Start(corefile)
	// Twiddle your thumbs
	instance.Wait()
}
```

coredns的启动流程还是比较简洁的,, 可以看到coredns没有太多参数选项, 除了打印插件列表, 显示版本的命令参数之外，就是启动流程了，而启动流程概括起来也不负载，加载配置文件，基于配置文件启动，但是在在深入`caddy.LoadCaddyfile`和`caddy.Start`之前要先看看在此之前运行的`init`方法.

```go
// core\dnsserver\register.go
func init() {
	caddy.RegisterServerType(serverType, caddy.ServerType{
		Directives: func() []string { return Directives },
		DefaultInput: func() caddy.Input {
            // 如果配置文件找不到会加载配置了whoami, log插件的配置文件
			return caddy.CaddyfileInput{
				Filepath:       "Corefile",
				Contents:       []byte(".:" + Port + " {\nwhoami\nlog\n}\n"),
				ServerTypeName: serverType,
			}
		},
		NewContext: newContext,
	})
}
```

因为caddy是一个http/s web服务器，而不是一个dns服务器，所以我们需要在调用caddy启动流程之前注入一个用于dns的ServerType，后续创建的Server等对象都是基于此，并且这个ServerType设置了一个静态的配置文件`".:" + Port + " {\nwhoami\nlog\n}\n"`, 也就是说在没有指定配置文件路径以及本地没有Corefile的情况下，还是能够启动一个默认的dns服务器，这个服务加载了whoami, log两个插件。



### 加载配置文件

在入口函数可以知道, 注入了以下两个配置文件加载函数

```go
// 该函数比较简单, 就是将函数追加到caddyfileLoaders切片中
caddy.RegisterCaddyfileLoader("flag", caddy.LoaderFunc(confLoader))
// 如果caddyfileLoaders切片中所有函数都没有加载到配置文件, 就会使用默认加载函数
caddy.SetDefaultCaddyfileLoader("default", caddy.LoaderFunc(defaultLoader))
```

前者的加载函数就是读取参数-conf指定的配置文件。

后者就是读取本地的Corefile, 如果存在的话。



confLoader的代码如下:

```go
func confLoader(serverType string) (caddy.Input, error) {
	if conf == "" {
		return nil, nil
	}

	if conf == "stdin" {
		return caddy.CaddyfileFromPipe(os.Stdin, serverType)
	}

	contents, err := os.ReadFile(filepath.Clean(conf))
	return caddy.CaddyfileInput{
		Contents:       contents,
		Filepath:       conf,
		ServerTypeName: serverType,
	}, nil
}
```

可以看到逻辑比较简单, 如果指定了-conf参数就通过参数值找到对应的配置文件并返回

因为我们没有指定-conf参数, 所以调用默认加载函数。



LoadCaddyfile加载逻辑如下:

```go
// vendor\github.com\coredns\caddy\caddy.go
func LoadCaddyfile(serverType string) (Input, error) {
	// 通过注册的配置文件加载函数, 默认加载函数加载配置文件
	cdyfile, err := loadCaddyfileInput(serverType)
    // 函数找不到就用
	if cdyfile == nil {
		cdyfile = DefaultInput(serverType)
	}

	return cdyfile, nil
}

// vendor\github.com\coredns\caddy\plugins.go
func loadCaddyfileInput(serverType string) (Input, error) {
	var loadedBy string
	var caddyfileToUse Input
    // 这里只注册一个从命令行参数加载的loader
    // caddy.RegisterCaddyfileLoader("flag", caddy.LoaderFunc(confLoader))
    // 因为没有指定参数, 所以没哟配置文件会加载
	for _, l := range caddyfileLoaders {
		cdyfile, err := l.loader.Load(serverType)
	}
    // 继而调用默认的加载函数
	if caddyfileToUse == nil && defaultCaddyfileLoader.loader != nil {
		cdyfile, err := defaultCaddyfileLoader.loader.Load(serverType)

		if cdyfile != nil {
			loaderUsed = defaultCaddyfileLoader
			caddyfileToUse = cdyfile
		}
	}
	return caddyfileToUse, nil
}
```

上面的主要逻辑就是首先判断注册的加载函数能不能加载到配置文件，如果不能，就调用默认加载函数。

而默认加载函数如下

```go
func defaultLoader(serverType string) (caddy.Input, error) {
    // caddy.DefaultConfigFile = Corefile
	contents, err := os.ReadFile(caddy.DefaultConfigFile)

	return caddy.CaddyfileInput{
		Contents:       contents,
		Filepath:       caddy.DefaultConfigFile,
		ServerTypeName: serverType,
	}, nil
}
```

因为本地有Corefile文件, 所以读取并构造CaddyfileInput对象。

至此配置文件加载完成。



#### 小结

通过代码我们知道配置文件的加载顺序依次是

```shell
命令行参数指定的配置文件 > 当前工作目录的Corefile > 静态设置的Corefile内容（".:" + Port + " {\nwhoami\nlog\n}\n")）
```



### 启动服务

再次粘贴一下前面的启动代码:

```go
// 解析配置文件
instance, err := caddy.Start(corefile)
// 主进程等待退出信号
instance.Wait()
```

基于上一步加载的配置文件开始服务.

代码如下:

```go
func Start(cdyfile Input) (*Instance, error) {
	inst := &Instance{serverType: cdyfile.ServerType(), wg: new(sync.WaitGroup), Storage: make(map[interface{}]interface{})}
    // 启动监听进程
	err := startWithListenerFds(cdyfile, inst, nil)
    
    // 用于重启, 告诉父进程是否重启成功
	signalSuccessToParent()

	// 执行on之类的相关命令, 比如
    // on startup /etc/init.d/php-fpm start
	EmitEvent(InstanceStartupEvent, inst)

	return inst, nil
}


func startWithListenerFds(cdyfile Input, inst *Instance, restartFds map[string]restartTriple) error {
	instances = append(instances, inst)

    // 验证配置文件并解析
	err = ValidateAndExecuteDirectives(cdyfile, inst, false)
	// 创建Server对象用于后续监听服务
	slist, err := inst.context.MakeServers()
	
    // 依次调用各个插件注册的启动函数
	for _, startupFunc := range inst.OnStartup {
		err = startupFunc()
		if err != nil {
			return err
		}
	}

    // 开始监听
	err = startServers(slist, inst, restartFds)
	started = true

	return nil
}
```

启动服务大概可以分为两步

- 解析配置文件

  加载配置的各个插件并按**插件的顺序执行setup函数**, 而不是配置文件插件名出现的顺序加载插件

- 启动监听服务



#### 解析配置文件

```go
func ValidateAndExecuteDirectives(cdyfile Input, inst *Instance, justValidate bool) error {
    // dns
	stypeName := cdyfile.ServerType()
	// 获取dns的serverType, 在core\dnsserver\register.go中注册
	stype, err := getServerType(stypeName)
	inst.caddyfileInput = cdyfile
	// 将配置文件加载成一个个ServerBlock对象
	sblocks, err := loadServerBlocks(stypeName, cdyfile.Path(), bytes.NewReader(cdyfile.Body()))
	// 还是core\dnsserver\register.go中注册的Context
	inst.context = stype.NewContext(inst)

	sblocks, err = inst.context.InspectServerBlocks(cdyfile.Path(), sblocks)
	return executeDirectives(inst, cdyfile.Path(), stype.Directives(), sblocks, justValidate)
}



func executeDirectives(inst *Instance, filename string,
	directives []string, sblocks []caddyfile.ServerBlock, justValidate bool) error {
	storages := make(map[int]map[string]interface{})

	// 最外层的循环是治理，所以配置文件的指令顺序不重要，重要的代码里面的顺序
    // 插件的顺序是根据plugin.cfg文件生成的
	for _, dir := range directives {
		for i, sb := range sblocks {
			var once sync.Once
			// 依次去serverBlocks中检查是否存在该指令
            // keys是 .:53, .:1053之类的监听地址
			for j, key := range sb.Keys {
				if tokens, ok := sb.Tokens[dir]; ok {
					controller := &Controller{
						instance:  inst,
						Key:       key,
						Dispenser: caddyfile.NewDispenserTokens(filename, tokens),
						OncePerServerBlock: func(f func() error) error {
							var err error
							once.Do(func() {
								err = f()
							})
							return err
						},
						ServerBlockIndex:    i,
						ServerBlockKeyIndex: j,
						ServerBlockKeys:     sb.Keys,
						ServerBlockStorage:  storages[i][dir],
					}
                    // 因为各个key都是公用同一个ServerBlocks, 所以没比较初始化两遍
                    if j > 0 {
                        continue
                    }
					
                    // 调用插件的setup方法
                    // 这里只是注册插件，还没将插件构造成pluginChain
					setup, err := DirectiveAction(inst.serverType, dir)
					err = setup(controller)
				}
			}
		}
	}

	return nil
}
```

解析配置文件的主要工作就是解析配置文件的指令，然后根据代码中指令的顺序依次调用对应的setup方法。

setup方法会在自定义插件编写的段落着重介绍，这里只需要知道，setup方法是一个将插件集成到调用链的一个方法就行了。

至此配置文件解析完成，各个插件也加载完成了。是时候启动服务了

> 之所以按照插件在代码顺序执行而不是在配置文件中出现的顺序配置，这是为了避免一些奇怪的问题，比如log和cache放在forward之后缓存和日志就不生效了，这会让人很恼火。



#### 启动监听服务

启动服务的入口大致如下:

```go
// 创建server对象并启动
// 这里的context来自core\dnsserver\register.go
slist, err := inst.context.MakeServers()
err = startServers(slist, inst, restartFds)
```

MakeServers代码如下:

```go
func (h *dnsContext) MakeServers() ([]caddy.Server, error) {

	// 检查配置文件是否有冲突, 比如监听域名是否有重复等
	errValid := h.validateZonesAndListeningAddresses()

	// 共享第一个配置的相关值
	for _, c := range h.configs {
		c.Plugin = c.firstConfigInBlock.Plugin
		c.ListenHosts = c.firstConfigInBlock.ListenHosts
		c.Debug = c.firstConfigInBlock.Debug
		c.TLSConfig = c.firstConfigInBlock.TLSConfig
	}

	// 将监听的端口聚合起来
	groups, err := groupConfigsByListenAddr(h.configs)
    
	// 开始创建caddy.Server
	var servers []caddy.Server
	for addr, group := range groups {
		// switch on addr
		switch tr, _ := parse.Transport(addr); tr {
        // 默认就是DNS
		case transport.DNS:
			s, err := NewServer(addr, group)
			if err != nil {
				return nil, err
			}
			servers = append(servers, s)
        // 还有TLS,GRPC,HTTPS
	}

	return servers, nil
}
    
func NewServer(addr string, group []*Config) (*Server, error) {
	s := &Server{
		Addr:         addr,
		zones:        make(map[string]*Config),
		graceTimeout: 5 * time.Second,
	}

    // 为每个zone构建一个site对象以及对应的stack对象, 并注册各指令，然后赋值pluginChain
    // pluginChain就是后面的响应函数
	for _, site := range group {
		if site.Debug {
			s.debug = true
			log.D.Set()
		}
		s.zones[site.Zone] = site

		var stack plugin.Handler
        // 将插件列表按倒叙依次传给优先级高的插件
        // 这样一层套一层就可以让优先级高的插件在最外层，也就是优先执行。
		for i := len(site.Plugin) - 1; i >= 0; i-- {
			stack = site.Plugin[i](stack)
			site.registerHandler(stack)
			}
		}
		site.pluginChain = stack
	}

	return s, nil
}
```

至此构造好了配置文件中的各个Server对象，然后开始监听服务

startServers代码如下:

```go
func startServers(serverList []Server, inst *Instance, restartFds map[string]restartTriple) error {
	for _, s := range serverList {
		var (
			ln  net.Listener
			pc  net.PacketConn
			err error
		)
		// 可以看到默认tcp和udp同时监听
		if ln == nil {
			ln, err = s.Listen()
			if err != nil {
				return fmt.Errorf("Listen: %v", err)
			}
		}
		if pc == nil {
			pc, err = s.ListenPacket()
			if err != nil {
				return fmt.Errorf("ListenPacket: %v", err)
			}
		}

		inst.servers = append(inst.servers, ServerListener{server: s, listener: ln, packet: pc})
	}

    // 一起启动监听服务
    // tcp接口调用Serve
    // udp接口调用ServePacket
	for _, s := range inst.servers {
		inst.wg.Add(2)
		stopWg.Add(2)
		func(s Server, ln net.Listener, pc net.PacketConn, inst *Instance) {
			go func() {
				defer func() {
					inst.wg.Done()
					stopWg.Done()
				}()
				errChan <- s.Serve(ln)
			}()

			go func() {
				defer func() {
					inst.wg.Done()
					stopWg.Done()
				}()
				errChan <- s.ServePacket(pc)
			}()
		}(s.server, s.listener, s.packet, inst)
	}

	return nil
}
```

至此监听服务启动起来了，可以接口客户端的请求。

这里看看udp的处理逻辑把

```go
// core\dnsserver\server.go
func (s *Server) ServePacket(p net.PacketConn) error {
	s.m.Lock()
    // 这里的Handler实现了ServeDNS接口, 会直接动用传入的函数
	s.server[udp] = &dns.Server{PacketConn: p, Net: "udp", Handler: dns.HandlerFunc(func(w dns.ResponseWriter, r *dns.Msg) {
		ctx := context.WithValue(context.Background(), Key{}, s)
		ctx = context.WithValue(ctx, LoopKey{}, 0)
        // ServeDNS是每个插件都要实现的函数接口, 超级重要的流量入口
        // 最终将数据导向h.pluginChain.ServeDNS
		s.ServeDNS(ctx, w, r)
	})}
	s.m.Unlock()

	return s.server[udp].ActivateAndServe()
}

// 后面的调用链比较长，大家了解一下就行，其实最终还是调用上面的HandlerFunc里面传入的匿名函数
func (srv *Server) ActivateAndServe() error {
	srv.init()

	if srv.PacketConn != nil {
		srv.started = true
		unlock()
		return srv.serveUDP(srv.PacketConn)
	}
	return &Error{err: "bad listeners"}
}

func (srv *Server) serveUDP(l net.PacketConn) error {
	defer l.Close()

	reader := Reader(defaultReader{srv})
	lUDP, isUDP := l.(*net.UDPConn)
	readerPC, canPacketConn := reader.(PacketConnReader)

	rtimeout := srv.getReadTimeout()
	// 不断读取udp包
	for srv.isStarted() {
		var (
			m    []byte
			sPC  net.Addr
			sUDP *SessionUDP
			err  error
		)
		if isUDP {
			m, sUDP, err = reader.ReadUDP(lUDP, rtimeout)
		} else {
			m, sPC, err = readerPC.ReadPacketConn(l, rtimeout)
		}
		wg.Add(1)
        // 每个包创建一个协程专门处理
		go srv.serveUDPPacket(&wg, m, l, sUDP, sPC)
	}

	return nil
}

func (srv *Server) serveUDPPacket(wg *sync.WaitGroup, m []byte, u net.PacketConn, udpSession *SessionUDP, pcSession net.Addr) {
	w := &response{tsigProvider: srv.tsigProvider(), udp: u, udpSession: udpSession, pcSession: pcSession}
	srv.serveDNS(m, w)
	wg.Done()
}

func (srv *Server) serveDNS(m []byte, w *response) {
    // udp包解析
	dh, off, err := unpackMsgHdr(m, 0)

	req := new(Msg)
	req.setHdr(dh)

	switch action := srv.MsgAcceptFunc(dh); action {
	case MsgAccept:
		// 处理细节
	case MsgReject, MsgRejectNotImplemented:
		// 处理细节
	case MsgIgnore:
		// 处理细节
	}
	
    // 这里就是最上面的那个handlerfunc
	srv.Handler.ServeDNS(w, req) // Writes back to the client
}
```

可以看到监听的处理调用链还是比较长的。



#### 小结

Coredns默认会同时监听tcp和udp, 基于解析的配置文件会构造一个pluginChain, 而这个pluginChain就如它的名字那样直白，将插件包装成一个链条依次执行以完成dns解析。



## 自定义插件编写

因为caddy的优秀的插件系统，所以扩展起来很方便。

编写插件大致分为一下几步

- 复制代码框架(模板)
- 注入插件代码
- 重新生成插件列表
- 编译运行



### 复制代码框架(模板)

要开发自己的插件首先要下载coredns的源代码, coredns的代码结构如下:

```shell
tree .
├── ADOPTERS.md
├── CODE_OF_CONDUCT.md -> .github/CODE_OF_CONDUCT.md
├── CODEOWNERS
├── CONTRIBUTING.md -> .github/CONTRIBUTING.md
├── core
├── coredns.1.md
├── coredns.go
├── corefile.5.md
├── coremain
├── directives_generate.go
├── Dockerfile
├── go.mod
├── go.sum
├── GOVERNANCE.md
├── LICENSE
├── Makefile
├── Makefile.doc
├── Makefile.docker
├── Makefile.release
├── man
├── notes
├── owners_generate.go
├── pb
├── plugin
├── plugin.cfg
├── plugin.md
├── README.md
├── request
├── SECURITY.md -> .github/SECURITY.md
└── test
```

官方提供了一个可以直接运行的示例: https://github.com/coredns/example, 你可以拷贝下来做成自己的一个模块, 比如:

```go
go mod init github.com/{github账号}/{你的仓库名}
```

或者将其直接复制到coredns的plugin目录



这里使用第二种方法,  本文的插件名叫dforward

所以目录结构如下:

```shell
.
├── coredns.go
├── directives_generate.go
├── Dockerfile
├── go.mod
├── go.sum
├── plugin
│   ├── acl
│   ├── example  # 自定插件在这
│   # 省略其他插件名
└── test
    ├── auto_test.go

63 directories, 196 files
```



### 注入插件代码

为了让我们的插件集成到coredns里面，我们需要编辑plugin.cfg文件以及重新生成代码。

从上面的源代码阅读我们知道插件的顺序很重要，所以不能将插件的顺序放在太前，假设我们的插件放在第一位，那么log, errors等插件就都不会在我们自定义的插件前被调用，还有就是cache插件就不能正常缓存了，当然了，如果你的插件就是类似于log, errors, cache等插件的功能，那么你可以将其放在较前面的顺序，具体顺序应该具体分析。

效果如下:

```shell
loop:loop
example:example  # 你的插件在这个位置
forward:forward
grpc:grpc
```

如果你是使用第一种方法注入编写插件，那么效果如下:

```shell
loop:loop
dforward:github.com/{github账号}/{你的仓库名}  # 你的插件在这个位置
forward:forward
grpc:grpc
```

### 重新生成插件列表

重新生成相关代码，并不复杂，只需要在coredns代码根目录执行一条命令即可。

```shell
go generate
```

如果没有出现错误, 你会发现`core\dnsserver\zdirectives.go` 和`core\plugin\zplugin.go`两个文件出现了dforward的相关信息。

### 编译运行

然后就可以在Corefile文件里面使用example的指令了。

example这个指令的唯一功能就是在日志中输出一个example。



### 小结

编写Coredns的插件并不复杂，唯一要考虑的是，是不是需要编写自己的插件，可以先了解内置的插件列表以及外部的插件列表中的各个插件功能在决定是否需要编写，很多时候是不需要，如果你真的需要编写一个自己的插件来满足特定的功能，也不需要自己实现各种功能，比如转发你可以直接调用forward插件，缓存可以直接调用cache插件等，再者就是coredns有许多常用的工具函数，这些放在下一个段落。



## 一些常用的工具函数

一些在域名解析中常用到的函数等



### 判断一个域名是否是一个zone(可以简单认为是域名)列表的子域名。

```go
import (
	"fmt"

	"github.com/coredns/coredns/plugin"
)

func main() {
	zones := []string{"a.com.", "b.com."}
	fmt.Println(plugin.Zones(zones).Matches("xx.a.com."))
	fmt.Println(plugin.Zones(zones).Matches("xx.c.com.")) // 没匹配上就会输出空字符串
}

```

输出如下:

```shell
a.com.

```

> 如果是很多域名的话，建议搞一个前缀树来匹配，因为这里的Matches方法是便利列表来匹配的。



### 解析dns各种协议

coredns支持dns, tls(dot), https(doh), grpc等多种传输协议

```go
package main

import (
	"fmt"

	"github.com/coredns/coredns/plugin/pkg/parse"
)

func main() {
	hosts := []string{
		"tls://127.0.0.1:853",
		"127.0.0.1:53",
		"grpc://127.0.0.1:999",
		"https://127.0.0.1:1443",
	}
	for _, host := range hosts {
		trans, addr := parse.Transport(host)
		fmt.Println(host, "->", trans, addr)
	}
}
```

输出如下:

```shell
tls://127.0.0.1:853 -> tls 127.0.0.1:853
127.0.0.1:53 -> dns 127.0.0.1:53
grpc://127.0.0.1:999 -> grpc 127.0.0.1:999
https://127.0.0.1:1443 -> https 127.0.0.1:1443
```



### 各种协议的请求

根据需要发起各种类型的请求

我们可以不用到处找支持这些协议的dns服务器，用coredns自身监听即可，下面是配置文件

```
.:53 tls://.:853 https://.:1043 {
  tls plugin/tls/test_cert.pem plugin/tls/test_key.pem plugin/tls/test_ca.pem
  log
  errors
  hosts example.hosts
}
```

example.hosts就只有一行

```shell
127.0.0.1 example.com
```

coredns有一个小小的坑, 如果你没有显式的设置证书，那么即使是指定了tls, https等协议，最终还是以tcp和http的方式来监听。

> 个人觉得更好的体验是自动在本地创建一个证书或者在日志中发出警告, 但是coredns暗搓搓的把tls的那层给去掉了。。。。。



#### 原生的DNS请求

```go
package main

import (
	"fmt"
	"net"
	"os"
	"time"

	"github.com/miekg/dns"
)

func main() {
	if len(os.Args) == 1 {
		fmt.Println("必须指定一个域名")
		os.Exit(1)
	}
	// 将域名标准化, 比如example.com 变成 example.com. 最后面加了一个点
	query := dns.Fqdn(os.Args[1])
	m1 := new(dns.Msg)
	m1.Id = dns.Id()
	m1.RecursionDesired = true
	m1.Question = make([]dns.Question, 1)
	m1.Question[0] = dns.Question{Name: query, Qtype: dns.TypeA, Qclass: dns.ClassINET}
	c := new(dns.Client)
	in, rtt, err := c.Exchange(m1, "127.0.0.1:53")
	if err != nil {
		panic(err)
	}

	if len(in.Answer) == 0 {
		fmt.Println("没有查询到任何结果")
		os.Exit(1)
	}

	if a, ok := in.Answer[0].(*dns.A); ok {
		fmt.Println("获取到ip地址:", a.A.String())
	} else {
		fmt.Println("返回结果不是A记录:", in)
	}
	fmt.Println("耗时: ", rtt)

	c2 := new(dns.Client)
	laddr := net.UDPAddr{
		IP:   net.ParseIP("[::1]"),
		Port: 12345,
		Zone: "",
	}

	fmt.Println("设置超时的客户端的响应结果:")
	c2.Dialer = &net.Dialer{
		Timeout:   200 * time.Millisecond,
		LocalAddr: &laddr,
	}
	in2, rtt2, err2 := c2.Exchange(m1, "127.0.0.1:53")
	if err2 != nil {
		panic(err)
	}

	if a, ok := in2.Answer[0].(*dns.A); ok {
		fmt.Println("获取到ip地址:", a.A.String())
	} else {
		fmt.Println("返回结果不是A记录:", in)
	}
	fmt.Println("耗时: ", rtt2)
}
```

输出如下:

```shell
获取到ip地址: 127.0.0.1
耗时:  512µs
设置超时的客户端的响应结果:
获取到ip地址: 127.0.0.1
耗时:  0s
```



#### DNS Over TLS请求(DOT)

```go
package main

import (
	"crypto/tls"
	"fmt"
	"log"
	"os"

	"github.com/miekg/dns"
)

func main() {
	tlsConfig := new(tls.Config)
	tlsConfig.InsecureSkipVerify = true
	conn, err := dns.DialWithTLS("tcp", "127.0.0.1:853", tlsConfig)
	if err != nil {
		log.Fatalln("连接出错:", err)
	}
	defer conn.Close()

	query := dns.Fqdn(os.Args[1])
	m1 := new(dns.Msg)
	m1.Id = dns.Id()
	m1.RecursionDesired = true
	m1.Question = make([]dns.Question, 1)
	m1.Question[0] = dns.Question{Name: query, Qtype: dns.TypeA, Qclass: dns.ClassINET}
	err = conn.WriteMsg(m1)
	if err != nil {
		log.Fatal("发送请求失败:", err)
	}
	ret, err := conn.ReadMsg()
	if err != nil {
		log.Fatal("读取响应失败:", err)
	}
	fmt.Println(ret)
}
```

输出如下:

```shell
获取到ip地址: 127.0.0.1
```



#### DNS Over HTTPS请求(DOH)

```go
package main

import (
	"crypto/tls"
	"fmt"
	"os"

	"bytes"
	"encoding/base64"
	"io"
	"net/http"

	"github.com/miekg/dns"
)

func main() {

	query := dns.Fqdn(os.Args[1])
	m1 := new(dns.Msg)
	m1.Id = dns.Id()
	m1.RecursionDesired = true
	m1.Question = make([]dns.Question, 1)
	m1.Question[0] = dns.Question{Name: query, Qtype: dns.TypeA, Qclass: dns.ClassINET}
	req, err := NewRequest("GET", "127.0.0.1:1043", m1)
	if err != nil {
		panic("创建请求失败: " + err.Error())
	}

	httpClient := http.Client{}
	httpClient.Transport = &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	resp, err := httpClient.Do(req)
	if err != nil {
		panic("读取响应失败: " + err.Error())
	}

	in, err := ResponseToMsg(resp)
	if err != nil {
		panic("解析响应结果失败: " + err.Error())
	}
	if len(in.Answer) == 0 {
		fmt.Println("没有查询到任何结果")
		os.Exit(1)
	}

	if a, ok := in.Answer[0].(*dns.A); ok {
		fmt.Println("获取到ip地址:", a.A.String())
	} else {
		fmt.Println("返回结果不是A记录:", in)
	}
}

// 以下代码复制自plugin\pkg\doh
// MimeType is the DoH mimetype that should be used.
const MimeType = "application/dns-message"

// Path is the URL path that should be used.
const Path = "/dns-query"

// NewRequest returns a new DoH request given a method, URL (without any paths, so exclude /dns-query) and dns.Msg.
func NewRequest(method, url string, m *dns.Msg) (*http.Request, error) {
	buf, err := m.Pack()
	if err != nil {
		return nil, err
	}

	switch method {
	case http.MethodGet:
		b64 := base64.RawURLEncoding.EncodeToString(buf)

		req, err := http.NewRequest(http.MethodGet, "https://"+url+Path+"?dns="+b64, nil)
		if err != nil {
			return req, err
		}

		req.Header.Set("content-type", MimeType)
		req.Header.Set("accept", MimeType)
		return req, nil

	case http.MethodPost:
		req, err := http.NewRequest(http.MethodPost, "https://"+url+Path+"?bla=foo:443", bytes.NewReader(buf))
		if err != nil {
			return req, err
		}

		req.Header.Set("content-type", MimeType)
		req.Header.Set("accept", MimeType)
		return req, nil

	default:
		return nil, fmt.Errorf("method not allowed: %s", method)
	}
}

// ResponseToMsg converts a http.Response to a dns message.
func ResponseToMsg(resp *http.Response) (*dns.Msg, error) {
	defer resp.Body.Close()

	return toMsg(resp.Body)
}

// RequestToMsg converts a http.Request to a dns message.
func RequestToMsg(req *http.Request) (*dns.Msg, error) {
	switch req.Method {
	case http.MethodGet:
		return requestToMsgGet(req)

	case http.MethodPost:
		return requestToMsgPost(req)

	default:
		return nil, fmt.Errorf("method not allowed: %s", req.Method)
	}
}

// requestToMsgPost extracts the dns message from the request body.
func requestToMsgPost(req *http.Request) (*dns.Msg, error) {
	defer req.Body.Close()
	return toMsg(req.Body)
}

// requestToMsgGet extract the dns message from the GET request.
func requestToMsgGet(req *http.Request) (*dns.Msg, error) {
	values := req.URL.Query()
	b64, ok := values["dns"]
	if !ok {
		return nil, fmt.Errorf("no 'dns' query parameter found")
	}
	if len(b64) != 1 {
		return nil, fmt.Errorf("multiple 'dns' query values found")
	}
	return base64ToMsg(b64[0])
}

func toMsg(r io.ReadCloser) (*dns.Msg, error) {
	buf, err := io.ReadAll(http.MaxBytesReader(nil, r, 65536))
	if err != nil {
		return nil, err
	}
	m := new(dns.Msg)
	err = m.Unpack(buf)
	return m, err
}

func base64ToMsg(b64 string) (*dns.Msg, error) {
	buf, err := b64Enc.DecodeString(b64)
	if err != nil {
		return nil, err
	}

	m := new(dns.Msg)
	err = m.Unpack(buf)

	return m, err
}

var b64Enc = base64.RawURLEncoding

```

输出结果如下:

```go
获取到ip地址: 127.0.0.1
```



## 总结

coredns还是很棒的, 因为是GO写的所以可以交叉编译各个平台的可执行文件，这样部署很方便，又因为coredns是一个发展不错的项目，所以资源和插件都很丰富，又因为借鉴了caddy的插件体系，所以扩展起来很方便。

GitHub地址参考: https://github.com/youerning/blog/tree/master/coredns_code
