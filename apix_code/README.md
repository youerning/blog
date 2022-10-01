# 500行以内写一个API网关
本文实现的apix网关代码结构基本上是借鉴了APISIX的源代码, 可以看做APISIX的一个极度缩减版本。本文的实现只依赖openresty镜像已有的库，不依赖额外的库，所以路由的实现非常简陋，也没有实现路由的持久化，但是大致实现了动态路由更新和转发, 插件机制。

> 如果你认真计算代码行数之后会发现代码行数超过了500行, 但是笔者认为去掉注释，以及将一些代码压缩之后是可以降到500行以内的, 之所以取这个标题是为了想《500 lines or less》这本书至今

由于之前写了APISIX的源代码阅读的文章，所以这篇文章不会写的太细，只是着重讲解一些实现的细节，而流量的各个阶段如何流转这里就不再赘述了, 对本文有疑问就直接看源代码吧, 代码量不多。

## 测试一下
在进入代码之前可以先测试一下这个实现的功能

通过以下代码运行
```shell
docker run -it --rm -v /root/apix_code/src/apix/:/usr/local/openresty/lualib/apix -v /root/apix_code/src/nginx.conf:/usr/local/openresty/nginx/conf/nginx.conf  -p 8000:80 -p 81:81 -p 82:82 openresty/openresty:1.21.4.1-3-alpine-fat openresty -g "daemon off;"
```
> 本文的源代码会在文末贴出

> 注意`/root/apix_code/`这个位置具体根据自己的路径配置


运行起来后openresty会监听三个端口, 8000, 81, 82。
8000端口包含管理接口, 网关入口
81, 82使用测试的后端。

可以通过以下命令简单测试一下后端
```
curl 127.0.0.1:81/ping
# 响应结果: 
test web1: /ping

curl 127.0.0.1:82/ping
# 响应结果: 
test web2: /ping
```


### 负载均衡
通过一下命令查看当前路由列表
```shell
curl 127.0.0.1:8000/apix/admin/routes|python -m json.tool
```

**响应结果:**
```json
[
    {
        "host": "test.com",
        "id": 1,
        "methods": [
            "GET",
            "POST"
        ],
        "update_time": 1663833578,
        "upstream": {
            "nodes": {
                "127.0.0.1:81": 1,
                "127.0.0.1:82": 1
            }
        },
        "uri": "/*"
    },
    {
        "host": "test2.com",
        "id": 2,
        "methods": [
            "GET",
            "POST"
        ],
        "plugins": {
            "basic-auth": {
                "password": "test",
                "username": "test"
            },
            "echo": {
                "after_body": "\necho after here\n",
                "before_body": "echo before here\n"
            }
        },
        "update_time": 1663833578,
        "upstream": {
            "nodes": {
                "127.0.0.1:81": 1,
                "127.0.0.1:82": 1
            }
        },
        "uri": "/*"
    }
]
```


通过上面的路由知道test.com域名会轮训的转发到127.0.0.1:81, 127.0.0.1:82, 而域名test2.com在转发的基础上还会执行两个插件(echo, basic-auth, 这两个插件就是直接从APISIX代码中复制出来的.)。
可以通过以下命令验证

**验证路由1:**
```shell
curl -H "Host: test.com" 127.0.0.1:8000/ping
curl -H "Host: test.com" 127.0.0.1:8000/ping
```
**响应结果:**
```
test web1: /ping
test web2: /ping
```
可以看到两次结果发生了变化, 第一次转发到了81, 第二次转发到了82


**验证路由2:**
```shell
curl -H "Host: test2.com" 127.0.0.1:8000/ping
```

**响应结果:**
```
echo before here
{"message":"Missing authorization in request"}
echo after here
```
因为路由2配置两个插件, 其中一个插件是basic-auth的验证插件, 所以结果中会提示缺失了验证, 而响应中的`echo before here`和`echo aftre here`内容是有echo插件导致的。

下面在使用用户名密码测试一下
```shell
curl -H "Host: test2.com" http://test:test@127.0.0.1:8000/ping
```

**响应结果:**
```
echo before here
test web1: /ping

echo after here
```
然后发现响应内容正常了, 


