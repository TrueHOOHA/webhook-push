<div align="center">

# 企业微信群消息推送

基于 Webhook 的轻量企业微信通知工具，零依赖，一键启动。

`Python` · `HTML` · `零依赖`

</div>

---

## ✨ 特性

- 🚀 **零依赖** — 仅用 Python 标准库，无需 `pip install`
- 🌐 **网页界面** — 浏览器即可操作，支持浅色 / 深色主题
- 📝 **多种消息类型** — 纯文本、Markdown、Markdown V2、图片
- 🖼️ **本地图片** — 直接选图发送，自动转 base64
- 👥 **@所有人** — 纯文本消息一键提醒全员
- 🔗 **多群推送** — 支持多个 webhook 地址同时发送
- 🔒 **密钥保护** — webhook 密钥文件已加入 `.gitignore`

---

## 🚀 快速开始

```bash
# 启动服务器
python server.py
```

浏览器打开 <http://localhost:5000> 即可使用。

> 要求 Python 3.8+，无需安装任何第三方库。

---

## ⚙️ 配置

在 `webhook_url.txt` 中配置企业微信群机器人地址，**每行一个**，空行自动忽略：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key1
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=你的key2
```

> 配置了多个地址时，消息会统一推送到所有群。

---

## 📖 使用说明

### 消息类型

| 类型 | 说明 |
|------|------|
| **Markdown** | 支持标题、表格、引用、字体颜色等 |
| **Markdown V2** | 新版语法，不支持字体颜色与 @成员 |
| **纯文本** | 支持 `@所有人` |
| **图片** | 本地选图，可同时多张 |

### 命令行（可选）

如需命令行推送，需额外安装 `requests`：

```bash
pip install requests
python message_push.py --type markdown --content "# 通知内容"
```

---

## 📁 目录结构

```
server.py            # Web 服务器（零依赖，Python 标准库）
templates/
  index.html         # 网页界面
message_push.py      # 命令行工具（可选）
webhook_url.txt      # webhook 地址配置（已 gitignore）
requirements.txt     # 仅命令行工具需要
```

---

## 🛡️ 安全建议

- `webhook_url.txt` 包含推送密钥，**已被 `.gitignore` 忽略**，切勿提交到仓库
- 请勿在公开渠道（博客、GitHub）泄露你的 webhook 地址，防止他人恶意推送

---

## 📄 License

MIT