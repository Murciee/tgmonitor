# Telegram Keyword Monitor (Userbot + Bot 双端系统)

这是一个专为 Telegram 打造的高级群组关键字监控系统。它通过 Userbot 隐形监听指定群组，当触发设定好的正则/关键词时，自动将消息**原生转发**到你的私人频道。

同时，它集成了一个官方 Bot 作为**可视化控制台**。你无需修改代码或重启服务，直接在 Telegram 内点击按钮即可完成所有规则的管理。

## ✨ 核心特性

* **🚀 纯图形化管理**：通过内联按钮（Inline Keyboard）管理配置，告别繁琐的命令行操作。
* **🖱️ 动态点击删除**：所有的监控群、关键词、黑名单都会生成按钮列表，点一下即可删除。
* **🧲 消息抓取解析**：直接将带有目标用户的消息/群组信息转发给 Bot，Bot 会自动提取 ID 并弹出快捷添加面板。
* **⏸️ 全局状态控制**：一键暂停/恢复监控，无需停机。
* **🛡️ 完美防封/黑名单抗坑**：原生 Forward 转发（完美保留原消息按钮与排版）；双重黑名单检测（同时拦截发送者与原消息作者）。

## 🛠️ 部署指南 (Docker)

本应用强烈依赖 Docker 运行。

### 1. 准备工作
* 申请 [Telegram API_ID 和 API_HASH](https://my.telegram.org)
* 通过 [@BotFather](https://t.me/BotFather) 申请一个机器人的 `BOT_TOKEN`
* 准备一个接收通知的频道/群组，获取其 `Chat ID`（如 `-100123456789`）
* 获取你自己的个人 Telegram 用户 ID (`ADMIN_ID`)

### 2. 填写配置
克隆项目后，修改 `docker-compose.yml` 中的环境变量：
```yaml
environment:
  - API_ID=你的API_ID
  - API_HASH=你的API_HASH
  - BOT_TOKEN=你的Bot_Token
  - TARGET_CHANNEL=-100xxxxxxxxxx
  - ADMIN_ID=123456789
3. 首次交互登录 (关键)
由于 Telegram 的机制，Userbot 首次运行必须接收手机验证码。千万不要直接后台启动！

在终端中运行交互模式：

Bash
docker-compose run --rm -it emby-monitor
按照终端提示，输入你的手机号（需带国家区号，如 +8613800000000）。

检查你的 Telegram，获取官方发来的登录验证码并在终端填入。

看到 系统运行中... 提示后，按 Ctrl+C 退出。此时当前目录已生成免密登录凭证 .session。

4. 正式后台运行
凭证生成后，一键拉起后台服务：

Bash
docker-compose up -d
🎮 使用方法
部署成功后，在 Telegram 中找到你通过 BotFather 申请的那个机器人。

唤出控制台：向机器人发送 /start。

快捷提取 ID：如果不知道某个群的 ID 或某人的 ID，直接在其他群里把他们的发言转发给这个 Bot，Bot 会自动解析并弹窗问你是否加入黑名单或监控群。

实时生效：所有的点击和配置修改会实时写入 config.json，下一次触发监控时立即生效，无需重启 Docker 容器！

安全警告：面板已做硬编码隔离，仅限环境变量中设置的 ADMIN_ID 用户点击操作，其他人乱点会直接弹出无权限警告。
