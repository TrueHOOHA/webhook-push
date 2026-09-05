#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
WeChat Webhook Message Sender
通过企业微信群机器人发送文本或 Markdown 消息。

推荐使用方式（Windows）：
    python message_push.py --content "这是一条测试通知"
    python message_push.py --type markdown --content "# 标题\n\n自定义内容"
    python message_push.py --type text --content "文本通知" --dry-run
    python message_push.py --interactive

webhook_url.txt 支持多行：
    每行一个 webhook URL
    空行会自动跳过
"""

from __future__ import annotations

import argparse
import base64 as b64mod
import hashlib
import json
from pathlib import Path
import sys
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

WEBHOOK_FILE_PATH = Path(__file__).with_name("webhook_url.txt")
DEFAULT_MARKDOWN_CONTENT = (
    "@所有人 \n\n# 周末维护通知\n\n## 系统重启安排\n\n"
    "> **重启时间**: <font color=\"warning\">今日下午16:00</font>  \n"
    "> **涉及系统**: 仿真系统和生产系统  \n"
    "> **预计恢复**: <font color=\"info\">18:00</font>\n\n"
    "### PTrade系统状态\n\n"
    "| 系统名称 | 当前状态 | 详细说明 |\n"
    "|----------|----------|----------|\n"
    "| **PTrade仿真端** | <font color=\"success\">正常使用</font> | 本周末无变更，可以正常使用 |\n"
    "| **PTrade生产端** | <font color=\"warning\">测试模式</font> | 明日（1月17日）8:00开始测试，期间可使用“离线登录”功能进行研究和回测 |\n\n"
    "**感谢您的支持与配合！**"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="向企业微信 Webhook 发送文本或 Markdown 消息。"
    )
    parser.add_argument(
        "--webhook-file",
        default=str(WEBHOOK_FILE_PATH),
        help="保存企业微信 webhook 地址的本地文件路径，默认使用脚本目录下的 webhook_url.txt。",
    )
    parser.add_argument(
        "--type",
        choices=("markdown", "markdown_v2", "text", "image"),
        default="markdown",
        help="消息类型，默认 markdown。",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--content",
        help="直接指定自定义发送内容；不传时可改用 --content-file，二者都不传则使用默认模板。",
    )
    group.add_argument(
        "--content-file",
        help="从本地文本文件读取发送内容，支持 text 和 markdown。",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="启动终端交互模式，运行时选择内容来源和本地文本文件路径。",
    )
    parser.add_argument(
        "--mention-all",
        action="store_true",
        help="仅 text 消息生效：自动 @所有人。",
    )
    parser.add_argument(
        "--image",
        dest="image_path",
        help="image 类型时使用的本地图片路径。",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="请求超时时间（秒），默认 10。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅在本地打印将发送的 payload，不实际调用 webhook。",
    )
    return parser.parse_args()


def load_webhook_urls(webhook_file: str) -> list[str]:
    file_path = Path(webhook_file)
    if not file_path.exists():
        raise FileNotFoundError(f"Webhook 文件不存在: {file_path}")

    webhook_urls = [
        line.strip()
        for line in file_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not webhook_urls:
        raise ValueError(f"Webhook 文件内容为空: {file_path}")

    return webhook_urls


def read_content_file(content_file: str) -> str:
    file_path = Path(content_file)
    if not file_path.exists():
        raise FileNotFoundError(f"内容文件不存在: {file_path}")

    file_content = file_path.read_text(encoding="utf-8")
    if not file_content.strip():
        raise ValueError(f"内容文件为空: {file_path}")

    return file_content


def prompt_interactive_content(message_type: str) -> tuple[str | None, str | None]:
    print("请选择发送内容来源：")
    print("1. 使用默认模板")
    print("2. 直接输入内容")
    print("3. 从本地文件读取内容")

    while True:
        choice = input("请输入选项编号 (1/2/3): ").strip()
        if choice == "1":
            return None, None
        if choice == "2":
            print("请输入要发送的内容，输入完成后直接回车确认：")
            typed_content = input().rstrip()
            if not typed_content:
                print("输入内容不能为空，请重新选择。")
                continue
            return typed_content, None
        if choice == "3":
            prompt = "请输入本地文本文件路径: "
            if message_type == "markdown":
                prompt = "请输入本地 Markdown/文本文件路径: "
            content_file = input(prompt).strip().strip('"')
            if not content_file:
                print("文件路径不能为空，请重新选择。")
                continue
            return None, content_file
        print("无效选项，请输入 1、2 或 3。")


def load_content(
    content: str | None,
    content_file: str | None,
    interactive: bool,
    message_type: str,
) -> tuple[str | None, str | None]:
    if interactive and content is None and content_file is None:
        content, content_file = prompt_interactive_content(message_type)

    if content is not None:
        return content, None

    if content_file is None:
        return None, None

    file_content = read_content_file(content_file)
    return file_content, content_file


def build_message(message_type: str, content: str | None, mention_all: bool, image_path: str | None) -> dict[str, Any]:
    if message_type == "text":
        text_content = content or "这是一条默认文本通知。"
        payload: dict[str, Any] = {
            "msgtype": "text",
            "text": {
                "content": text_content,
            },
        }
        if mention_all:
            payload["text"]["mentioned_list"] = ["@all"]
        return payload

    if message_type in ("markdown", "markdown_v2"):
        markdown_content = content or DEFAULT_MARKDOWN_CONTENT
        return {
            "msgtype": message_type,
            message_type: {
                "content": markdown_content,
            },
        }

    if message_type == "image":
        if not image_path:
            raise ValueError("image 类型必须通过 --image 指定图片路径")
        raw = Path(image_path).read_bytes()
        encoded = b64mod.b64encode(raw).decode("ascii")
        return {
            "msgtype": "image",
            "image": {
                "base64": encoded,
                "md5": hashlib.md5(raw).hexdigest(),
            },
        }

    raise ValueError(f"不支持的消息类型: {message_type}")


def send_to_wechat(message: dict[str, Any], webhook_url: str, timeout: float) -> tuple[int, str]:
    headers = {"Content-Type": "application/json"}
    data = json.dumps(message).encode("utf-8")
    req = request.Request(webhook_url, data=data, headers=headers, method="POST")
    with request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read().decode("utf-8")


def main() -> int:
    args = parse_args()

    try:
        webhook_urls = load_webhook_urls(args.webhook_file)
        content, selected_content_file = load_content(
            args.content,
            args.content_file,
            args.interactive,
            args.type,
        )
        message = build_message(args.type, content, args.mention_all, args.image_path)
    except (FileNotFoundError, OSError, ValueError) as exc:
        print(f"读取配置失败: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print("Dry run payload:")
        print(message)
        print(f"Webhook file: {args.webhook_file}")
        print(f"Webhook count: {len(webhook_urls)}")
        if selected_content_file:
            print(f"Content file: {selected_content_file}")
        return 0

    success_count = 0
    for index, webhook_url in enumerate(webhook_urls, start=1):
        try:
            status_code, response_text = send_to_wechat(message, webhook_url, args.timeout)
        except (HTTPError, URLError) as exc:
            print(f"[{index}/{len(webhook_urls)}] 发送失败: {exc}", file=sys.stderr)
            continue

        try:
            response_json = json.loads(response_text)
            errcode = response_json.get("errcode", 0)
        except ValueError:
            errcode = 0  # 无法解析时保守视为成功，由人工检查
        if errcode != 0:
            print(f"[{index}/{len(webhook_urls)}] 发送失败: errcode={errcode}, {response_json.get('errmsg', response_text)}", file=sys.stderr)
            continue

        success_count += 1
        print(f"[{index}/{len(webhook_urls)}] Message sent successfully!")
        print(f"Status Code: {status_code}")
        print(f"Response: {response_text}")

    if success_count == len(webhook_urls):
        return 0

    return 1 if success_count == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
