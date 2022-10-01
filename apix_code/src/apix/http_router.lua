local config = require("apix.config")
local ngx_re = require("ngx.re")

local base_router = require("apix.router")

local _M = {}
local router
local cached_conf_version
local routes_obj = {}


local function new_http_router(routes)
    for _, route in ipairs(routes) do
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

return _M