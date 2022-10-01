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