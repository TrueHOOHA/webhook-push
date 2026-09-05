# message_push

企业微信群机器人消息推送工具，完全零依赖，Python 标准库即可运行。

## 快速开始

```bash
python server.py
```

浏览器打开 `http://localhost:5000`，填写消息内容后发送。

## 配置

编辑同目录下的 `webhook_url.txt`，每行一个 webhook URL：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key1
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key2
```

## 命令行（可选）

如需命令行使用，仍需安装 `requests`：

```bash
pip install requests
python message_push.py --type markdown --content "# 通知内容"
```

## 目录结构

```
message_push.py     # CLI 命令行工具
server.py           # Web 服务器（零依赖）
templates/
  index.html        # Web 界面
webhook_url.txt     # webhook 地址配置
requirements.txt    # 仅 CLI 需要
README.md
```
