# APISIX源代码阅读

apisix主要是lua脚本跟openresty(或者说nginx)的组合,  流量具体转发由nginx承载, 但是按照什么规则转发用lua脚本定义. apisix在nginx之上封装了非常多功能强大有用的特性, 提供丰富的流量管理功能，比如态调整upstream, 灰度发布, 流量熔断, 认证, 观测性等。


代码可分为两个部分

- 启动前

  启动前主要是检查环境是否符合要求(比如openresty版本, luajit版本), 加载配置文件, 初始化数据中心, 渲染nginx.conf配置文件

- 启动后

  启动后主要是个组件的初始化(比如router, services, upstream等对象),  基于这些组件接受客户端的请求，这些请求可以大致可分为两种类型，一是配置路由, 服务, 上游等数据，即配置转发规则，二是基于已有的规则转发请求。

> 代码讲解大部分放在代码中的上下行

## 启动前

要启动apisix不能直接使用`openresty -p /path/to/prefix -c /path/to/conf`这样的命令，apisix为启动编写专门的启动脚本， 即`apisix start`, 启动前的所有操作全部已经涵盖在这个命令里了。



如果你不想直接启动，可以先初始化试试，又或者将启动命令分解成以下三步。



初始化配置文件。

```bash
/usr/bin/apisix init 
```

初始化etcd

```bash
/usr/bin/apisix init_etcd
```

启动openresty

```bash
/usr/local/openresty/bin/openresty -p /usr/local/apisix -g 'daemon off;'
```



### 启动脚本

apisix的启动脚本逻辑比较简单就是找到相应的lua解释器(lua或者luajit)然后调用`apisix.lua`。

源代码简化如下:

```bash
APISIX_LUA=/usr/local/apisix/apisix/cli/apisix.lua

# 寻找openresty, lua命令
OR_BIN=$(which openresty || exit 1)
OR_EXEC=${OR_BIN:-'/usr/local/openresty-debug/bin/openresty'}
OR_VER=$(openresty -v 2>&1 | awk -F '/' '{print $2}' | awk -F '.' '{print $1"."$2}')
LUA_VERSION=$(lua -v 2>&1| grep -E -o  "Lua [0-9]+.[0-9]+")

# 判断环境决定使用lua还是luajit。
if [[ -e $OR_EXEC && "$OR_VER" =~ "1.19" ]]; then
    # OpenResty version is 1.19, use luajit by default
    # find the luajit binary of openresty
    LUAJIT_BIN=$(${OR_EXEC} -V 2>&1 | grep prefix | grep -Eo 'prefix=(.*)/nginx\s+--' | grep -Eo '/.*/')luajit/bin/luajit

    # use the luajit of openresty
    echo "$LUAJIT_BIN $APISIX_LUA $*"
    exec $LUAJIT_BIN $APISIX_LUA $*
elif [[ "$LUA_VERSION" =~ "Lua 5.1" ]]; then
    # OpenResty version is not 1.19, use Lua 5.1 by default
    echo "lua $open $*"
    exec lua $APISIX_LUA $*
else
fi
```

其中openresty1.19版本以上默认使用luajit, 否则使用lua原生解释器，在找到lua解释器之后就执行apisix.lua脚本。



而apisix.lua代码如下

```lua
local pkg_cpath_org = package.cpath
local pkg_path_org = package.path

local apisix_home = "/usr/local/apisix"
-- 代码依赖的路径注入, 其中包括yaml, etcd, radixtree等依赖库
local pkg_cpath = apisix_home .. "/deps/lib64/lua/5.1/?.so;"
                  .. apisix_home .. "/deps/lib/lua/5.1/?.so;"
local pkg_path = apisix_home .. "/deps/share/lua/5.1/?.lua;"
package.cpath = pkg_cpath .. pkg_cpath_org
package.path  = pkg_path .. pkg_path_org


local env = require("apisix.cli.env")(apisix_home, pkg_cpath_org, pkg_path_org)
-- 获取apisix家目录, 当前目录是否是root目录, openresty启动参数, 依赖库路径, 最小etcd版本, ulimit参数(ulimit -n返回值)
local ops = require("apisix.cli.ops")

-- 启动入口
ops.execute(env, arg)
```

