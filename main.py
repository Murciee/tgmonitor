import os
import json
import re
import logging
import asyncio
import math
from telethon import TelegramClient, events, Button, utils

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s', level=logging.INFO)

# --- 环境变量配置 ---
API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
BOT_TOKEN = os.environ.get('BOT_TOKEN')
TARGET_CHANNEL = int(os.environ.get('TARGET_CHANNEL'))
ADMIN_ID = int(os.environ.get('ADMIN_ID'))

CONFIG_FILE = 'config.json'

# --- 🚀 高性能内存缓存与异步锁 ---
GLOBAL_CONFIG = {}
COMPILED_REGEXES = []
CONFIG_LOCK = asyncio.Lock()

async def load_config_async():
    global GLOBAL_CONFIG, COMPILED_REGEXES
    async with CONFIG_LOCK:
        if not os.path.exists(CONFIG_FILE):
            GLOBAL_CONFIG = {
                "status": "running",
                "notify_dm": True,  # 新增：默认开启私聊通知
                "groups": [],
                "keywords": [r"(?i)emby.*(注册|邀请|开注)"],
                "blacklist": [],
                "group_names": {},
                "user_names": {}
            }
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(GLOBAL_CONFIG, f, ensure_ascii=False, indent=4)
        else:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                GLOBAL_CONFIG = json.load(f)
                # 兼容老数据结构
                if "status" not in GLOBAL_CONFIG: GLOBAL_CONFIG["status"] = "running"
                if "notify_dm" not in GLOBAL_CONFIG: GLOBAL_CONFIG["notify_dm"] = True
                if "group_names" not in GLOBAL_CONFIG: GLOBAL_CONFIG["group_names"] = {}
                if "user_names" not in GLOBAL_CONFIG: GLOBAL_CONFIG["user_names"] = {}

        # 启动时预编译所有正则，榨干 CPU 性能
        COMPILED_REGEXES.clear()
        for kw in GLOBAL_CONFIG.get("keywords", []):
            try:
                COMPILED_REGEXES.append(re.compile(kw))
            except Exception as e:
                logging.error(f"正则预编译异常 {kw}: {e}")

async def save_config_async():
    global COMPILED_REGEXES
    async with CONFIG_LOCK:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(GLOBAL_CONFIG, f, ensure_ascii=False, indent=4)
            
        # 配置文件保存后，重新编译正则对象
        COMPILED_REGEXES.clear()
        for kw in GLOBAL_CONFIG.get("keywords", []):
            try:
                COMPILED_REGEXES.append(re.compile(kw))
            except Exception as e:
                logging.error(f"正则重新编译异常 {kw}: {e}")

user_client = TelegramClient('user_session', API_ID, API_HASH)
bot_client = TelegramClient('bot_session', API_ID, API_HASH)

WAITING_STATE = {}

# ==========================================
#         第一部分：Bot 交互界面与逻辑
# ==========================================

def build_main_menu(config):
    status_icon = "🟢 运行中" if config['status'] == 'running' else "🔴 已暂停"
    notify_icon = "🔔 开启" if config.get('notify_dm', True) else "🔕 关闭"
    
    text = f"⚙️ **Emby 监控管理控制台**\n\n系统状态: **{status_icon}**\n私聊提醒: **{notify_icon}**\n请选择要管理的模块："
    buttons = [
        [Button.inline(f"监控状态: {status_icon}", b"toggle_status"),
         Button.inline(f"私聊提醒: {notify_icon}", b"toggle_notify")],
        [Button.inline(f"📁 群组管理 ({len(config['groups'])})", b"menu_grp"),
         Button.inline(f"🏷️ 关键词管理 ({len(config['keywords'])})", b"menu_key")],
        [Button.inline(f"🚫 黑名单管理 ({len(config['blacklist'])})", b"menu_blk"),
         Button.inline("📊 查看完整配置", b"view_all")]
    ]
    return text, buttons

