# message_push

一个基于 `venv` 管理依赖的企业微信机器人消息发送脚本，支持：

- 从本地文件读取一个或多个 webhook URL
- 发送 `markdown` 或 `text` 消息
- 直接传入消息内容，或从本地文本文件读取消息内容
- 运行时进入终端交互界面，选择内容来源和文本文件路径
- 文本消息 `@所有人`
- `dry-run` 本地预览 payload

## 目录结构

```text
push/
├─ message_push.py
├─ requirements.txt
├─ webhook_url.txt
└─ venv/
```

## 1. 创建虚拟环境

在当前目录执行：

```bash
python -m venv venv
```

Windows 安装依赖：

```bash
venv\Scripts\pip install -r requirements.txt
```

## 2. 配置 webhook 文件

脚本默认读取同目录下的 `webhook_url.txt`。

文件格式：**每行一个 webhook URL**，空行会自动跳过。

示例：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key1
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key2
```

如果只发一个群，就只写一行。

## 3. 基本用法

### 发送默认 Markdown 模板

```bash
venv\Scripts\python message_push.py
```

### 发送自定义 Markdown 内容

```bash
venv\Scripts\python message_push.py --type markdown --content "# 标题

这里是自定义 Markdown 内容"
```

### 从本地文本文件读取 Markdown 内容发送

```bash
venv\Scripts\python message_push.py --type markdown --content-file "C:\\path\\to\\message.md"
```

### 发送自定义文本内容

```bash
venv\Scripts\python message_push.py --type text --content "这是一条文本通知"
```

### 从本地文本文件读取文本内容发送

```bash
venv\Scripts\python message_push.py --type text --content-file "C:\\path\\to\\message.txt"
```

### 交互模式选择内容来源

```bash
venv\Scripts\python message_push.py --interactive
```

运行后可在终端中选择：

1. 使用默认模板
2. 直接输入内容
3. 从本地文件读取内容

如果选择第 3 项，脚本会提示你输入本地文本文件或 Markdown 文件路径。

### 文本消息 @所有人

```bash
venv\Scripts\python message_push.py --type text --content "请尽快查看" --mention-all
```

### 指定其他 webhook 文件

```bash
venv\Scripts\python message_push.py --webhook-file "C:\path\to\my_webhook.txt" --content "这是自定义内容"
```

### 仅预览，不实际发送

```bash
venv\Scripts\python message_push.py --type text --content "测试内容" --dry-run
```

## 4. 参数说明

| 参数 | 说明 |
| --- | --- |
| `--webhook-file` | webhook 文件路径，默认是脚本同目录下的 `webhook_url.txt` |
| `--type` | 消息类型：`markdown` 或 `text`，默认 `markdown` |
| `--content` | 直接指定发送内容；与 `--content-file` 二选一 |
| `--content-file` | 从本地文本文件读取发送内容；与 `--content` 二选一 |
| `--interactive` | 启动终端交互模式，运行时选择内容来源和本地文件路径 |
| `--mention-all` | 仅 `text` 消息生效，发送时 `@所有人` |
| `--timeout` | 请求超时时间，默认 `10` 秒 |
| `--dry-run` | 只打印 payload 和 webhook 数量，不真正发送 |

## 5. 返回码

脚本执行结束后会返回以下状态码：

- `0`：全部发送成功
- `1`：全部发送失败，或 webhook 文件读取失败
- `2`：部分发送成功，部分发送失败

## 6. 说明

- 群发是**按行逐个发送**，不是并发发送
- 某个 webhook 发送失败，不会中断其他 webhook
- `webhook_url.txt` 中建议只保留 URL，不要混入其他说明文字
- `--content` 和 `--content-file` 是互斥的，二者都不传时使用脚本内默认模板
- `--interactive` 只有在没有传入 `--content` / `--content-file` 时，才会进入内容来源选择流程

## 7. 安全建议

建议不要把以下内容提交到代码仓库：

```gitignore
venv/
webhook_url.txt
```

如果你需要，可以继续补一个 `.gitignore`。