这部分代码主要是获取一些基本的信息, apisix家目录, 当前目录是否是root目录, openresty启动参数, 依赖库路径, 最小etcd版本, ulimit参数(ulimit -n返回值)等数据。



通过这些参数就可以进入启动流程了。

ops.lua的源代码如下:

```lua
-- apisix支持的命令行
local action = {
    help = help,
    version = version,
    init = init,
    init_etcd = etcd.init,
    start = start,
    stop = stop,
    quit = quit,
    restart = restart,
    reload = reload,
    test = test,
}

-- 通过table找到对应的命令, start自然对应的是start
function _M.execute(env, arg)
    local cmd_action = arg[1]
    action[cmd_action](env, arg[2])
end


local function start(env, ...)
    -- 因为apisix的工作进程以nobody权限启动，所以不能访问/root目录, 所以禁止在/root目录启动
    if env.is_root_path then
        util.die("Error: It is forbidden to run APISIX in the /root directory.\n")
    end

    -- 创建日志目录
    local cmd_logs = "mkdir -p " .. env.apisix_home .. "/logs"
    util.execute_cmd(cmd_logs)

    -- 检查是否正在运行
    local pid_path = env.apisix_home .. "/logs/nginx.pid"
    local pid = util.read_file(pid_path)
    pid = tonumber(pid)
    if pid then
        local lsof_cmd = "lsof -p " .. pid
        local res, err = util.execute_cmd(lsof_cmd)
        if not (res and res == "") then
            if not res then
                print(err)
            else
                print("APISIX is running...")
            end

            return
        end
    end

    -- 初始化环境
    -- 检查端口是否可用，配置文件参数是否合法，生成nginx.conf文件等
    init(env)
    -- 检测与etcd的连通性以及根据创建必要的key
    init_etcd(env, args)
    
    -- 最终执行/usr/local/openresty/bin/openresty -p /usr/local/apisix -g 'daemon off;'
    util.execute_cmd(env.openresty_args)
end

```

ops.execute调用链如下: 

ops.execute ->  ops.start -> ops.init -> ops.init_etcd -> util.execute_cmd。

其中execute_cmd的函数功能比较简单，就是指定对应的命令，如果有错误就读取错误输出并返回

```lua
local function execute_cmd(cmd)
    -- 调用命令
    local t, err = popen(cmd)
    if not t then
        return nil, "failed to execute command: "
                    .. cmd .. ", error info: " .. err
    end
    local data, err = t:read("*all")
    t:close()
    return data
end
```

启动前的逻辑并不是太复杂，代码之所多是因为做了很多的参数检查，环境检查，这是因为apisix功能丰富导致的必然结果，只要不深入各个函数，整体代码结构还是比较清晰。



在进入代码启动后的段落前得看看apisix渲染的nginx.confg配置文件是什么样的，它的模板文件在`apisix\cli\ngx_tpl.lua`



nginx.conf配置文件简化如下:

