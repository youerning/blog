local ngx = ngx

local _M = {}


function _M.body_filter(conf, ctx)
    -- ngx.arg[1]代表当前读取的body的内容
    -- ngx.arg[2]代表是否已经读取完所有body内容
    ngx.log(ngx.ERR, "basic-auth 开始处理")
    if conf.body then
        ngx.arg[1] = conf.body
        ngx.arg[2] = true
    end

    if conf.before_body and not ctx.plugin_echo_body_set then
        ngx.arg[1] = conf.before_body ..  ngx.arg[1]
        ctx.plugin_echo_body_set = true
    end

    if ngx.arg[2] and conf.after_body then
        ngx.arg[1] = ngx.arg[1] .. conf.after_body
    end
end

return _M