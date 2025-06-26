"""管理員處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, Product, Category, Order, User, OrderItem
from config import ADMIN_IDS
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import os
import sys

# 對話狀態
WAITING_API_KEY = 1
WAITING_NEW_ADMIN = 2
WAITING_BROADCAST = 3

def check_admin(user_id):
    """檢查是否為管理員"""
    return user_id in ADMIN_IDS

def add_product_command(update: Update, context: CallbackContext):
    """新增商品指令處理"""
    if not check_admin(update.effective_user.id):
        update.message.reply_text("❌ 您沒有權限使用此功能")
        return
    
    # /addproduct 商品名稱 價格 庫存 分類
    if len(context.args) < 4:
        update.message.reply_text(
            "使用方式：\n"
            "/addproduct 商品名稱 價格 庫存 分類\n\n"
            "範例：\n"
            "/addproduct 礦泉水 30 100 海水"
        )
        return
    
    try:
        name = context.args[0]
        price = float(context.args[1])
        stock = int(context.args[2])
        category_name = context.args[3]
        
        session = SessionLocal()
        
        # 查找分類
        category = session.query(Category).filter_by(name=category_name).first()
        if not category:
            update.message.reply_text(f"❌ 找不到分類：{category_name}")
            session.close()
            return
        
        # 創建商品
        product = Product(
            name=name,
            price=price,
            stock=stock,
            category=f"{category.icon} {category.name}" if category.icon else category.name,
            category_id=category.id
        )
        
        session.add(product)
        session.commit()
        
        update.message.reply_text(
            f"✅ 商品新增成功！\n\n"
            f"名稱：{name}\n"
            f"價格：${price}\n"
            f"庫存：{stock}\n"
            f"分類：{category.name}"
        )
        
        session.close()
        
    except (ValueError, IndexError) as e:
        update.message.reply_text(f"❌ 輸入格式錯誤：{str(e)}")

def show_all_orders(update: Update, context: CallbackContext):
    """顯示所有訂單"""
    if not check_admin(update.effective_user.id):
        update.message.reply_text("❌ 您沒有權限使用此功能")
        return
    
    session = SessionLocal()
    orders = session.query(Order).order_by(Order.created_at.desc()).limit(20).all()
    
    if not orders:
        update.message.reply_text("📋 目前沒有訂單")
        session.close()
        return
    
    text = "📋 **所有訂單**\n\n"
    
    for order in orders[:10]:
        text += f"訂單號: `{order.order_no}`\n"
        text += f"用戶: {order.user_id}\n"
        text += f"狀態: **{order.status}**\n"
        text += f"門市: {order.store_code}\n"
        
        # 計算總價
        total = 0
        for item in order.items:
            total += item.price * item.quantity
        
        text += f"金額: ${total}\n"
        text += "─" * 20 + "\n"
    
    if len(orders) > 10:
        text += f"\n📌 共 {len(orders)} 筆訂單，僅顯示最新 10 筆"
    
    keyboard = [[
        InlineKeyboardButton("📤 匯出訂單", callback_data="EXPORT_ORDERS")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()



def admin_menu(update: Update, context: CallbackContext):
    """管理員主選單"""
    from utils.keyboards import get_admin_menu_keyboard
    
    if update.callback_query:
        query = update.callback_query
        query.answer()
        keyboard = get_admin_menu_keyboard()
        query.message.edit_text(
            "🔧 **管理員控制台**\n\n請選擇功能：",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    else:
        keyboard = get_admin_menu_keyboard()
        update.message.reply_text(
            "🔧 **管理員控制台**\n\n請選擇功能：",
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

def start_add_product(update):
    """開始新增商品流程"""
    if update.callback_query:
        query = update.callback_query
        query.answer()
        query.message.reply_text("請使用以下格式新增商品：\n\n`商品名稱,價格,庫存,分類名稱`\n\n例如：金魚,100,10,海水", parse_mode='Markdown')
    else:
        update.message.reply_text("請使用以下格式新增商品：\n\n`商品名稱,價格,庫存,分類名稱`\n\n例如：金魚,100,10,海水", parse_mode='Markdown')

def handle_admin_text(update: Update, context: CallbackContext):
    """處理管理員文字輸入"""
    text = update.message.text
    
    # 檢查是否正在編輯商品
    if context.user_data.get('editing_product'):
        from handlers.product_management import handle_product_edit
        handle_product_edit(update, context)
        return
    
    # 檢查是否正在新增分類
    if context.user_data.get('adding_category'):
        from handlers.category_management import handle_category_add
        handle_category_add(update, context)
        return
    
    # 檢查是否正在編輯分類
    if context.user_data.get('editing_category'):
        from handlers.category_management import handle_category_edit
        handle_category_edit(update, context)
        return
    
    # 檢查是否正在輸入出貨單號
    if context.user_data.get('shipping_order'):
        from handlers.order_management import handle_shipping_number
        handle_shipping_number(update, context)
        return
    
    # 檢查是否正在發送客戶通知
    if context.user_data.get('notify_order'):
        from handlers.order_management import handle_customer_notification
        handle_customer_notification(update, context)
        return
    
    # 處理新增商品
    if ',' in text:
        parts = text.split(',')
        if len(parts) == 4:
            try:
                name = parts[0].strip()
                price = float(parts[1].strip())
                stock = int(parts[2].strip())
                category_name = parts[3].strip()
                
                session = SessionLocal()
                
                # 查找或創建分類
                category = session.query(Category).filter_by(name=category_name).first()
                if not category:
                    category = Category(name=category_name, icon='📦', order=0)
                    session.add(category)
                    session.flush()
                
                # 創建商品
                product = Product(
                    name=name,
                    price=price,
                    stock=stock,
                    category_id=category.id
                )
                
                session.add(product)
                session.commit()
                
                update.message.reply_text(
                    f"✅ 商品新增成功！\n\n"
                    f"名稱：{name}\n"
                    f"價格：${price}\n"
                    f"庫存：{stock}\n"
                    f"分類：{category.name}"
                )
                
                session.close()
                return
            except:
                update.message.reply_text("❌ 格式錯誤，請重新輸入")

def show_admin_menu(query):
    """顯示管理員選單"""
    keyboard = [
        [
            InlineKeyboardButton("📦 商品管理", callback_data="MANAGE_PRODUCTS"),
            InlineKeyboardButton("🗂️ 分類管理", callback_data="MANAGE_CATEGORIES")
        ],
        [
            InlineKeyboardButton("📋 訂單管理", callback_data="MANAGE_ORDERS"),
            InlineKeyboardButton("📊 統計報表", callback_data="VIEW_STATS")
        ],
        [
            InlineKeyboardButton("📤 匯出訂單", callback_data="EXPORT_ORDERS"),
            InlineKeyboardButton("📢 推播訊息", callback_data="BROADCAST")
        ],
        [
            InlineKeyboardButton("🔧 系統設定", callback_data="SYSTEM_SETTINGS"),
            InlineKeyboardButton("🔄 重啟服務", callback_data="RESTART_BOT")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 獲取管理員資訊
    admin_count = len(ADMIN_IDS)
    
    text = f"""🔐 **管理員選單**