def build_sub_menu(menu_type):
    titles = {'grp': '📁 **群组管理**', 'key': '🏷️ **关键词/正则管理**', 'blk': '🚫 **黑名单管理**'}
    text = f"{titles[menu_type]}\n请选择操作："
    buttons = [
        [Button.inline("➕ 添加新项", f"prompt_add_{menu_type}".encode()), 
         Button.inline("➖ 点击删除", f"list_{menu_type}_del_0".encode())],
        [Button.inline("📝 点击修改", f"list_{menu_type}_edit_0".encode())],
        [Button.inline("🔙 返回主菜单", b"menu_main")]
    ]
    return text, buttons

def build_item_list(config, list_type, action, page=0):
    items_per_page = 8
    action_text = "删除" if action == 'del' else "修改"
    
    if list_type == 'grp':
        data_list = config['groups']
        title = f"📁 点击群组 {action_text}："
    elif list_type == 'key':
        data_list = config['keywords']
        title = f"🏷️ 点击关键词/正则 {action_text}："
    else:
        data_list = config['blacklist']
        title = f"🚫 点击黑名单 {action_text}："

    total_pages = math.ceil(len(data_list) / items_per_page) or 1
    page = min(max(0, page), total_pages - 1)
    
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_items = data_list[start_idx:end_idx]

    buttons = []
    for i, item in enumerate(page_items):
        actual_idx = start_idx + i
        icon = '❌' if action == 'del' else '✏️'
        
        if list_type == 'grp':
            name = config.get('group_names', {}).get(str(item), "未命名群组")
            raw_text = f"{name} ({item})"
        elif list_type == 'blk':
            name = config.get('user_names', {}).get(str(item), "未知用户")
            raw_text = f"{name} ({item})"
        else:
            raw_text = str(item)
            
        display_text = f"{icon} {raw_text[:35]}..." if len(raw_text) > 35 else f"{icon} {raw_text}"
        buttons.append([Button.inline(display_text, f"{action}_{list_type}_{actual_idx}".encode())])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline("⬅️ 上一页", f"list_{list_type}_{action}_{page-1}".encode()))
    if page < total_pages - 1:
        nav_buttons.append(Button.inline("下一页 ➡️", f"list_{list_type}_{action}_{page+1}".encode()))
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([Button.inline("🔙 返回上一级", f"menu_{list_type}".encode())])
    return f"{title}\n(第 {page+1}/{total_pages} 页)", buttons


