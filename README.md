# Telegram Emby Monitor (Userbot + Bot 双端交互系统)

这是一个专为 Telegram 打造的高级群组关键字监控系统。它通过 Userbot 隐形监听指定群组，当触发设定好的正则/关键词时，自动将消息**原生转发**到你的私人频道。

集成官方 Bot 作为**可视化控制台**，你可以直接在手机上点击按钮管理所有规则，无需接触代码或重启服务。

---

## ✨ 核心特性

* **🚀 纯图形化管理**：通过内联按钮（Inline Keyboard）管理配置，支持分页显示。
* **🖱️ 动态点击删除**：所有的监控群、关键词、黑名单都会生成列表按钮，点一下即可精准删除。
* **🧲 消息抓取解析**：直接将任何人的发言**转发**给控制 Bot，Bot 会自动解析其 ID 和来源群组 ID，并弹出快捷添加面板。
* **⏸️ 全局状态控制**：主菜单一键切换“运行中/已暂停”，灵活控制监控开关。
* **🛡️ 完美原生转发**：采用 `Forward` 机制，100% 保留原消息的按钮、特效字体、隐藏超链接及 Emoji。
* **💾 数据持久化**：所有配置实时保存至 `config.json`，改完即生效，Docker 重启数据不丢失。

---

## 🔍 常见正则表达式示例

在管理面板中点击“添加正则词”时，可以直接复制以下常用模式（`(?i)` 表示忽略大小写）：

| 匹配目标 | 正则表达式示例 | 说明 |
| :--- | :--- | :--- |
| **Emby 综合监控** | `(?i)emby.*(注册|邀请|开注|发码)` | 匹配 Emby 关键词后跟常见的动作词 |
| **通用激活码** | `(?i)(invite|code|邀请码|注册码|激活码)` | 抓取各类含“码”的信息 |
| **英文开注提醒** | `(?i)(register|sign up|open now)` | 监控国外频道/群组的开注动态 |
| **私有加群链接** | `https://t\.me/\+` | 捕捉包含私有群组邀请链接的消息 |
| **排除负面词汇** | `^(?!.*(满员|关闭)).*emby` | 包含 emby 但排除已失效的消息 |

---

## 🛠️ 部署指南 (Docker)

### 1. 准备参数
* **API_ID & API_HASH**: 访问 [my.telegram.org](https://my.telegram.org) 申请。
* **BOT_TOKEN**: 通过 [@BotFather](https://t.me/BotFather) 申请。
* **TARGET_CHANNEL**: 接收通知的频道 ID（如 `-100123456789`）。
* **ADMIN_ID**: 你个人的 Telegram 用户 ID（用于鉴权）。

### 2. 编写配置
修改 `docker-compose.yml` 环境变量部分：

```yaml
version: '3.8'
services:
  emby-monitor:
    build: .
    container_name: emby_monitor
    restart: unless-stopped
    environment:
      - API_ID=你的API_ID
      - API_HASH=你的API_HASH
      - BOT_TOKEN=你的Bot_Token
      - TARGET_CHANNEL=-100xxxxxxxxxx
      - ADMIN_ID=123456789
      - PYTHONUNBUFFERED=1
    volumes:
      - ./:/app
```
### 3. 首次启动与登录 (❗ 交互模式)
由于初次登录需要输入手机号和验证码，必须使用交互式终端运行：

执行登录命令：

Bash
docker-compose run --rm -it emby-monitor
完成验证： 按照提示输入手机号（如 +86138...）及 Telegram 验证码。

确认成功： 看到 🎉 系统运行中... 提示后，按 Ctrl+C 退出即可。

### 4. 正式后台运行 (✅ 生产模式)
当凭证文件 .session 生成后，即可一键进入后台常驻运行：

执行启动命令：

Bash
docker-compose up -d
查看日志状态： 使用 docker-compose logs -f 确认运行正常。

🎮 使用方法
管理控制台：向你的官方 Bot 发送 /start 即可唤出图形化面板。

快捷添加：在其他群组看到目标消息，直接转发给你的 Bot，根据弹窗提示一键监控或拉黑。

黑名单保护：系统自动校验“转发者”与“原作者”，若命中黑名单则直接拦截。

⚠️ 安全警告：本系统已做严格的 ID 隔离。仅限环境变量中设置的 ADMIN_ID 用户有权操作。其他人发送指令或点击按钮将不会得到任何响应。