👤 管理員數量：{admin_count}
🤖 機器人狀態：運行中

請選擇功能："""
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def show_system_settings(query):
    """顯示系統設定選單"""
    keyboard = [
        [
            InlineKeyboardButton("🔑 更換 API KEY", callback_data="CHANGE_API_KEY"),
            InlineKeyboardButton("👥 管理員管理", callback_data="MANAGE_ADMINS")
        ],
        [
            InlineKeyboardButton("📱 查看 Bot 資訊", callback_data="BOT_INFO"),
            InlineKeyboardButton("🗄️ 資料庫備份", callback_data="BACKUP_DB")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="ADMIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """⚙️ **系統設定**

請選擇要設定的項目："""
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def start_change_api_key(query):
    """開始更換 API KEY 流程"""
    query.message.reply_text(
        "🔑 **更換 Bot API Key**\n\n"
        "⚠️ 注意：更換後需要重啟機器人\n\n"
        "請輸入新的 Bot Token："
    )
    query.answer()
    return WAITING_API_KEY

def handle_new_api_key(update: Update, context: CallbackContext):
    """處理新的 API KEY"""
    new_token = update.message.text.strip()
    
    # 驗證 token 格式
    if not new_token or ':' not in new_token:
        update.message.reply_text("❌ Token 格式錯誤，請重新輸入：")
        return WAITING_API_KEY
    
    try:
        # 讀取現有的 config.py
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替換 BOT_TOKEN
        import re
        new_content = re.sub(
            r'BOT_TOKEN\s*=\s*["\'].*?["\']',
            f'BOT_TOKEN = "{new_token}"',
            content
        )
        
        # 寫回 config.py
        with open('config.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 立即重啟", callback_data="RESTART_NOW"),
                InlineKeyboardButton("⏱️ 稍後重啟", callback_data="ADMIN_MENU")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "✅ **API Key 更新成功！**\n\n"
            "新的 Token 已儲存，需要重啟機器人才能生效。",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        update.message.reply_text(
            f"❌ 更新失敗：{str(e)}\n"
            "請確認有寫入權限"
        )
        return ConversationHandler.END

def show_admin_management(query):
    """顯示管理員管理介面"""
    session = SessionLocal()
    
    # 顯示現有管理員
    admin_list = "👥 **現有管理員 ID：**\n"
    for i, admin_id in enumerate(ADMIN_IDS, 1):
        admin_list += f"{i}. `{admin_id}`\n"
    
    keyboard = [
        [
            InlineKeyboardButton("➕ 新增管理員", callback_data="ADD_ADMIN"),
            InlineKeyboardButton("📋 查看所有用戶", callback_data="VIEW_ALL_USERS")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="SYSTEM_SETTINGS")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""{admin_list}
⚠️ 管理員 ID 無法刪除，只能新增

請選擇操作："""
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    session.close()