@bot_client.on(events.NewMessage(from_users=ADMIN_ID))
async def bot_message_handler(event):
    if event.text.startswith('/start'):
        WAITING_STATE[ADMIN_ID] = None
        text, buttons = build_main_menu(GLOBAL_CONFIG)
        await event.reply(text, buttons=buttons)
        return

    if event.fwd_from:
        WAITING_STATE[ADMIN_ID] = None
        chat_id, user_id = None, None
        if event.fwd_from.saved_from_peer:
            chat_id = utils.get_peer_id(event.fwd_from.saved_from_peer)
        if event.fwd_from.from_id:
            user_id = utils.get_peer_id(event.fwd_from.from_id)
            
        if chat_id or user_id:
            text = "🤖 **解析转发消息成功**\n请选择快捷操作："
            buttons = []
            if chat_id: buttons.append([Button.inline(f"➕ 将群组 {chat_id} 加入监控", f"quick_grp_{chat_id}".encode())])
            if user_id: buttons.append([Button.inline(f"🚫 将用户 {user_id} 加入黑名单", f"quick_blk_{user_id}".encode())])
            buttons.append([Button.inline("❌ 取消", b"menu_main")])
            await event.reply(text, buttons=buttons)
            return

    state = WAITING_STATE.get(ADMIN_ID)
    if not state: return
    if event.text.startswith('/'): return
    
    text = event.text.strip()
    if text.lower() == '/cancel':
        WAITING_STATE[ADMIN_ID] = None
        t, b = build_main_menu(GLOBAL_CONFIG)
        await event.reply("✅ 操作已取消。", buttons=b)
        return

    config = GLOBAL_CONFIG
    try:
        is_duplicate = False
        parts = text.split(maxsplit=1)
        val_str = parts[0]
        remark = parts[1] if len(parts) > 1 else None
        
        if state == 'add_grp':
            val = int(val_str)
            if val in config['groups']: is_duplicate = True
            else: 
                config['groups'].append(val)
                config.setdefault('group_names', {})[str(val)] = remark or "未命名群组"
        elif state == 'add_blk':
            val = int(val_str)
            if val in config['blacklist']: is_duplicate = True
            else: 
                config['blacklist'].append(val)
                config.setdefault('user_names', {})[str(val)] = remark or "未知用户"
        elif state == 'add_key':
            if text in config['keywords']: is_duplicate = True
            else: config['keywords'].append(text)
            
        elif state.startswith('doedit_'):
            state_parts = state.split('_')
            list_type, idx = state_parts[1], int(state_parts[2])
            target_list = config['groups'] if list_type == 'grp' else (config['keywords'] if list_type == 'key' else config['blacklist'])
            
            if list_type in ['grp', 'blk']:
                val = int(val_str)
                if val in target_list and target_list.index(val) != idx: is_duplicate = True
                else: 
                    target_list[idx] = val
                    if list_type == 'grp' and remark: config.setdefault('group_names', {})[str(val)] = remark
                    if list_type == 'blk' and remark: config.setdefault('user_names', {})[str(val)] = remark
            else:
                if text in target_list and target_list.index(text) != idx: is_duplicate = True
                else: target_list[idx] = text

        if is_duplicate:
            WAITING_STATE[ADMIN_ID] = None
            t, b = build_main_menu(config)
            await event.reply(f"⚠️ 操作失败：`{val_str}` 已存在于列表中，请勿重复添加/修改！", buttons=b)
            return
            
        await save_config_async()
        WAITING_STATE[ADMIN_ID] = None
        t, b = build_main_menu(config)
        success_msg = "✅ 修改成功！" if state.startswith('doedit_') else f"✅ 添加成功：{text}"
        await event.reply(success_msg, buttons=b)
        
    except ValueError:
        await event.reply("❌ 格式错误：ID必须是纯数字！请重新输入或发 /cancel 取消。")