### 动态路由
管理接口在/apix/admin/routes

#### 获取当前路由列表
前面已经测试过了, 这里就不赘述了.

#### 删除指定路由
```
curl -X DELETE 127.0.0.1:8000/apix/admin/routes/1
```
**响应结果:**
```json
{"msg":"删除成功"}
```
然后再获取路由列表会发现第一条路由记录没了。


#### 更新指定路由
```shell
curl -X PUT 127.0.0.1:8000/apix/admin/routes/1 -d '{
    "host": "test2.com",
    "id": 2,
    "methods": [
        "GET",
        "POST"
    ],
    "update_time": 1663833578,
    "upstream": {
        "nodes": [
            {
                "host": "127.0.0.1",
                "port": "81",
                "weight": 1
            },
            {
                "host": "127.0.0.1",
                "port": "82",
                "weight": 1
            }
        ]
    },
    "uri": "/*"
}
'
```
**响应结果:**
```json
{"msg":"更新成功"}
```
> 注意这里的url是127.0.0.1:8000/apix/admin/routes/**1**, 这是因为路由列表只有一条了，而lua的索引是有1开始的, 通过查看路由列表，可以发现只剩一条记录了。


#### 新增路由
新增路由跟更新路由差不多，只需将方法`PUT`改成`POST`即可, 这里也不赘述了。


## 代码结构
因为本身就是借鉴的APISIX, 所以代码结构和nginx的配置内容和APISIX差不多, nginx配置文件如下:
```nginx.conf

http {
    lua_shared_dict routes 10m;

    # 配置一个由lua代码处理负载均衡的配置, 当流量到balance阶段就会调用apix.http_balancer_phase()
    upstream apix_backend {
        server 0.0.0.1;

        balancer_by_lua_block {
            apix.http_balancer_phase()

        }
    }

    # master进程初始化时调用, 可以在这里引用后续配置需要引用的库
    init_by_lua_block {
        require("resty.core")
        -- 后面的代码, 直接可以调用这里导入的apix
        apix = require("apix")
        apix.http_init()
    }

    # worker进程初始化时调用
    init_worker_by_lua_block {
        apix.http_init_worker()
    }

    # worker进程退出时调用, reload的时候也是
    exit_worker_by_lua_block {
        apix.http_exit_worker()
    }

    server {
        listen       80;
        server_name  localhost;

        location / {
            
            # 流量入口处理函数
            access_by_lua_block {
                apix.http_access_phase()
            }

            proxy_pass      $upstream_scheme://apix_backend$upstream_uri;

            # nginx的其他阶段可被注入的钩子函数
            header_filter_by_lua_block {
                apix.http_header_filter_phase()
            }

            body_filter_by_lua_block {
                apix.http_body_filter_phase()
            }

            log_by_lua_block {
                apix.http_log_phase()
            }
        }

        # 管理接口的定义
        location /apix/admin {
            allow 127.0.0.0/24;
            allow 172.17.0.0/16;
            deny all;

            content_by_lua_block {
                apix.http_admin()
            }
        }
    }

    # 用于测试的两个后端, 简单的返回请求的uri即可
    server {
        listen       81;
        server_name  localhost;

        location / {
            access_by_lua_block {
                ngx.say("test web1: " .. ngx.var.uri)
            }
        }
    }

    server {
        listen       82;
        server_name  localhost;

        location / {
            access_by_lua_block {
                ngx.say("test web2: " .. ngx.var.uri)
            }
        }
    }
}

```
> 内容有被简化, 完整内容参考源代码.



代码结构如下:
```shell
src
|-- apix
|   |-- admin.lua
|   |-- balancer.lua
|   |-- config.lua
|   |-- http_router.lua
|   |-- init.lua
|   |-- plugin.lua
|   |-- plugins
|   |   |-- basic-auth.lua
|   |   `-- echo.lua
|   `-- router.lua
`-- nginx.conf
```

### 小结
无论是代码结构还是nginx的配置内容都是借鉴的APISIX.


## 管理接口
一个网关自然需要一个管理接口用于配置路由的增删改查, 而这里的实现会比较简单。代码如下:
```lua

local json = require("cjson")
local ngx = ngx
local ngx_re = require("ngx.re")
local ngx_var = ngx.var
local ngx_exit = ngx.exit
local get_method = ngx.req.get_method
local str_lower = string.lower
local str_upper = string.upper
local ngx_print = ngx.print
local ngx_read_body = ngx.req.read_body
local ngx_get_body_data = ngx.req.get_body_data
local ngx_time = ngx.time

local base_router = require("apix.router")
local shared_routes = ngx.shared["routes"]

local router
local cached_routes
local need_get_again = true
local shared_routes_key = "routes"
local _M = {shared_routes_key = shared_routes_key}

-- 路由列表
local admin_routes = {
    {
        methods = {"GET", "POST", "DELETE", "PUT"},
        uri = "/apix/admin/routes*",
    }
}

-- 在路由中注入一个时间用于对比路由是否更新
local function inject_time(route, force)
    if force then
        route.update_time = ngx_time()
        return
    end
    if not route.update_time then
        route.update_time = ngx_time()
    end
end

local function get_routes()
    if need_get_again then
        cached_routes = json.decode(shared_routes:get(shared_routes_key))    
        need_get_again = false
        return cached_routes
    end 
    return cached_routes
end

local function set_routes(routes)
    need_get_again = true
    shared_routes:set(shared_routes_key, json.encode(routes))
end

_M.get_routes = get_routes
_M.set_routes = set_routes

-- 一个工具函数, 用于响应结果
local function resp_exit(code, data)
    ngx.status = code
    if type(data) == "table" then
        ngx_print(json.encode(data))
    else
        ngx_print(data)
    end
    
    ngx_exit(code)
end

_M.resp_exit = resp_exit


local function handler()
    local method = get_method()
    local uri = ngx_var.uri
    local route_id = tonumber(ngx_re.split(uri, "/")[5])
    -- ngx.log(ngx.ERR, "method: ", method, " uri: ", uri, " route-id: ", route_id)
    if method == "GET" and uri == "/apix/admin/routes" then
        return resp_exit(200, get_routes())
    end
    if method == "POST" and uri == "/apix/admin/routes" then
        ngx_read_body()
        local req_body = ngx_get_body_data()
        local route = json.decode(req_body)
        inject_time(route)
        local routes = get_routes()
        table.insert(routes, route)
        set_routes(routes)
        return resp_exit(200, {msg = "新增成功"})
    end
    if method == "DELETE" then
        local routes = get_routes()
        if not route_id or route_id > #routes then
            return resp_exit(ngx.HTTP_BAD_REQUEST, {error = "非法的route id: " .. route_id})
        end
        local new_routes = {}
        for i, route in ipairs(routes) do
            if i ~= route_id then
                table.insert(new_routes, route)
            end
        end
        set_routes(new_routes)
        return resp_exit(200, {msg = "删除成功"})
    end

    if method == "PUT" then
        local routes = get_routes()
        if not route_id or route_id > #routes then
            return resp_exit(ngx.HTTP_BAD_REQUEST, {error = "非法的route id: " .. route_id})
        end
        ngx_read_body()
        local req_body = ngx_get_body_data()
        local route = json.decode(req_body)
        inject_time(route)
        routes[route_id] = route
        set_routes(routes)
        return resp_exit(200, {msg = "更新成功"})
    end
    return resp_exit(404, {error = "管理接口没有匹配的路由"})
end


local function new_admin_router(routes)
    -- ngx.log(ngx.ERR, "init admin routes: ", json.encode(routes))
    for _, route in ipairs(routes) do
        route.handler = handler
    end

    return base_router.new(routes)
end

function _M.http_init_worker()
    router = new_admin_router(admin_routes)
end

function _M.get()
    return router
end


return _M
```
可以看到管理接口的实现并不复杂, 通过判断请求方法和uri做对应的逻辑即可, 而路由列表的操作比较简单粗暴, 首先从`shared.DICT`中读取最新的路由列表, GET就是直接返回，POST就是在列表中增加一个路由, 然后保存到`shared.DICT`, PUT跟POST差不多, 不同在于，后者所以到对应的route然后更新, 最后保存, DELETE就是删除对应的索引到的值, 然后保存。

### 小结
一个网关自然需要一个管理接口, 通过这个接口可以增删查改路由列表, 这样就是动态的配置路由，多棒。那么管理接口的路由怎么驱动内存中的路由对象变化呢? 请看下一节。


## 动态路由
动态路由的核心逻辑在于构造一个路由对象, 这跟web框架差不多, 但是在openresty(或者说nginx+lua)的实现有些点需要注意, 因为nginx是master-worker的工作模型, 所以每个worker教程会有独立的内存空间, 换句话说, 如果每个worker教程初始化一个router对象, 那么每个worker教程会有一个独立的router, 所以不能将数据保存在worke进程的内存中, 而需要借助独立于worker进程外的数据.  

为了实现简单, 本文是将路由列表的数据放在了nginx的`shared.DICT`里面, 而APISIX的实现是将数据存储在etcd里面, 并且通过watch方法监听数据的变化, 可以近实时的让路由对象动态变更, 所见即所得。

首先在nginx.conf里面配置一个对应的`shared.DICT`对象
```nginx
http{
    lua_shared_dict routes 10m;
}
```

然后就可以在lua代码中使用了
```lua
local shared_routes = ngx.shared["routes"]
shared_routes:get("routes")
shared_routes:set("routes", "{}")
```


### 路由的实现
路由实现比较简陋, 只有一个dispatch方法用来匹配路由.

```lua
local json = require("cjson")
local ngx_re = ngx.re
local ipairs = ipairs

local _M = {}
local mt = {__index = _M}

-- routes对象就是一个由json解码后的table对象, 一个数组
function _M.new(routes)
    -- ngx.log(ngx.ERR, "new router with routes: ", #routes)
    return setmetatable({routes=routes}, mt)
end


local function array_contains(arr, key)
    for _, m in ipairs(arr) do
        if m == key then
            -- ngx.log(ngx.ERR, "method matched")
            return true
        end
    end
    return false
end


local function uri_match(pattern, uri)
    local m, err = ngx_re.match(uri, pattern)
    if m then
        -- ngx.log(ngx.ERR, "uri matched")
        return true
    end
    return false
end


function _M.dispatch(self, uri, match_opts, ...)
    -- ngx.log(ngx.ERR, "dispatch uri: ", uri, " with opts: ", json.encode(match_opts), " routes number: ", #self.routes)
    for i, route in ipairs(self.routes) do
        -- ngx.log(ngx.ERR, "route uri: ", route.uri, " route host: ", route.host, " route methods: ", json.encode(route.methods))
        if not uri_match(route.uri, uri) or not array_contains(route.methods, match_opts.method) then
            goto CONTINUE
            -- ngx.log(ngx.ERR, "matched route: ", route.uri)
        end
        -- ngx.log(ngx.ERR, "route host: ", route.host, " match_opts: ", match_opts.host)
        if not route.host or route.host == match_opts.host then
            -- ngx.log(ngx.ERR, "开始派发请求")
            return route.handler(...)    
        end

        ::CONTINUE::
    end
end


return _M
```
通过代码可以知道, 匹配的逻辑就是通过正则表达式匹配uri, 以及匹配请求方法，以及一个可选的Host头信息。而APISIX的路由对象是由`resty.radixtree`模块实现的, 底层由c代码实现, 所以转发性能(这个转发性能值, 匹配的性能)会比较好, 而且支持的匹配条件要更多，还包括, args, headers, cookie, 客户端地址等。

可以看到匹配到之后就会调用路由的handler方法。

而handler方法是在创建路由的时候动态创建的，代码如下:
```lua
local function new_http_router(routes)
    for _, route in ipairs(routes) do
        -- 重点就是在api_ctx对象上绑定一个matched_route变量
        route.handler = function(api_ctx)
            api_ctx.matched_route = route
        end

        local new_nodes = {}
        -- 将对象的形式改成数组的形式
        -- 本代码中并没有用到weight字段
        for addr, weight in pairs(route.upstream.nodes) do
            addr = ngx_re.split(addr, ":")
            local host, port = addr[1], addr[2]
            local node = {
                host = host,
                port = port,
                weight = weight
            }
            table.insert(new_nodes, node)
        end
        route.upstream.nodes = new_nodes
    end
    return base_router.new(routes)
end
```
而匹配后的业务逻辑只需要判断是否存在`matched_route`字段即可, 如果没有这个字段就说明没有匹配的路由, 直接返回404即可。

请求时的主要逻辑
```lua
do 
function _M.http_access_phase()
    -- ngx.log(ngx.ERR, "开始access阶段")
    local api_ctx = {}
    ngx.ctx.api_ctx = api_ctx
    -- 注意这里调用的是match方法, 而不是路由对象的dispatch方法, 这个问题跟上面的问题一起说明。
    http_router.match(ngx_var.uri, {method=get_method(), host=ngx_var.host}, api_ctx)

    local route = api_ctx.matched_route
    if not api_ctx.matched_route then
        return admin.resp_exit(404, {error = "没有匹配的路由"})
    end

    api_ctx.plugins = plugin.filter(api_ctx, route)
    plugin.run_plugin("rewrite", api_ctx.plugins, api_ctx)
    -- ngx.log(ngx.ERR, "matched upstream: ", json.encode(route.upstream))
    api_ctx.picked_server = load_balancer.pick_server(route.upstream.nodes)
end
end --do
```
### 动态变化
前面有一个问题, 就是管理接口怎么驱动这里的动态路由,还有就是为啥不直接调用`dispatch`方法, 而是单独包装了一个`match`方法.
这里看看match方法的实现
```lua
function _M.http_init_worker()
    routes_obj = config.new("/routes")
    router = new_http_router(routes_obj.routes)
    cached_conf_version = routes_obj.conf_version
end


function _M.match(uri, match_opts, api_ctx)
    -- ngx.log(ngx.ERR, "cached: ", cached_conf_version, " new conf_version: ", routes_obj.conf_version)
    if cached_conf_version ~= routes_obj.conf_version then
        -- ngx.log(ngx.ERR, "发现新版本, 重新创建路由对象")
        router = new_http_router(routes_obj.routes)
        cached_conf_version = routes_obj.conf_version
    end

    router:dispatch(uri, match_opts, api_ctx)
end
```
通过源代码知道, 每次调用`dispatch`之前需要先判断路由对象的配置版本是否发生的变化, 如果变化了就重新创建一个路由，这样就解决了前面的两个问题.
可以知道这个问题的关键在于`routes_obj`, 这个对象会在后台不断的去比对配置是否发生的变化.

代码如下:
```lua
local json = require("cjson")
local table_clone = require("table.clone")
local ngx_timer_at = ngx.timer.at
local ngx_sleep = ngx.sleep

local admin = require("apix.admin")

local _M = {}
local created_obj = {}


-- 如果不通过table.clone复制对象会存在get_routes里面的数据被更改
-- 因为引用的是同一份数据
local function routes_copy(routes)
    local new_routes = {}
    for i, v in ipairs(routes) do
        new_routes[i] = table_clone(v)
    end
    return new_routes
end


local function sync_data(premature, key)
    -- ngx.log(ngx.ERR, "开始同步数据")
    -- premature是ngx.timer.at函数传的第一个函数，告诉回调函数当前是否在退出
    if premature then
        return
    end

    local current_routes = created_obj[key].routes
    local latest_routes = admin.get_routes()
    if #latest_routes ~= #current_routes then
        created_obj[key].routes = routes_copy(latest_routes)
        -- 通过conf_version字段代表当前配置文件的版本, 用于检测是否需要重新创建路由对象
        created_obj[key].conf_version = created_obj[key].conf_version + 1
    end

    for index, route in ipairs(current_routes) do
        if route.update_time ~= latest_routes[index].update_time then
            created_obj[key].routes = routes_copy(latest_routes)
            created_obj[key].conf_version = created_obj[key].conf_version + 1
            break
        end
    end

    ngx_sleep(1)
    -- 递归调用同步函数, 用于无限同步
    ngx_timer_at(0, sync_data, key)
end

function _M.new(key)
    local obj = {
        routes = {},
        conf_version = 0
    }

    ngx_timer_at(0, sync_data, key)
    created_obj[key] = obj
    return obj
end

return _M
```
通过代码知道, 配置对象通过`ngx.timer.at`配置了一个后台的定时任务,这个定时任务会递归的调用`sync_data`函数, 而`sync_data`函数会在内部sleep一秒, 这是为了性能考虑, 但是也会造成数据的延迟, APISIX的实现更加实时, 它是通过etcd的watch接口实时监听数据是否发生了变化。


### 小结
因为需要动态配置路由, 所以需要在内存中构造了一个router对象用于匹配路由, 因为需要动态的读取最新的路由列表, 所以需要在后台启动一个定时任务来不断的更新路由。


## 插件
如果只是动态路由，那么API网关的功能会比较单薄，因此需要一种机制来扩展网关的功能，Kong, APISIX都有非常多的插件来扩展网关的功能, 这里自然也实现一下插件的机制。

插件的实现比较简单, 代码如下:
```lua
local json = require("cjson")
local pcall = pcall
local require = require
local ngx_exit = ngx.exit

local admin = require("apix.admin")

local _M = {}
-- 默认要加载的路由列表
local enabled_plugins = {"basic-auth", "echo"}
local loaded_plugins = {}


function _M.http_init_worker()
    for _, plugin_name in ipairs(enabled_plugins) do
        -- 通过pcall可以在当前进程不崩溃的情况下尝试调用指定函数
        -- 为了保证插件加载的健壮性
        local ok, plugin_obj = pcall(require, "apix.plugins." .. plugin_name)
        if not ok then
            ngx.log(ngx.ERR, "加载plugin: " .. plugin_name .. "失败")
        end
        loaded_plugins[plugin_name] = plugin_obj
    end
end


function _M.run_plugin(phase, plugins, ctx)
    -- ngx.log(ngx.ERR, "阶段: " .. phase .. "开始运行插件")
    if not plugins then
        return 
    end

    local plugin_run = false
    -- 本代码只执行了两个阶段的插件 rewrite, body_filter
    -- rewrite阶段可能会返回响应码和内容, 如果存在响应码就直接返回, 不会继续处理
    -- 所以需要单独处理
    if phase ~= "body_filter" then
        for i = 1, #plugins, 2 do
            local plugin_func = plugins[i][phase]
            if plugin_func then
                plugin_run = true
                local code, res = plugin_func(plugins[i+1], ctx)
                if code then
                    admin.resp_exit(code, res)
                end
            end
        end
        return ctx, plugin_run
    end

    -- 非rewrite阶段只是改写header, body, 增加日志等, 所以直接调用即可
    for i = 1, #plugins, 2 do
        local plugin_func = plugins[i][phase]
        if plugin_func then
            -- ngx.log(ngx.ERR, "开始运行插件: " .. json.encode(plugins[i+1]))
            plugin_run = true
            plugin_func(plugins[i+1], ctx)
        end
    end
    return ctx, plugin_run
end


function _M.filter(ctx, conf)
    local user_plugins_conf = conf.plugins
    if not user_plugins_conf then
        return nil
    end
    -- 加载路由中配置的插件
    -- 注意: 这里是首先遍历enabled_plugins插件列表然后去加载插件的
    -- 这样的做法可以保证插件按照enabled_plugins插件的配置顺序依次执行
    local plugins = {}
    for _, plugin_name in ipairs(enabled_plugins) do
        local plugin_conf = user_plugins_conf[plugin_name]
        if plugin_conf then
            table.insert(plugins, loaded_plugins[plugin_name])
            table.insert(plugins, plugin_conf)
        end
    end
    
    return plugins
end

return _M
```
插件在初始化的时候会根据`enabled_plugins`的值动态的从本地导入插件对象, 保存到`loaded_plugins`, 后续运行插件的时候会调用这些对象。

运行插件的逻辑就是根据路由中配置的信息作为conf对象传给前面导入的插件对象, 调用对应的阶段方法。

每个插件会实现对应节点的方法, 比如`rewrite`, `body_filter`, 之所以不同的阶段实现不同的方法, 这其实是为了符合openresty的最佳实践。


## 总结
这里开发的网关主要是借助了nginx稳定高效的网络转发能力, 即数据面, 而网关的功能在于控制面的开发。

代码地址: https://github.com/youerning/blog/tree/master/apix_code






