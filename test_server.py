#!/usr/bin/env python3
"""自检：起本地假 webhook + 真 server，验证图片标题以 text 消息先发。用法: python test_server.py"""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib import request

import server

received = []


class DummyWechat(BaseHTTPRequestHandler):
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        received.append(body)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"errcode":0,"errmsg":"ok"}')

    def log_message(self, *a):
        pass


def post_send(payload):
    req = request.Request(
        "http://127.0.0.1:5000/send",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def main():
    dummy = HTTPServer(("127.0.0.1", 5001), DummyWechat)
    threading.Thread(target=dummy.serve_forever, daemon=True).start()

    server.WEBHOOK_FILE = Path(__file__).with_name("test_webhook_url.txt")
    server.WEBHOOK_FILE.write_text("http://127.0.0.1:5001/hook\n", encoding="utf-8")
    real = HTTPServer(("127.0.0.1", 5000), server.Handler)
    threading.Thread(target=real.serve_forever, daemon=True).start()

    img_b64 = base64.b64encode(b"\x89PNG fake").decode()

    # 1. 带标题的图片：标题 text 先发，图片后发
    r = post_send({"type": "image", "title": "测试标题", "base64s": [img_b64, img_b64]})
    assert r["ok"] and r["sent"] == 3, r  # 1 标题 + 2 图片
    assert [m["msgtype"] for m in received] == ["text", "image", "image"]
    assert received[0]["text"]["content"] == "测试标题"

    # 2. 无标题：只发图片
    received.clear()
    r = post_send({"type": "image", "base64s": [img_b64]})
    assert r["ok"] and r["sent"] == 1, r
    assert [m["msgtype"] for m in received] == ["image"]

    # 3. markdown 回归
    received.clear()
    r = post_send({"type": "markdown", "content": "# hi"})
    assert r["ok"] and received[0]["markdown"]["content"] == "# hi"

    dummy.shutdown()
    real.shutdown()
    server.WEBHOOK_FILE.unlink()
    print("all passed")


if __name__ == "__main__":
    main()