@bot_client.on(events.CallbackQuery())
async def bot_callback(event):
    if event.sender_id != ADMIN_ID:
        await event.answer("❌ 无权限", alert=True)
        return

    data = event.data.decode('utf-8')
    config = GLOBAL_CONFIG
    WAITING_STATE[ADMIN_ID] = None

    if data == 'menu_main':
        t, b = build_main_menu(config)
        await event.edit(t, buttons=b)
    elif data in ['menu_grp', 'menu_key', 'menu_blk']:
        t, b = build_sub_menu(data.split('_')[1])
        await event.edit(t, buttons=b)
    
    elif data == 'toggle_status':
        config['status'] = 'paused' if config['status'] == 'running' else 'running'
        await save_config_async()
        t, b = build_main_menu(config)
        await event.edit(t, buttons=b)

    elif data == 'toggle_notify':
        config['notify_dm'] = not config.get('notify_dm', True)
        await save_config_async()
        t, b = build_main_menu(config)
        await event.edit(t, buttons=b)
        
    elif data == 'view_all':
        grp_str = ", ".join([f"{config.get('group_names', {}).get(str(x), '未命名')}({x})" for x in config['groups']])
        blk_str = ", ".join([f"{config.get('user_names', {}).get(str(x), '未知')}({x})" for x in config['blacklist']])
        
        text = (
            f"📊 **完整配置概览**\n\n"
            f"**状态:** {config['status']} (私聊提醒: {'开启' if config.get('notify_dm', True) else '关闭'})\n"
            f"**群组:** `{grp_str}`\n"
            f"**正则:** `{config['keywords']}`\n"
            f"**黑名单:** `{blk_str}`"
        )
        await event.answer("已在聊天中输出全部配置")
        await event.reply(text)

    elif data.startswith('prompt_add_'):
        m_type = data.split('_')[2]
        WAITING_STATE[ADMIN_ID] = f'add_{m_type}'
        tips = {
            'grp': '群组ID (支持直接打备注，例如: `-100123 测试群`)', 
            'key': '关键词/正则', 
            'blk': '用户ID (支持直接打备注，例如: `12345 骗子`)'
        }
        await event.reply(f"👉 请发送要添加的 **{tips[m_type]}**\n_发送 /cancel 取消_")

    elif data.startswith('quick_'):
        parts = data.split('_')
        action, val = parts[1], int(parts[2])
        
        if action == 'grp':
            if val in config['groups']:
                await event.edit(f"⚠️ 群组 `{val}` 已经在监控列表中了！")
            else:
                config['groups'].append(val)
                config.setdefault('group_names', {})[str(val)] = "未命名群组"
                await save_config_async()
                await event.edit(f"✅ 已成功将群组 `{val}` 加入监控！")
                
        elif action == 'blk':
            if val in config['blacklist']:
                await event.edit(f"⚠️ 用户 `{val}` 已经在黑名单中了！")
            else:
                config['blacklist'].append(val)
                config.setdefault('user_names', {})[str(val)] = "未知用户"
                await save_config_async()
                await event.edit(f"✅ 已成功将用户 `{val}` 加入黑名单！")

    elif data.startswith('list_'):
        parts = data.split('_')
        list_type, action, page = parts[1], parts[2], int(parts[3])
        t, b = build_item_list(config, list_type, action, page)
        await event.edit(t, buttons=b)

    elif data.startswith('del_'):
        parts = data.split('_')
        list_type, idx = parts[1], int(parts[2])
        target_list = config['groups'] if list_type == 'grp' else (config['keywords'] if list_type == 'key' else config['blacklist'])
        
        if 0 <= idx < len(target_list):
            deleted_item = target_list.pop(idx)
            if list_type == 'grp' and str(deleted_item) in config.get('group_names', {}):
                del config['group_names'][str(deleted_item)]
            if list_type == 'blk' and str(deleted_item) in config.get('user_names', {}):
                del config['user_names'][str(deleted_item)]
            await save_config_async()
            await event.answer(f"已删除: {deleted_item}")
        
        t, b = build_item_list(config, list_type, 'del', 0)
        await event.edit(t, buttons=b)

    elif data.startswith('edit_'):
        parts = data.split('_')
        list_type, idx = parts[1], int(parts[2])
        target_list = config['groups'] if list_type == 'grp' else (config['keywords'] if list_type == 'key' else config['blacklist'])
        
        if 0 <= idx < len(target_list):
            old_val = target_list[idx]
            WAITING_STATE[ADMIN_ID] = f"doedit_{list_type}_{idx}"
            await event.reply(f"👉 正在修改：\n`{old_val}`\n\n请直接发送修改后的新内容 (可带空格备注)：\n_发送 /cancel 取消_")

# ==========================================
#         第二部分：Userbot 监听端逻辑
# ==========================================