```nginx
http {
    
	# 各种数据容器初始化
    lua_shared_dict internal_status      10m;
	# ....

	# 负载均衡入口
    upstream apisix_backend {
        server 0.0.0.1;
        balancer_by_lua_block {
            # 负载均衡解析逻辑在这
            apisix.http_balancer_phase()
        }
    }

    # openresty master进程初始化
    init_by_lua_block {
        require "resty.core"
        apisix = require("apisix")

        local dns_resolver = { "127.0.0.11", }
        local args = {
            dns_resolver = dns_resolver,
        }
        # 主要初始化过程在这
        apisix.http_init(args)
    }
	
    # openresty worker进程时初始化
    init_worker_by_lua_block {
        # 初始化工作进程
        apisix.http_init_worker()
    }

    ## 默认http/https监听端口
    server {
        listen 9080 default_server reuseport;
        listen 9443 ssl default_server http2 reuseport;
        
        server_name _;
		# 管理接口，用于路由等对象的增删改查
        location /apisix/admin {
                allow 0.0.0.0/0;
                deny all;
            content_by_lua_block {
                apisix.http_admin()
            }
        }
		
        # ssl握手也有lua脚本处理
        ssl_certificate_by_lua_block {
            apisix.http_ssl_phase()
        }

        location / {
            # 在balancer_by_lua_block之前调用
            access_by_lua_block {
                apisix.http_access_phase()
            }

            # 流量代理
            proxy_pass      $upstream_scheme://apisix_backend$upstream_uri;

            # 过滤http头信息
            header_filter_by_lua_block {
                apisix.http_header_filter_phase()
            }
			
            # 过滤http请求体信息
            body_filter_by_lua_block {
                apisix.http_body_filter_phase()
            }
			# 日志收尾阶段
            log_by_lua_block {
                apisix.http_log_phase()
            }
        }
    }
}
```

如果想搞清整个流量的转发流程就得看看下面这张图

![1661911163550](img/nginx_phase.png)

根据上图，可以知道openresty启动是会调用`init_by_lua_block`和`init_worker_by_lua_block`对应的lua代码。



而http流量跟https流量的主要区别在于是否要处理ssl证书，所以http请求的流量流向如下:

```shell
access_by_lua_block -> balancer_by_lua_block -> header_filter_by_lua_block -> body_filter_by_lua_block -> log_by_lua_block
```

而https的流量的不同在于多了ssl证书的处理，流量流向如下:

```shell
ssl_certificate_by_lua_block -> access_by_lua_block -> balancer_by_lua_block -> header_filter_by_lua_block -> body_filter_by_lua_block -> log_by_lua_block
```



### 小结

apisix的启动流程不是很复杂，但是代码不少，这是因为apisix的配置项非常多，所以参数校验占了很大的一部分，所以在阅读代码时不要过于纠结各个参数的细节，即使有些参数看懂也没关系，当大体流程搞懂之后就可以深入细节，看看细节部分的具体实现。





## 启动后

openresty启动后就开始根据nginx.conf配置文件加载相应的lua代码。



根据配置文件不难知道初始化由下面两个部分配置组成。

```nginx
init_by_lua_block {
    require "resty.core"
    apisix = require("apisix")

    local dns_resolver = { "127.0.0.1"}
    local args = {
        dns_resolver = dns_resolver,
    }
    apisix.http_init(args)
}

init_worker_by_lua_block {
    apisix.http_init_worker()
}
```



### 初始化

初始化主要分为两个部分，一是master进程的初始化，二是worker进程的初始化。



#### master进程初始化

`apisix.http_init(args)`的代码在`apisix\init.lua`

```lua
function _M.http_init(args)
    -- 设置dns服务器
    core.resolver.int_resolver(args)
    -- 设置实例id
    core.id.init()

	-- 启用特权进程
    local process = require("ngx.process")
    local ok, err = process.enable_privileged_agent()
    if not ok then
        core.log.error("failed to enable privileged_agent: ", err)
    end

    -- 检查配置中心是否可以正常工作, 默认是etcd
    if core.config.init then
        local ok, err = core.config.init()
        if not ok then
            core.log.error("failed to load the configuration: ", err)
        end
    end
end
```

这部分的初始化并不复杂。

其中特权进程是为了后续代码中判断是否在进程的类型，master或worker。



#### worker进程初始化

apisix的所有对象的初始化都在这一部分，初始化的对象非常多，本文主要聚焦在路由，负载均衡等部分的初始化，其他如services, upstream等暂不涉及。

代码简化如下:

