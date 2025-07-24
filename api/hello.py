"""
最もシンプルなVercel Python関数
"""

from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write('{"status": "ok", "message": "Hello from Vercel"}'.encode())
        return