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


local admin_routes = {
    {
        methods = {"GET", "POST", "DELETE", "PUT"},
        uri = "/apix/admin/routes*",
    }
}


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