```lua
function _M.http_init_worker()
    -- 啥都不做
    require("apisix.balancer").init_worker()
    load_balancer = require("apisix.balancer")
    -- 初始化管理接口的路由及响应函数
    require("apisix.admin.init").init_worker()
    -- 创建http,ssl路由对象，用来路由客户端请求，路由规则来源于上面的管理接口
    router.http_init_worker()
end
```

`loadbalancer`对象在后面章节再介绍，这里暂时略过，这里着重看路由对象的初始化过程。



##### 管理接口路由

`require("apisix.admin.init").init_worker()`的代码简化如下:

```lua
local resources = {
    -- 几乎每个对象都实现了"GET", "PUT", "POST", "DELETE", "PATCH"五个方法
    routes          = require("apisix.admin.routes"),
}

local function run()
    local api_ctx = {}
    core.ctx.set_vars_meta(api_ctx)
    ngx.ctx.api_ctx = api_ctx

    local uri_segs = core.utils.split_uri(ngx.var.uri)
    -- /apisix/admin/routes分割后如下
    -- {"", "apisix", "admin", "route"}
    local seg_res, seg_id = uri_segs[4], uri_segs[5]
    local seg_sub_path = core.table.concat(uri_segs, "/", 6)
	-- 找到对应的资源对象
    local resource = resources[seg_res]
    local method = str_lower(get_method())
	-- 获取请求体, 如果有数据就JSON反序列化
    local req_body, err = core.request.get_body(MAX_REQ_BODY)
    if req_body then
        local data, err = core.json.decode(req_body)
        req_body = data
    end

    -- 直接调用对应的响应函数然后返回
    local code, data = resource[method](seg_id, req_body, seg_sub_path,
                                        uri_args)
    if code then
        data = strip_etcd_resp(data)
        core.response.exit(code, data)
    end
end

-- 路由列表
local uri_route = {
    {
        paths = [[/apisix/admin/*]],
        methods = {"GET", "PUT", "POST", "DELETE", "PATCH"},
        handler = run,
    },
}

function _M.init_worker()
    router = route.new(uri_route)
end
```

> 注意lua的table对象的索引从1开始。

这里以官方的请求为例

```shell
curl "http://127.0.0.1:9080/apisix/admin/routes/1" -H "X-API-KEY: edd1c9f034335f136f87ad84b625c8f1" -X PUT -d '
{
  "methods": ["GET"],
  "host": "example.com",
  "uri": "/anything/*",
  "upstream": {
    "type": "roundrobin",
    "nodes": {
      "httpbin.org:80": 1
    }
  }
}'
```

所以对应的响应函数是`require("apisix.admin.routes")["PUT"]`

代码如下:

```lua
function _M.put(id, conf, sub_path, args)
    -- conf就是请求体的json对象
    -- 这里主要检查关联的plugins, upstream, services等对象是否存在, 如果关联了的话
    local id, err = check_conf(id, conf, true)

    -- 如果路由id已对应一个路由对象，那么在当前的配置文件中注入必要的配置信息，比如时间戳
    local key = "/routes/" .. id
    local ok, err = utils.inject_conf_with_prev_conf("route", key, conf)
	-- 将数据持久化到etcd
    local res, err = core.etcd.set(key, conf, args.ttl)
    return res.status, res.body
end
```

路由的创建还是比较简单的，主要流程就是检查配置文件是否合法，然后注入已存在的路由信息(如果存在的话)，然后就是保存数据到etcd。



至此，我们可以通过管理接口增删改查路由对象以控制流量转发规则。



##### 数据转发路由

`router.http_init_worker()`的代码简化如下:

