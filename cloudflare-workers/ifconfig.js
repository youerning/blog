// 获取客户端请求信息
// https://ifconfig.youerning.top/

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  // 获取客户端IP（优先使用CF专用头）
  const ip = request.headers.get('CF-Connecting-IP') || 
             request.headers.get('X-Forwarded-For') || 
             'IP not available';

  // 获取请求头信息
  const headers = {};
  for (const [key, value] of request.headers) {
    headers[key] = value;
  }

  // 获取Cloudflare提供的扩展信息[1,5](@ref)
  const cfInfo = request.cf ? { ...request.cf } : {};
  
  // 可选：添加地理位置信息[3,5](@ref)
  if (!cfInfo.country) {
    cfInfo.country = request.headers.get('CF-IPCountry');
    cfInfo.city = request.headers.get('CF-IPCity');
  }

  // 构建响应对象
  const responseData = {
    ip: ip,
    headers: headers,
    cf: cfInfo,
    timestamp: new Date().toISOString(),
    method: request.method,
    url: request.url
  };

  // 返回JSON响应
  return new Response(JSON.stringify(responseData, null, 2), {
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*' // 允许跨域访问
    }
  });
}