@user_client.on(events.NewMessage)
async def user_handler(event):
    # 极速内存读取，0磁盘消耗
    config = GLOBAL_CONFIG
    
    if config.get('status', 'running') != 'running': return
    
    chat_id = event.chat_id
    if chat_id not in config['groups']: return

    sender_id = event.sender_id
    fwd_from_id = None
    if event.fwd_from:
        if event.fwd_from.from_id:
            if hasattr(event.fwd_from.from_id, 'user_id'): fwd_from_id = event.fwd_from.from_id.user_id
            elif hasattr(event.fwd_from.from_id, 'channel_id'): fwd_from_id = event.fwd_from.from_id.channel_id

    blacklist_strs = [str(x).replace('-100', '') for x in config['blacklist']]
    def is_blocked(uid): return str(uid).replace('-100', '') in blacklist_strs if uid else False

    if is_blocked(sender_id) or is_blocked(fwd_from_id): return

    text = event.message.text or ""
    matched = False
    
    # 极速匹配：使用预编译的正则引擎
    for regex in COMPILED_REGEXES:
        if regex.search(text):
            matched = True
            break
            
    if matched:
        chat = await event.get_chat()
        sender = await event.get_sender()
        
        sender_name = "Unknown"
        if sender:
            if hasattr(sender, 'first_name'): 
                first = getattr(sender, 'first_name', None) or ''
                last = getattr(sender, 'last_name', None) or ''
                sender_name = f"{first} {last}".strip()
            elif hasattr(sender, 'title'): 
                sender_name = sender.title

        fwd_info = ""
        if event.fwd_from:
            fwd_name = "未知"
            if event.fwd_from.from_name: 
                fwd_name = event.fwd_from.from_name
            elif event.fwd_from.from_id:
                try:
                    fwd_entity = await user_client.get_entity(event.fwd_from.from_id)
                    if hasattr(fwd_entity, 'title') and fwd_entity.title:
                        fwd_name = fwd_entity.title
                    else:
                        first = getattr(fwd_entity, 'first_name', None) or ''
                        last = getattr(fwd_entity, 'last_name', None) or ''
                        fwd_name = f"{first} {last}".strip()
                except Exception as e: 
                    fwd_name = f"ID: {fwd_from_id}"
            fwd_info = f"**直接来源:** {fwd_name}\n"

        source_name = getattr(chat, 'title', "Unknown Group")
        chat_id_str = str(chat_id)
        
        # 智能自学习机制
        needs_save = False
        if config.get('group_names', {}).get(chat_id_str) != source_name:
            config.setdefault('group_names', {})[chat_id_str] = source_name
            needs_save = True
            
        if sender_id and sender_name != "Unknown":
            sender_id_str = str(sender_id)
            if config.get('user_names', {}).get(sender_id_str) != sender_name:
                config.setdefault('user_names', {})[sender_id_str] = sender_name
                needs_save = True
                
        if needs_save: await save_config_async()

        msg_link = f"https://t.me/{chat.username}/{event.id}" if getattr(chat, 'username', None) else f"https://t.me/c/{chat_id_str.replace('-100', '')}/{event.id}"
        
        has_buttons = event.message.reply_markup is not None
        has_real_media = False
        if event.message.media:
            if event.message.media.__class__.__name__ != 'MessageMediaWebPage':
                has_real_media = True

        needs_native_forward = has_buttons or has_real_media

        source_info = (
            f"**来源群组:** {source_name} (`{chat_id_str}`)\n"
            f"**发送用户:** {sender_name} (`{sender_id or 'N/A'}`)\n"
            f"{fwd_info}"
            f"**直达链接:** [点击跳转]({msg_link})"
        )
        
        try:
            if needs_native_forward:
                log_header = f"🎯 **来源信息**\n{source_info}"
                await user_client.send_message(TARGET_CHANNEL, log_header, link_preview=False)
                fwd_msg = await event.forward_to(TARGET_CHANNEL)
                logging.info(f"分流发送 (带按钮/媒体): {source_name}")
            else:
                final_text = f"{text}\n\n┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈┈\n{source_info}"
                fwd_msg = await user_client.send_message(TARGET_CHANNEL, final_text, link_preview=False)
                logging.info(f"极速合并发送 (纯文本): {source_name}")
                
            # --- 受控的私聊推送引擎 ---
            if config.get('notify_dm', True):
                channel_link = str(TARGET_CHANNEL).replace('-100', '')
                jump_url = f"https://t.me/c/{channel_link}/{fwd_msg.id}"
                
                await bot_client.send_message(
                    ADMIN_ID, 
                    f"🛎 **监控触发！** 抓到来自 `{source_name}` 的新消息。\n[👉 点击前往频道查看]({jump_url})", 
                    link_preview=False
                )
            
        except Exception as e:
            logging.error(f"发送或推送失败: {e}")

# --- 启动逻辑 ---
async def main():
    print("--- 正在初始化全局内存与配置 ---")
    await load_config_async()
    print("✅ 预加载完成！")
    
    print("正在连接交互 Bot...")
    await bot_client.start(bot_token=BOT_TOKEN)
    print("✅ 交互 Bot 启动成功！\n🎉 系统运行中... 请前往你的 Bot 发送 /start 开始管理。")
    await asyncio.gather(user_client.run_until_disconnected(), bot_client.run_until_disconnected())

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    print("--- 检查 Userbot 凭证 ---")
    user_client.start()
    print("✅ Userbot 检查通过！\n")
    loop.run_until_complete(main())
