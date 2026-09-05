#!/usr/bin/env python3
"""
企业微信消息推送服务器（完全零依赖，Python 标准库即可运行）
用法: python server.py
浏览器访问 http://localhost:5000
"""
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError

WEBHOOK_FILE = Path(__file__).parent / "webhook_url.txt"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self):
        self.path = "/templates/index.html"
        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path != "/send":
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            data = json.loads(raw)
        except Exception:
            self._json({"ok": False, "error": "Invalid JSON"}, 400)
            return

        msg_type = data.get("type", "markdown")
        content = data.get("content", "").strip()
        mention_all = data.get("mention_all", False)

        if not content:
            self._json({"ok": False, "error": "Content cannot be empty"}, 400)
            return

        try:
            urls = [
                line.strip()
                for line in WEBHOOK_FILE.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except FileNotFoundError:
            self._json({"ok": False, "error": "webhook_url.txt not found"}, 500)
            return
        except Exception as e:
            self._json({"ok": False, "error": str(e)}, 500)
            return

        if not urls:
            self._json({"ok": False, "error": "No webhook URLs configured"}, 500)
            return

        payload = self._build_payload(msg_type, content, mention_all)
        results, success = [], 0

        for i, url in enumerate(urls, 1):
            try:
                req = request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with request.urlopen(req, timeout=10) as resp:
                    success += 1
                    results.append({"index": i, "ok": True})
            except HTTPError as e:
                results.append({"index": i, "ok": False, "error": f"HTTP {e.code}"})
            except URLError as e:
                results.append({"index": i, "ok": False, "error": str(e.reason)})

        if success == len(urls):
            self._json({"ok": True, "sent": success, "total": len(urls)})
        elif success > 0:
            self._json({"ok": False, "sent": success, "total": len(urls), "errors": results}, 207)
        else:
            self._json({"ok": False, "sent": 0, "total": len(urls), "errors": results}, 500)

    def _build_payload(self, msg_type, content, mention_all):
        if msg_type == "text":
            p = {"msgtype": "text", "text": {"content": content}}
            if mention_all:
                p["text"]["mentioned_list"] = ["@all"]
            return p
        return {"msgtype": "markdown", "markdown": {"content": content}}

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("Server running at http://localhost:5000")
    print("Press Ctrl+C to stop.")
    HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
