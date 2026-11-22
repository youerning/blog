# 被穿透的目标服务：多线程、响应 200 字节，专供 curl 测 TCP 握手与首字节
# 端口默认 60990 —— 开放段是 60000-61000，61000 是上界，61002 会落在段外
import http.server, socketserver, sys

BODY = b"x" * 200

class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        big = self.path.startswith("/big")   # /big 返回 2MB，用来量吞吐
        body = b"x" * (2 * 1024 * 1024) if big else BODY
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass

class S(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 60990
    S(("0.0.0.0", port), H).serve_forever()