```lua
-- 检查router对象是否有满足必要的接口
-- routes方法返回路由列表
-- init_worker用于初始化路由
local function attach_http_router_common_methods(http_router)
    if http_router.routes == nil then
        http_router.routes = function ()
            if not http_router.user_routes then
                return nil, nil
            end

            local user_routes = http_router.user_routes
            return user_routes.values, user_routes.conf_version
        end
    end

    if http_router.init_worker == nil then
        http_router.init_worker = function (filter)
            -- http的路由对象就是在这里初始化
            http_router.user_routes = http_route.init_worker(filter)
        end
    end
end

function _M.http_init_worker()
    -- 配置配置文件 config.yaml
    local conf = core.config.local_conf()
    local router_http_name = "radixtree_uri"
    local router_ssl_name = "radixtree_sni"

    -- 加载http(s)请求的路由并并初始化
    local router_http = require("apisix.http.router." .. router_http_name)
    attach_http_router_common_methods(router_http)
    router_http.init_worker(filter)
    _M.router_http = router_http

    local router_ssl = require("apisix.ssl.router." .. router_ssl_name)
    router_ssl.init_worker()
    _M.router_ssl = router_ssl
	-- 没太看懂这个router用来干啥的
    _M.api = require("apisix.api_router")
end
```

这一部分就是创建router对象用于后续的流量转发，首先看看router_http, 根据上面的代码可以知道init_worker就是http_route.init_worker.

```lua
-- apisix\http\route.lua
function _M.init_worker(filter)
    local user_routes, err = core.config.new("/routes", {
            automatic = true,
            item_schema = core.schema.route,
            checker = check_route,
            filter = filter,
        })
    if not user_routes then
        error("failed to create etcd instance for fetching /routes : " .. err)
    end

    return user_routes
end
```

