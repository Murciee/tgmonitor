# Telegram Monitor (Userbot + Bot 双端交互系统)

<img width="400" height="302" alt="image" src="https://github.com/user-attachments/assets/e3c15bc1-55c1-4f83-8d55-876e2c85973f" />

<img width="324" height="166" alt="image" src="https://github.com/user-attachments/assets/5c7464f6-8bcb-481e-bd78-04335012a01b" />

这是一个专为 Telegram 打造的高级群组关键字监控系统。它通过 Userbot 隐形监听指定群组，当触发设定好的正则/关键词时，自动将消息**原生转发**到你的私人频道。

集成官方 Bot 作为**可视化控制台**，你可以直接在手机上点击按钮管理所有规则，无需接触代码或重启服务。

---

## ✨ 核心特性

* **🚀 纯图形化管理**：通过内联按钮（Inline Keyboard）管理配置，支持分页显示。
* **🖱️ 动态点击删除**：监控群、关键词、黑名单均生成列表按钮，点一下即可精准删除。
* **🧲 消息抓取解析**：直接将消息**转发**给控制 Bot，Bot 自动解析 ID 并弹出快捷添加面板。
* **⏸️ 全局状态控制**：主菜单一键切换“运行中/已暂停”，灵活控制监控开关。
* **🛡️ 完美原生转发**：采用 `Forward` 机制，100% 保留原消息的按钮、特效字体及 Emoji。
* **💾 数据持久化**：所有配置实时保存至 `config.json`，改完即生效，Docker 重启数据不丢失。

---

## 🔎 常见正则表达式示例

在管理面板中点击“添加正则词”时，可以直接参考以下常用模式（`(?i)` 表示忽略大小写）：

| 匹配目标 | 正则表达式示例 | 说明 |
| :--- | :--- | :--- |
| **优惠活动综合监控** | `(?i)(优惠\|折扣\|促销\|限时\|活动).*(开始\|上线\|开放\|开抢)` | 匹配活动关键词及相关动作 |
| **通用优惠码** | `(?i)(coupon\|promo\s?code\|折扣码\|优惠码\|兑换码)` | 抓取各类含“码”的信息 |
| **英文活动提醒** | `(?i)(sale\|deal\|limited time\|flash sale)` | 监控英文频道中的促销动态 |
| **私有加群链接** | `https://t\.me/\+` | 捕捉私有群组邀请链接 |
| **排除负面词汇** | `^(?!.*(结束\|过期\|抢完)).*(优惠\|活动)` | 包含优惠/活动信息，但排除失效消息 |

---

## 🛠️ 部署指南 (Docker)

### 1. 准备参数
* **API_ID & API_HASH**: 访问 https://my.telegram.org 申请。
* **BOT_TOKEN**: 通过 @BotFather 申请。
* **TARGET_CHANNEL**: 接收通知的频道 ID（如 `-100123456789`）。
* **ADMIN_ID**: 你个人的用户 ID（用于鉴权）。

### 2. 编写 Docker Compose
在项目目录下创建 `docker-compose.yml` 并修改环境变量：

    version: '3.8'
    services:
      emby-monitor:
        build: .
        container_name: tg_monitor
        restart: unless-stopped
        environment:
          - API_ID=12345
          - API_HASH=your_hash
          - BOT_TOKEN=your_token
          - TARGET_CHANNEL=-100123456
          - ADMIN_ID=987654321
          - PYTHONUNBUFFERED=1
        volumes:
          - ./:/app

### 3. 首次启动与登录 (❗ 交互模式)
由于初次登录需要输入手机号和验证码，必须使用交互式终端运行。

执行登录命令：

    docker-compose run --rm -it tg-monitor

登录步骤说明：
1. 按照终端提示输入手机号（需带国家区号，如 `+86138...`）。
2. 输入 Telegram 官方下发的验证码（如开启了两步验证也需输入密码）。
3. 看到 `🎉 系统运行中...` 提示后，按 `Ctrl+C` 退出即可。

### 4. 正式后台运行 (✅ 生产模式)
当凭证文件 `user_session.session` 生成后，即可进入后台常驻运行。

执行启动命令：

    docker-compose up -d

状态检查：
* 使用 `docker-compose logs -f` 确认运行日志无报错。
* 确认目录下已生成必要的 `.session` 凭证文件。

---

## 🎮 使用方法

1. **管理控制台**：向你的官方 Bot 发送 `/start` 即可唤出图形化面板。
2. **快捷添加**：在其他群组看到目标消息，直接**转发**给你的 Bot，根据弹窗提示一键监控或拉黑。
3. **黑名单保护**：系统自动校验“转发者”与“原作者”，若命中黑名单则直接拦截。

---

> **⚠️ 安全警告**：本系统已做严格的 ID 隔离。仅限环境变量中设置的 `ADMIN_ID` 用户有权操作。其他人发送指令或点击按钮将不会得到任何响应。
