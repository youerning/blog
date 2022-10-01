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