http的init_worker的主要功能就是将一个映射etcd路由列表数据的对象(user_routes)暴露出来，这个对象会不断的同步ectd的数据(/apisix/routes/*)到这个对象，这样，通过管理接口对路由的增删改查就能保持路由的动态更新，其他诸如services, upstream大体一直。

`core.config.new("/routes"`的代码在apisix\core\config_etcd.lua

代码如下:

```lua
local function sync_data(self)
   -- 这函数超级长, 大体逻辑就是将数据合并到self里面去
end

local function _automatic_fetch(premature, self)
    local i = 0
    -- 一个用于同步的循环, 默认每个循环最多32次，
    while not exiting() and self.running and i <= 32 do
        i = i + 1

        local ok, err = xpcall(function()
            if not self.etcd_cli then
                local etcd_cli, err = get_etcd()
                self.etcd_cli = etcd_cli
            end

            local ok, err = sync_data(self)
	-- 如果没有结束就继续递归的调用，再次循环
    if not exiting() and self.running then
        ngx_timer_at(0, _automatic_fetch, self)
    end
end

function _M.new(key, opts)
    local local_conf, err = config_local.local_conf()
    local etcd_conf = local_conf.etcd
    -- 存在etcd中的键值前缀/apisix
    local prefix = etcd_conf.prefix
    -- 同步时间间隔，默认5s
    local resync_delay = etcd_conf.resync_delay
    if not resync_delay or resync_delay < 0 then
        resync_delay = 5
    end
    -- etcd健康检查超时时间
    local health_check_timeout = etcd_conf.health_check_timeout
    if not health_check_timeout or health_check_timeout < 0 then
        health_check_timeout = 10
    end
	
    -- lua的对象继承写法
    local obj = setmetatable({
        etcd_cli = nil,
        key = key and prefix .. key,
		-- 各种参数...
    }, mt)

    if automatic then
        -- 同步etcd数据到obj对象的逻辑在这启动
        ngx_timer_at(0, _automatic_fetch, obj)
    end

    -- 将obj对象的应用放在本模块的created_obj对象中, 这样后续就可以获取已创建的obj对象了，
    if key then
        created_obj[key] = obj
    end

    return obj
end
```

至此路由规则的同步就完成了，apisix由此可以动态的增删改查路由规则。



#### 小结

初始化的过程会比较复杂，这主要是因为组件比较多，但是每个组件的初始化其实有迹可循，首先是初始化模块里的局部变量，然后创建一个可以不断同步etcd数据的对象，然后创建必要的对象用于后续处理请求。

其中同步的逻辑会稍微复杂一些，再就是路由的创建也多了好几层抽象，但是初始化过程中并没有马上创建可以分发流量的路由对象，这是因为路由对象是在匹配中创建的，但是，也是在数据有变动的情况下才会再次创建，这部分在后面会提到。



### 路由转发

这里再次回顾一下路由转发设计的lua代码

```shell
access_by_lua_block -> balancer_by_lua_block -> header_filter_by_lua_block -> body_filter_by_lua_block -> log_by_lua_block
```

access_by_lua_block的代码如下:

```lua
function _M.http_access_phase()
    local ngx_ctx = ngx.ctx

    -- always fetch table from the table pool, we don't need a reused api_ctx
    local api_ctx = core.tablepool.fetch("api_ctx", 0, 32)
    ngx_ctx.api_ctx = api_ctx

    core.ctx.set_vars_meta(api_ctx)
	-- 路由匹配
    router.router_http.match(api_ctx)
    local route = api_ctx.matched_route
    -- 略过插件过滤及关联服务查询等逻辑
    
    -- 这里主要是检查相关参数
    -- 设置检查上游状态的checker对象(用于检查后端状态)
    -- 以及设置schema
    local code, err = set_upstream(route, api_ctx)
    -- 选择一个后端
    local server, err = load_balancer.pick_server(route, api_ctx)
	-- 后续的流量就会转发到这个选择的picked_server
    api_ctx.picked_server = server
	-- 设置必要的http 头信息
    set_upstream_headers(api_ctx, server)
end
```

这段代码的主要重点在于路由匹配及后端选取。

首先看看路由匹配，代码如下:

```lua
-- apisix\http\router\radixtree_uri.lua    
	local uri_routes = {}
    local uri_router
    local match_opts = {}
function _M.match(api_ctx)
    local user_routes = _M.user_routes
    local _, service_version = get_services()
    -- 判断是否需要重新创建路由对象
    if not cached_router_version or cached_router_version ~= user_routes.conf_version
        or not cached_service_version or cached_service_version ~= service_version
    then
        uri_router = base_router.create_radixtree_uri_router(user_routes.values,
                                                             uri_routes, false)
        cached_router_version = user_routes.conf_version
        cached_service_version = service_version
    end

    return base_router.match_uri(uri_router, match_opts, api_ctx)
end
```

router_http的匹配方法业务逻辑不多，重头戏放在了上一层目录的route.lua, 核心逻辑在base_router.

代码简化如下:

```lua
function _M.create_radixtree_uri_router(routes, uri_routes, with_parameter)
    routes = routes or {}

    core.table.clear(uri_routes)

    for _, route in ipairs(routes) do
        if type(route) == "table" then
            local status = core.table.try_read_attr(route, "value", "status")
            -- check the status
            if status and status == 0 then
                -- 用于lua没有continue关键字只能用这种蹩脚的方式。。。。。
                goto CONTINUE
            end

            local filter_fun, err

            local hosts = route.value.hosts or route.value.host
			-- 这段代码的核心逻辑就是基于route创建符合radixtree接口的对象
            core.table.insert(uri_routes, {
                paths = route.value.uris or route.value.uri,
                methods = route.value.methods,
                priority = route.value.priority,
                hosts = hosts,
                remote_addrs = route.value.remote_addrs
                               or route.value.remote_addr,
                vars = route.value.vars,
                filter_fun = filter_fun,
                -- 当底层对象匹配成功后就会调用这个函数
                -- 这个函数的功能就是设置匹配的路由
                handler = function (api_ctx, match_opts)
                    api_ctx.matched_params = nil
                    api_ctx.matched_route = route
                    api_ctx.curr_req_matched = match_opts.matched
                end
            })

            ::CONTINUE::
        end
    end

    if with_parameter then
        return radixtree.new(uri_routes)
    else
        -- 最终也是调用的resty.radixtree
        return router.new(uri_routes)
    end
end
```

但是最终干活的路由对象是radixtree模块,  关于它的接口可以查看: https://github.com/api7/lua-resty-radixtree

从这一段代码可知，路由在匹配成功之后就会设置matched_route对象，这样后续的流程可以继续，也基于此可以选择对应的后端。

然后再来看看`load_balancer.pick_server(route, api_ctx)`的代码

```lua
-- apisix\balancer.lua
local function pick_server(route, ctx)
    local up_conf = ctx.upstream_conf

    local nodes_count = #up_conf.nodes
    -- 如果只有一个后端，就直接返回了
    if nodes_count == 1 then
        local node = up_conf.nodes[1]
        ctx.balancer_ip = node.host
        ctx.balancer_port = node.port
        return node
    end

    local version = ctx.upstream_version
    local key = ctx.upstream_key
    local checker = ctx.up_checker

    ctx.balancer_try_count = (ctx.balancer_try_count or 0) + 1

    -- 由于可能出现重试的情况，所以整个请求中使用同一个picker, 所以这里做了缓存
    local server_picker = ctx.server_picker
    if not server_picker then
        -- 这里的create_server_picker相当于一个创建工厂函数
        server_picker = lrucache_server_picker(key, version,
                                               create_server_picker, up_conf, checker)
    end

    -- 默认使用的picker是
    local server, err = server_picker.get(ctx)
    ctx.balancer_server = server
	-- 如果是域名就将其解析成ip
    local domain = server_picker.addr_to_domain[server]
    local res, err = lrucache_addr(server, nil, parse_addr, server)

    res.domain = domain
    ctx.balancer_ip = res.host
    ctx.balancer_port = res.port
    ctx.server_picker = server_picker

    return res
end


local function create_server_picker(upstream, checker)
    local picker = pickers[upstream.type]
    if not picker then
        -- 默认是apisix.balancer.roundrobin
        pickers[upstream.type] = require("apisix.balancer." .. upstream.type)
        picker = pickers[upstream.type]
    end

    if picker then
        local nodes = upstream.nodes
        local addr_to_domain = {}
        for _, node in ipairs(nodes) do
            if node.domain then
                local addr = node.host .. ":" .. node.port
                addr_to_domain[addr] = node.domain
            end
        end
		-- 获取健康的后端并创建picker对象
        local up_nodes = fetch_health_nodes(upstream, checker)
        local server_picker = picker.new(up_nodes[up_nodes._priority_index[1]], upstream)
        server_picker.addr_to_domain = addr_to_domain
        return server_picker
    end

    return nil, "invalid balancer type: " .. upstream.type, 0
end

```

picker对象的接口基本上差不多，实现了get方法，会基于创建时传入的后端列表选择一个后端返回，这里就不继续深入了。

当选择到了后端之后`access_by_lua_block`这阶段就完成了，流量继续往下就是`balancer_by_lua_block`阶段。

代码简化如下:

```lua
-- apisix\init.lua
function _M.http_balancer_phase()
    local api_ctx = ngx.ctx.api_ctx
    if not api_ctx then
        core.log.error("invalid api_ctx")
        return core.response.exit(500)
    end

    load_balancer.run(api_ctx.matched_route, api_ctx, common_phase)
end

-- apisix\balancer.lua
function _M.run(route, ctx, plugin_funcs)
    local server, err

    if ctx.picked_server then
        -- use the server picked in the access phase
        server = ctx.picked_server
        ctx.picked_server = nil
		-- 设置必要的参数，超时时间，重试次数等。
        set_balancer_opts(route, ctx)

    else
        -- 其他逻辑
    end
	-- 开始转发流量
    local ok, err = set_current_peer(server, ctx)

    ctx.proxy_passed = true
end
```

至此apisix的路由转发功能大致完成，而后续的各种过滤操作，这里就不看了。



### SSL证书匹配

ssl的相关操作在`ssl_certificate_by_lua_block`阶段对应的代码是`http_ssl_phase`。

再次之前先看看ssl路由的创建和初始化

```lua
function _M.init_worker()
    local err
    ssl_certificates, err = core.config.new("/ssl", {
        automatic = true,
        item_schema = core.schema.ssl,
        checker = function (item, schema_type)
            return apisix_ssl.check_ssl_conf(true, item)
        end,
        filter = ssl_filter,
    })
end
```

可以看到ssl初始逻辑和router_http差不多，也是创建一个对象用于同步etcd的数据。



然后继续看`http_ssl_phase`的代码

```lua
function _M.http_ssl_phase()
    local ngx_ctx = ngx.ctx
    local api_ctx = ngx_ctx.api_ctx
    local ok, err = router.router_ssl.match_and_set(api_ctx)
end


-- apisix\ssl\router\radixtree_sni.lua
function _M.match_and_set(api_ctx)
    local err
    -- 然后创建一个radixtree的路由对象
    if not radixtree_router or
       radixtree_router_ver ~= ssl_certificates.conf_version then
        radixtree_router, err = create_router(ssl_certificates.values)
        if not radixtree_router then
            return false, "failed to create radixtree router: " .. err
        end
        radixtree_router_ver = ssl_certificates.conf_version
    end

    local sni
    -- 获取客户端请求的域名用作路由匹配
    sni, err = apisix_ssl.server_name()
    if type(sni) ~= "string" then
        local advise = "please check if the client requests via IP or uses an outdated protocol" ..
                       ". If you need to report an issue, " ..
                       "provide a packet capture file of the TLS handshake."
        return false, "failed to find SNI: " .. (err or advise)
    end

    core.log.debug("sni: ", sni)

    local sni_rev = sni:reverse()
    -- 
    local ok = radixtree_router:dispatch(sni_rev, nil, api_ctx)

    if type(api_ctx.matched_sni) == "table" then
        local matched = false
        for _, msni in ipairs(api_ctx.matched_sni) do
            if sni_rev == msni or not str_find(sni_rev, ".", #msni) then
                matched = true
            end
        end
    end

    local matched_ssl = api_ctx.matched_ssl

    ngx_ssl.clear_certs()
    -- 基于匹配的ssl证书信息，设置服务端的ssl证书
    ok, err = set_pem_ssl_key(sni, matched_ssl.value.cert,
                              matched_ssl.value.key)
    return true
end

local function create_router(ssl_items)
    local ssl_items = ssl_items or {}

    local route_items = core.table.new(#ssl_items, 0)
    local idx = 0

    for _, ssl in config_util.iterate_values(ssl_items) do
        if ssl.value ~= nil and
            (ssl.value.status == nil or ssl.value.status == 1) then  -- compatible with old version

            local j = 0
            local sni
            if type(ssl.value.snis) == "table" and #ssl.value.snis > 0 then
                sni = core.table.new(0, #ssl.value.snis)
                for _, s in ipairs(ssl.value.snis) do
                    j = j + 1
                    sni[j] = s:reverse()
                end
            else
                sni = ssl.value.sni:reverse()
            end

            idx = idx + 1
            route_items[idx] = {
                paths = sni,
                -- 跟http路由差不多，也是基于ssl列表的数据创建一个handler函数用于设置匹配的ssl
                handler = function (api_ctx)
                    if not api_ctx then
                        return
                    end
                    api_ctx.matched_ssl = ssl
                    api_ctx.matched_sni = sni
                end
            }
        end
    end
    local router, err = router_new(route_items)

    return router
end
```

ssl证书的路由匹配其实和http路由差不多，不同之处在于处理的逻辑不一样，但是流程大致是一致的，首先创建一个可以与etcd同步的数据对象，时刻保持同步，然后基于已有的数据创建路由并创建对应的handler函数。



## 总结

apisix的核心逻辑不是太复杂，但是因为功能比较多，所以代码中有很多的验证逻辑，如果略过会拖慢阅读速度。



以后有空写一个简单的apisix原型^_^.

