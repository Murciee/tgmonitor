import os
import json
import re
import logging
import asyncio
from telethon import TelegramClient, events, Button
from telethon.tl.types import User

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)

# --- 环境变量配置 ---
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')        # 你从 BotFather 申请的 Token
TARGET_CHANNEL = int(os.environ.get('TARGET_CHANNEL')) 
ADMIN_ID = int(os.environ.get('ADMIN_ID'))     # 你的个人TG ID (仅允许你操作Bot)

CONFIG_FILE = 'config.json'

# --- 配置文件管理 ---
def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "groups": [],
            "keywords": [r"(?i)emby.*(注册|邀请|开注)"],
            "blacklist": []
        }
        save_config(default_config)
        return default_config
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

# --- 初始化双客户端 ---
# user_client 用于监听群组消息
user_client = TelegramClient('user_session', API_ID, API_HASH)
# bot_client 用于提供交互界面
bot_client = TelegramClient('bot_session', API_ID, API_HASH)

# 用于记录 Bot 交互状态 (等待用户输入什么)
WAITING_STATE = {}

# ==========================================
#         第一部分：Bot 管理端逻辑 (交互UI)
# ==========================================

async def send_main_menu(chat_id):
    """发送主菜单面板"""
    buttons = [
        [Button.inline("➕ 添加监控群", b"add_group"), Button.inline("➖ 移除监控群", b"del_group")],
        [Button.inline("➕ 添加正则词", b"add_keyword"), Button.inline("➖ 移除正则词", b"del_keyword")],
        [Button.inline("➕ 拉黑用户", b"add_black"), Button.inline("➖ 移出黑名单", b"del_black")],
        [Button.inline("📊 查看当前所有配置", b"view_config")]
    ]
    await bot_client.send_message(chat_id, "⚙️ **Emby 监控管理面板**\n请选择你要进行的操作：", buttons=buttons)

@bot_client.on(events.NewMessage(from_users=ADMIN_ID, pattern='/start'))
async def bot_start(event):
    WAITING_STATE[ADMIN_ID] = None
    await send_main_menu(event.chat_id)

@bot_client.on(events.CallbackQuery(from_users=ADMIN_ID))
async def bot_callback(event):
    """处理按钮点击事件"""
    data = event.data.decode('utf-8')
    
    if data == 'view_config':
        config = load_config()
        text = (
            f"📊 **当前运行配置**\n\n"
            f"**监控群组 ({len(config['groups'])}):**\n`{config['groups']}`\n\n"
            f"**匹配正则 ({len(config['keywords'])}):**\n`{config['keywords']}`\n\n"
            f"**黑名单UID ({len(config['blacklist'])}):**\n`{config['blacklist']}`"
        )
        await event.reply(text)
        return

    # 记录用户的下一步输入意图
    WAITING_STATE[ADMIN_ID] = data
    
    prompts = {
        'add_group': "👉 请发送要**添加**的群组ID（例如: -10012345678）\n_提示: 可发送 /cancel 取消_",
        'del_group': "👉 请发送要**移除**的群组ID\n_提示: 可发送 /cancel 取消_",
        'add_keyword': "👉 请发送要**添加**的正则或关键词（例如: `(?i)emby`）\n_提示: 可发送 /cancel 取消_",
        'del_keyword': "👉 请发送要**移除**的正则或关键词\n_提示: 可发送 /cancel 取消_",
        'add_black': "👉 请发送要**拉黑**的用户ID\n_提示: 可发送 /cancel 取消_",
        'del_black': "👉 请发送要**解封**的用户ID\n_提示: 可发送 /cancel 取消_"
    }
    
    if data in prompts:
        await event.reply(prompts[data])

