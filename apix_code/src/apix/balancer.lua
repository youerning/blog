local json = require("cjson")
local math = require("math")
local balancer          = require("ngx.balancer")
local set_more_tries   = balancer.set_more_tries
local get_last_failure = balancer.get_last_failure
local set_timeouts     = balancer.set_timeouts
local ngx_now = ngx.now

local admin = require("apix.admin")

local _M = {}
local current_index = 1


function _M.http_init_worker()
    -- math.randomseed(ngx_now())
end

local function set_balancer_opts(route)
    local timeout = route.upstream.timeout
    if timeout then
        set_timeouts(timeout.connect, timeout.send,
                                     timeout.read)
    end

    local retries = route.upstream.retries
    if not retries or retries < 0 then
        retries = #route.upstream.nodes - 1
    end
    set_more_tries(retries)
    -- 这里有一个超级大的bug, 如果所有后端都不能用那么就会无限循环下去, 需要设置一个截止时间, 可以参考apisix的实现
end

local function pick_server(nodes)
    if #nodes == 1 then
       return nodes[1] 
    end

    local server = nodes[current_index]
    current_index = current_index + 1
    if current_index > #nodes then
        current_index = 1
    end
    -- ngx.log(ngx.ERR, "picked server: ", server.host .. ":" .. server.port)
    return server
end

_M.pick_server = pick_server

function _M.run(route, api_ctx)
    local server, err
    set_balancer_opts(route)
    if api_ctx.picked_server then
        server = api_ctx.picked_server
        api_ctx.picked_server = nil
    else
        -- ngx.log(ngx.ERR, "开始重试.....")
        server = pick_server(route.upstream.nodes)
        balancer.set_current_peer(server.host, server.port)
    end
    -- ngx.log(ngx.ERR, "connect to server: ", server.host .. ":" .. server.port)
    balancer.set_current_peer(server.host, server.port)
end

return _M