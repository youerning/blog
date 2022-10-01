local json = require("cjson")
local ngx_re = ngx.re
local ipairs = ipairs

local _M = {}
local mt = {__index = _M}


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