def start_add_admin(query):
    """開始新增管理員流程"""
    query.message.reply_text(
        "👤 **新增管理員**\n\n"
        "請輸入要設為管理員的 Telegram 用戶 ID："
    )
    query.answer()
    return WAITING_NEW_ADMIN

def handle_new_admin(update: Update, context: CallbackContext):
    """處理新增管理員"""
    text = update.message.text.strip()
    
    try:
        new_admin_id = int(text)
    except ValueError:
        update.message.reply_text("❌ 請輸入有效的數字 ID：")
        return WAITING_NEW_ADMIN
    
    if new_admin_id in ADMIN_IDS:
        update.message.reply_text("❌ 此用戶已經是管理員")
        return ConversationHandler.END
    
    try:
        # 讀取現有的 config.py
        with open('config.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 找到 ADMIN_IDS 並添加新 ID
        import re
        pattern = r'ADMIN_IDS\s*=\s*\[(.*?)\]'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            existing_ids = match.group(1).strip()
            if existing_ids:
                new_ids = f"{existing_ids}, {new_admin_id}"
            else:
                new_ids = str(new_admin_id)
            
            new_content = re.sub(
                pattern,
                f'ADMIN_IDS = [{new_ids}]',
                content
            )
            
            # 寫回 config.py
            with open('config.py', 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # 更新當前運行的 ADMIN_IDS
            ADMIN_IDS.add(new_admin_id)
            
            keyboard = [
                [
                    InlineKeyboardButton("➕ 繼續新增", callback_data="ADD_ADMIN"),
                    InlineKeyboardButton("🔙 返回", callback_data="MANAGE_ADMINS")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                f"✅ **新增成功！**\n\n"
                f"用戶 ID `{new_admin_id}` 已設為管理員\n"
                f"目前共有 {len(ADMIN_IDS)} 位管理員",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        else:
            update.message.reply_text("❌ 無法解析 config.py 文件")
            
        return ConversationHandler.END
        
    except Exception as e:
        update.message.reply_text(
            f"❌ 新增失敗：{str(e)}\n"
            "請確認有寫入權限"
        )
        return ConversationHandler.END

def restart_bot(query):
    """重啟機器人確認"""
    keyboard = [
        [
            InlineKeyboardButton("✅ 確認重啟", callback_data="CONFIRM_RESTART"),
            InlineKeyboardButton("❌ 取消", callback_data="ADMIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """⚠️ **確認重啟機器人**

重啟將會：
• 中斷所有進行中的對話
• 清空所有暫存資料
• 需要約 5-10 秒重新上線

確定要重啟嗎？"""
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def confirm_restart(query):
    """確認重啟機器人"""
    query.message.edit_text(
        "🔄 **正在重啟機器人...**\n\n"
        "請稍等 5-10 秒後重新連線",
        parse_mode='Markdown'
    )
    
    # 延遲一秒讓訊息發送出去
    import time
    time.sleep(1)
    
    # 重啟程序
    os.execv(sys.executable, ['python'] + sys.argv)

def show_bot_info(query):
    """顯示機器人資訊"""
    bot = query.bot
    
    try:
        bot_info = bot.get_me()
        
        text = f"""🤖 **機器人資訊**

🆔 ID：`{bot_info.id}`
👤 用戶名：@{bot_info.username}
📛 名稱：{bot_info.first_name}
🔧 可內聯：{'是' if bot_info.supports_inline_queries else '否'}

📅 啟動時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💾 資料庫：orders.db
🐍 Python：{sys.version.split()[0]}"""

        keyboard = [
            [InlineKeyboardButton("🔙 返回", callback_data="SYSTEM_SETTINGS")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        query.message.edit_text(f"❌ 無法獲取機器人資訊：{str(e)}")

def view_all_users(query):
    """查看所有用戶"""
    session = SessionLocal()
    
    users = session.query(User).all()
    
    if not users:
        query.message.edit_text("📋 暫無用戶")
        session.close()
        return
    
    text = "👥 **所有用戶列表**\n\n"
    
    for i, user in enumerate(users[:20], 1):  # 限制顯示20個
        admin_tag = " 👑" if user.id in ADMIN_IDS else ""
        text += f"{i}. {user.username or '無名稱'} (`{user.id}`){admin_tag}\n"
    
    if len(users) > 20:
        text += f"\n... 還有 {len(users) - 20} 位用戶"
    
    text += f"\n\n📊 總用戶數：{len(users)}"
    
    keyboard = [
        [InlineKeyboardButton("🔙 返回", callback_data="MANAGE_ADMINS")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    session.close()

def backup_database(query):
    """備份資料庫"""
    try:
        import shutil
        from datetime import datetime
        
        # 創建備份檔名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"orders_backup_{timestamp}.db"
        
        # 複製資料庫檔案
        shutil.copy2('orders.db', backup_filename)
        
        # 獲取檔案大小
        file_size = os.path.getsize(backup_filename) / 1024  # KB
        
        keyboard = [
            [InlineKeyboardButton("🔙 返回", callback_data="SYSTEM_SETTINGS")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.edit_text(
            f"✅ **資料庫備份成功！**\n\n"
            f"📁 檔案名稱：{backup_filename}\n"
            f"💾 檔案大小：{file_size:.2f} KB\n"
            f"📅 備份時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except Exception as e:
        query.message.edit_text(f"❌ 備份失敗：{str(e)}")

def cancel_operation(update: Update, context: CallbackContext):
    """取消當前操作"""
    text = "❌ 已取消操作"
    
    if update.message:
        update.message.reply_text(text)
    else:
        update.callback_query.answer()
        update.callback_query.message.edit_text(text)
    
    return ConversationHandler.END

def export_orders(query):
    """匯出訂單到Excel"""
    session = SessionLocal()
    
    try:
        # 取得所有訂單
        orders = session.query(Order).all()
        
        if not orders:
            query.answer("沒有訂單可匯出", show_alert=True)
            return
        
        # 準備資料
        data = []
        for order in orders:
            for item in order.items:
                data.append({
                    '訂單編號': order.id,
                    '下單時間': order.created_at.strftime('%Y-%m-%d %H:%M'),
                    '用戶ID': order.user_id,
                    '用戶名稱': order.user.username if order.user else 'N/A',
                    '商品名稱': item.product.name,
                    '數量': item.quantity,
                    '單價': item.price,
                    '小計': item.quantity * item.price,
                    '訂單狀態': order.status,
                    '訂單總額': order.total_amount
                })
        
        # 創建DataFrame
        df = pd.DataFrame(data)
        
        # 匯出到Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='訂單明細', index=False)
        
        output.seek(0)
        
        # 發送檔案
        query.bot.send_document(
            chat_id=query.message.chat_id,
            document=output,
            filename=f'orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
            caption='📊 訂單匯出完成'
        )
        
        query.answer("匯出成功")
        
    except Exception as e:
        query.answer(f"匯出失敗：{str(e)}", show_alert=True)
    finally:
        session.close()

def start_broadcast(query):
    """開始推播訊息"""
    query.message.reply_text(
        "📢 **推播訊息**\n\n"
        "請輸入要推播給所有用戶的訊息："
    )
    query.answer()
    return WAITING_BROADCAST

def handle_broadcast_message(update: Update, context: CallbackContext):
    """處理推播訊息"""
    message = update.message.text
    
    session = SessionLocal()
    users = session.query(User).all()
    
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            context.bot.send_message(
                chat_id=user.id,
                text=f"📢 **系統公告**\n\n{message}",
                parse_mode='Markdown'
            )
            success_count += 1
        except:
            fail_count += 1
    
    session.close()
    
    update.message.reply_text(
        f"✅ **推播完成**\n\n"
        f"成功：{success_count} 人\n"
        f"失敗：{fail_count} 人",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END 