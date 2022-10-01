local json = require("cjson")

local ngx = ngx
local ngx_var = ngx.var
local get_method = ngx.req.get_method
local ngx_re = ngx.re
local ngx_exit = ngx.exit

local admin = require("apix.admin")
local load_balancer = require("apix.balancer")
local http_router = require("apix.http_router")
local base_router = require("apix.router")
local plugin = require("apix.plugin")


local _M = {}
local router
local user_routes
local shared_routes
local shared_routes_key = "routes"


local default_routes = [[
    [{
        "id": 1,
        "host": "test.com",
        "methods": ["GET", "POST"],
        "uri": "/*",
        "update_time": 1663833578,
        "upstream": {
            "nodes": {
                "127.0.0.1:81": 1,
                "127.0.0.1:82": 1
            }
        }
    },
    {
        "id": 2,
        "host": "test2.com",
        "methods": ["GET", "POST"],
        "uri": "/*",
        "update_time": 1663833578,
        "plugins": {
            "basic-auth": {
                "username": "test",
                "password": "test"
            },
            "echo": {
                "before_body": "echo before here\n",
                "after_body": "\necho after here\n"
            }
        },
        "upstream": {
            "nodes": {
                "127.0.0.1:81": 1,
                "127.0.0.1:82": 1
            }
        }
    }]
]]


function _M.http_init()
    -- 设置默认的路由列表
    admin.set_routes(json.decode(default_routes))
end

function _M.http_init_worker()
    -- 初始化各组件
    admin.http_init_worker()
    http_router.http_init_worker()
    plugin.http_init_worker()
end


function _M.http_balancer_phase()
    -- ngx.log(ngx.ERR, "开始balancer阶段")
    local api_ctx = ngx.ctx.api_ctx
    load_balancer.run(api_ctx.matched_route, api_ctx)
end

do
    local admin_router
function _M.http_admin()
    if not admin_router then
        admin_router = admin.get()
    end
    admin_router:dispatch(ngx_var.uri, {method=get_method()})
end
end  -- do


do 
function _M.http_access_phase()
    -- ngx.log(ngx.ERR, "开始access阶段")
    local api_ctx = {}
    ngx.ctx.api_ctx = api_ctx
    
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

function _M.http_header_filter_phase()
    
end

function _M.http_body_filter_phase()
    local ctx = ngx.ctx.api_ctx
    plugin.run_plugin("body_filter", ctx.plugins, ctx)
end

function _M.http_log_phase()
    
end


return _M