@bot_client.on(events.NewMessage(from_users=ADMIN_ID))
async def bot_text_input(event):
    """处理用户根据提示输入的文本"""
    if event.text.startswith('/'): return # 忽略命令
    
    state = WAITING_STATE.get(ADMIN_ID)
    if not state: return # 如果不在等待输入状态，则不理会

    text = event.text.strip()
    if text.lower() == '/cancel':
        WAITING_STATE[ADMIN_ID] = None
        await event.reply("✅ 操作已取消。")
        await send_main_menu(event.chat_id)
        return

    config = load_config()
    success_msg = ""

    try:
        if state in ['add_group', 'del_group', 'add_black', 'del_black']:
            val = int(text) # 尝试转为数字
            if state == 'add_group':
                if val not in config['groups']: config['groups'].append(val)
                success_msg = f"✅ 成功添加监控群组: {val}"
            elif state == 'del_group':
                if val in config['groups']: config['groups'].remove(val)
                success_msg = f"✅ 成功移除监控群组: {val}"
            elif state == 'add_black':
                if val not in config['blacklist']: config['blacklist'].append(val)
                success_msg = f"✅ 成功拉黑用户: {val}"
            elif state == 'del_black':
                if val in config['blacklist']: config['blacklist'].remove(val)
                success_msg = f"✅ 成功移出黑名单: {val}"
                
        elif state == 'add_keyword':
            if text not in config['keywords']: config['keywords'].append(text)
            success_msg = f"✅ 成功添加关键词/正则: `{text}`"
            
        elif state == 'del_keyword':
            if text in config['keywords']: config['keywords'].remove(text)
            success_msg = f"✅ 成功移除关键词/正则: `{text}`"

        save_config(config)
        WAITING_STATE[ADMIN_ID] = None # 重置状态
        await event.reply(success_msg)
        await send_main_menu(event.chat_id)

    except ValueError:
        await event.reply("❌ 输入格式错误！群组ID和用户ID必须是数字，请重新输入或发送 /cancel 取消。")


# ==========================================
#         第二部分：Userbot 监听端逻辑
# ==========================================

@user_client.on(events.NewMessage)
async def user_handler(event):
    # 动态加载最新配置
    config = load_config()
    
    # 1. 检查是否在监控群组中
    chat_id = event.chat_id
    if chat_id not in config['groups']:
        return

    sender = await event.get_sender()
    chat = await event.get_chat()
    
    # 2. 检查黑名单
    if sender and sender.id in config['blacklist']:
        return

    text = event.message.text or ""
    
    # 3. 正则匹配
    matched = False
    for regex in config['keywords']:
        try:
            if re.search(regex, text):
                matched = True
                break
        except Exception as e:
            logging.error(f"正则错误 {regex}: {e}")
            
    if matched:
        # 4. 格式化并转发
        source_name = chat.title if hasattr(chat, 'title') else "Unknown Group"
        sender_name = "Unknown"
        if sender and isinstance(sender, User):
            sender_name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        
        log_text = (
            f"**📢 监控命中**\n"
            f"**来源群组:** {source_name} (`{chat_id}`)\n"
            f"**发送用户:** {sender_name} (`{sender.id if sender else 'N/A'}`)\n"
            f"**直达链接:** [点击跳转](https://t.me/c/{str(chat_id).replace('-100','')}/{event.message.id})\n"
            f"---\n"
            f"{text}"
        )
        
        try:
            await user_client.send_message(TARGET_CHANNEL, log_text, link_preview=False)
            logging.info(f"成功转发一条消息来自: {source_name}")
        except Exception as e:
            logging.error(f"转发失败: {e}")

# --- 启动逻辑 ---
async def main():
    print("正在启动系统...")
    # 启动 Userbot (如果没登录过会要求输入验证码)
    await user_client.start()
    print("✅ Userbot 启动成功！")
    
    # 启动 Bot
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ 交互 Bot 启动成功！")
    
    print("🎉 系统运行中... 请前往你的 Bot 发送 /start 开始管理。")
    await asyncio.gather(
        user_client.run_until_disconnected(),
        bot_client.run_until_disconnected()
    )

if __name__ == '__main__':
    asyncio.run(main())
