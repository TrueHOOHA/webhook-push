#!/usr/bin/env python3
"""
企业微信消息推送服务器（完全零依赖，Python 标准库即可运行）
用法: python server.py
浏览器访问 http://localhost:5000
"""
import base64 as b64mod
import hashlib
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
        if self.path != "/":
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not Found")
            return
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
        base64s = data.get("base64s", []) or data.get("base64", "")

        if msg_type == "image":
            images = base64s if isinstance(base64s, list) else ([base64s] if base64s else [])
            if not images:
                self._json({"ok": False, "error": "图片类型需要提供图片数据"}, 400)
                return
        elif not content:
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

        results = []
        total_images = len(images) if msg_type == "image" else 1
        success_count = 0

        for webhook_url in urls:
            if msg_type == "image":
                for img_data in images:
                    try:
                        req = request.Request(
                            webhook_url,
                            data=json.dumps(self._build_image_payload(img_data)).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST",
                        )
                        with request.urlopen(req, timeout=15) as resp:
                            body = resp.read().decode("utf-8", errors="replace")
                            result = self._parse_wechat_response(body)
                            if result["ok"]:
                                success_count += 1
                            results.append(result)
                    except HTTPError as e:
                        results.append({"ok": False, "error": f"HTTP {e.code}"})
                    except URLError as e:
                        results.append({"ok": False, "error": str(e.reason)})
            else:
                payload = self._build_payload(msg_type, content, mention_all)
                try:
                    req = request.Request(
                        webhook_url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    with request.urlopen(req, timeout=10) as resp:
                        body = resp.read().decode("utf-8", errors="replace")
                        result = self._parse_wechat_response(body)
                        if result["ok"]:
                            success_count += 1
                        results.append(result)
                except HTTPError as e:
                    results.append({"ok": False, "error": f"HTTP {e.code}"})
                except URLError as e:
                    results.append({"ok": False, "error": str(e.reason)})

        total_expected = len(urls) * total_images
        if success_count == total_expected:
            self._json({"ok": True, "sent": success_count, "total": total_expected})
        elif success_count > 0:
            self._json({"ok": False, "sent": success_count, "total": total_expected, "errors": results}, 207)
        else:
            self._json({"ok": False, "sent": 0, "total": total_expected, "errors": results}, 500)

    def _build_image_payload(self, base64_data):
        raw = b64mod.b64decode(base64_data)
        md5 = hashlib.md5(raw).hexdigest()
        return {
            "msgtype": "image",
            "image": {"base64": base64_data, "md5": md5},
        }

    def _build_payload(self, msg_type, content, mention_all):
        if msg_type == "text":
            if mention_all:
                content = "@所有人 " + content
            return {"msgtype": "text", "text": {"content": content}}
        # markdown 与 markdown_v2 顶层字段名恰好和 msg_type 字符串一致
        return {"msgtype": msg_type, msg_type: {"content": content}}

    def _parse_wechat_response(self, body):
        """企业微信 Webhook 在 HTTP 200 下也会返回 errcode != 0（如频率限制、参数错误），
        必须检查响应体里的 errcode 才能判定是否真正发送成功。"""
        try:
            data = json.loads(body)
        except (ValueError, TypeError):
            return {"ok": False, "error": f"无效响应: {body[:200]}"}
        if data.get("errcode", 0) == 0:
            return {"ok": True}
        return {"ok": False, "error": data.get("errmsg", "unknown error"), "errcode": data.get("errcode")}

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
