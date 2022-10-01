local ngx_re = require("ngx.re")
local ngx_header = ngx.header
local get_headers = ngx.req.get_headers
local ngx = ngx

local _M = {}


-- 直接复制自APISIX
local function extract_auth_header(auth_header)
    local m, err = ngx.re.match(auth_header, "Basic\\s(.+)", "jo")
    if err then
        return nil, nil, err
    end

    if not m then
        return nil, nil, "Invalid authorization header format"
    end

    local decoded = ngx.decode_base64(m[1])

    if not decoded then
        return nil, nil, "Failed to decode authentication header: " .. m[1]
    end

    local res
    res, err = ngx_re.split(decoded, ":")
    if err then
        return nil, nil, "Split authorization err:" .. err
    end
    if #res < 2 then
        return nil, nil, "Split authorization err: invalid decoded data: " .. decoded
    end

    local username = ngx.re.gsub(res[1], "\\s+", "", "jo")
    local password = ngx.re.gsub(res[2], "\\s+", "", "jo")

    return username, password, nil
end

function _M.rewrite(conf, ctx)
    -- ngx.log(ngx.ERR, "basic-auth 开始处理")
    local auth_header = get_headers()["Authorization"]
    if not auth_header then
        ngx_header["WWW-Authenticate"] = "Basic realm='.'"
        return 401, { message = "Missing authorization in request" }
    end

    local username, password, err = extract_auth_header(auth_header)
    -- ngx.log(ngx.ERR, "username: ", username, " password: ", password)
    if err then
        return 401, { message = err }
    end

    if conf.username ~= username and conf.password ~= password then
        return 401, { message = "invalid username or password" }
    end
end

return _M