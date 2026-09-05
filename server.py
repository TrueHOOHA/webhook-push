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
import re

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
        if self.path == "/upload":
            self._handle_upload()
        elif self.path == "/send":
            self._handle_send()
        else:
            self._send_not_found()

    # ── 文件上传（浏览器 → 服务器）───────────────────────────

    def _parse_multipart(self, body, content_type):
        m = re.search(r"boundary=(.+?)(?:;|$)", content_type)
        if not m:
            return {}, b""
        boundary = m.group(1).strip().strip('"')
        delim = f"--{boundary}".encode()
        parts = body.split(delim)
        for part in parts:
            if b"\r\n\r\n" not in part or not part.strip():
                continue
            header_block, file_data = part.split(b"\r\n\r\n", 1)
            headers = self._parse_headers(header_block.decode("utf-8", errors="replace"))
            if headers.get("name") == "file":
                return headers, file_data.rstrip(b"\r\n")
        return {}, b""

    def _parse_headers(self, text):
        result = {}
        for line in text.splitlines():
            if ": " in line:
                key, val = line.split(": ", 1)
                result[key.lower()] = val.strip()
        cd = result.get("content-disposition", "")
        m = re.search(r'name="([^"]+)"', cd) or re.search(r"name=([^;\s]+)", cd)
        if m:
            result["name"] = m.group(1).strip('"')
        m = re.search(r'filename="([^"]+)"', cd) or re.search(r"filename=([^;\s]+)", cd)
        if m:
            result["filename"] = m.group(1).strip('"')
        return result

    def _handle_upload(self):
        length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")
        body = self.rfile.read(length) if length else b""

        headers, file_data = self._parse_multipart(body, content_type)
        if not headers:
            self._json({"ok": False, "error": "Invalid multipart request"}, 400)
            return

        filename = headers.get("filename", "upload")
        ext = Path(filename).suffix.lower()
        allowed = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
        if ext not in allowed:
            self._json({"ok": False, "error": f"不支持的文件类型，仅支持图片（{', '.join(sorted(allowed))}）"}, 400)
            return

        if len(file_data) > 10 * 1024 * 1024:
            self._json({"ok": False, "error": "文件大小超过限制（最大 10MB）"}, 400)
            return

        try:
            media_id = self._upload_to_wechat(file_data, ext.lstrip("."))
        except Exception as e:
            self._json({"ok": False, "error": f"上传失败: {e}"}, 500)
            return

        self._json({"ok": True, "media_id": media_id})

    def _upload_to_wechat(self, file_data, ext):
        """上传到企业微信并返回 media_id"""
        urls = self._load_webhook_urls()
        if not urls:
            raise Exception("webhook_url.txt 未配置")

        key = self._extract_key(urls[0])
        upload_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key={key}&type={ext}"

        boundary = "----UploadBoundary"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="media"; filename="image.{ext}"\r\n'
            f"Content-Type: image/{ext}\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

        req = request.Request(
            upload_url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        if result.get("errcode", -1) != 0:
            raise Exception(result.get("errmsg", "upload failed"))
        return result["media_id"]

    # ── 消息发送 ──────────────────────────────────────────────

    def _handle_send(self):
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
        title = data.get("title", "").strip()
        media_id = data.get("media_id", "").strip()

        if msg_type == "image":
            if not media_id:
                self._json({"ok": False, "error": "图片类型需要提供 media_id"}, 400)
                return
        elif not content:
            self._json({"ok": False, "error": "Content cannot be empty"}, 400)
            return

        webhook_urls = self._load_webhook_urls()
        if not webhook_urls:
            self._json({"ok": False, "error": "No webhook URLs configured"}, 500)
            return

        payload = self._build_payload(msg_type, content, mention_all, title=title, media_id=media_id)
        results, success = [], 0

        for i, url in enumerate(webhook_urls, 1):
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

        if success == len(webhook_urls):
            self._json({"ok": True, "sent": success, "total": len(webhook_urls)})
        elif success > 0:
            self._json({"ok": False, "sent": success, "total": len(webhook_urls), "errors": results}, 207)
        else:
            self._json({"ok": False, "sent": 0, "total": len(webhook_urls), "errors": results}, 500)

    def _build_payload(self, msg_type, content, mention_all, title="", media_id=""):
        if msg_type == "text":
            if mention_all:
                content = "@所有人 " + content
            return {"msgtype": "text", "text": {"content": content}}
        if msg_type == "image":
            return {"msgtype": "image", "image": {"media_id": media_id}}
        return {"msgtype": "markdown", "markdown": {"content": content}}

    # ── 工具方法 ──────────────────────────────────────────────

    def _load_webhook_urls(self):
        try:
            return [
                line.strip()
                for line in WEBHOOK_FILE.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except FileNotFoundError:
            return []

    def _extract_key(self, url):
        m = re.search(r"\?key=([a-zA-Z0-9\-]+)", url)
        return m.group(1) if m else ""

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_not_found(self):
        self.send_response(404)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")


if __name__ == "__main__":
    print("Server running at http://localhost:5000")
    print("Press Ctrl+C to stop.")
    HTTPServer(("0.0.0.0", 5000), Handler).serve_forever()
