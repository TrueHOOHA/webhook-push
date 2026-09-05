#!/usr/bin/env python3
"""
轻量级消息推送服务器（零依赖，Python 标准库即可运行）
用法: python server.py
浏览器访问 http://localhost:5000
"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import requests

WEBHOOK_FILE = Path(__file__).parent / "webhook_url.txt"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self):
        # 所有 GET 请求都返回 index.html
        self.path = "/templates/index.html"
        super().do_GET()

    def do_POST(self):
        if self.path != "/send":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length)) if length else {}
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
                r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=10)
                r.raise_for_status()
                success += 1
                results.append({"index": i, "ok": True})
            except Exception as e:
                results.append({"index": i, "ok": False, "error": str(e)})

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
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print("Server running at http://localhost:5000")
    print("Press Ctrl+C to stop.")
    HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
