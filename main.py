#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 購物機器人主程式
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
from telegram.ext import CallbackContext
import logging
from datetime import datetime

from config import API_TOKEN, ADMIN_IDS
from models import Base, engine, SessionLocal, User
from utils.keyboards import get_main_menu_keyboard

# 匯入所有處理器
from handlers import products, cart, orders, admin
from handlers import product_options, product_management, order_management
from handlers import category_management, statistics
from handlers.orders import (
    WAITING_NAME, WAITING_PHONE, WAITING_STORE, 
    process_name, process_phone, process_store
)
from handlers.product_management import (
    WAITING_NAME as PROD_NAME,
    WAITING_PRICE as PROD_PRICE,
    WAITING_STOCK as PROD_STOCK,
    WAITING_CATEGORY as PROD_CATEGORY,
    WAITING_DESCRIPTION as PROD_DESCRIPTION,
    WAITING_IMAGE as PROD_IMAGE,
    handle_product_name,
    handle_product_price,
    handle_product_stock,
    handle_product_description,
    handle_product_image,
    cancel_add_product
)
from handlers.admin import (
    WAITING_API_KEY,
    WAITING_NEW_ADMIN,
    WAITING_BROADCAST,
    handle_new_api_key,
    handle_new_admin,
    handle_broadcast_message,
    cancel_operation
)

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化資料庫
Base.metadata.create_all(engine)

# 狀態定義
WAITING_STORE = 1

def start(update: Update, context: CallbackContext):
    """處理 /start 命令"""
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    
    # 確保用戶存在於資料庫
    session = SessionLocal()
    db_user = session.query(User).filter_by(user_id=user.id).first()
    
    if not db_user:
        db_user = User(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        session.add(db_user)
        session.commit()
    else:
        # 更新用戶資訊
        db_user.username = user.username
        db_user.first_name = user.first_name
        db_user.last_name = user.last_name
        db_user.last_active = datetime.now()
        session.commit()
    
    session.close()
    
    welcome_text = f"""
👋 歡迎使用購物機器人，{user.first_name}！

{"🔐 您擁有管理員權限" if is_admin else ""}

請選擇您要的功能：
"""
    
    keyboard = get_main_menu_keyboard(is_admin)
    update.message.reply_text(welcome_text, reply_markup=keyboard)

def show_help(update: Update, context: CallbackContext):
    """顯示幫助訊息"""
    help_text = """
📖 **使用說明**

**基本指令：**
/start - 開始使用機器人
/help - 顯示此幫助訊息
/menu - 顯示主選單
/cart - 查看購物車
/orders - 查看我的訂單
/search - 搜尋商品

**購物流程：**
1. 瀏覽商品或搜尋商品
2. 選擇商品並加入購物車
3. 查看購物車並結帳
4. 填寫收件資訊
5. 完成訂單

如有問題請聯繫客服！
"""
    update.message.reply_text(help_text, parse_mode='Markdown')

def menu(update: Update, context: CallbackContext):
    """顯示主選單"""
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    keyboard = get_main_menu_keyboard(is_admin)
    update.message.reply_text("請選擇功能：", reply_markup=keyboard)

def handle_button_message(update: Update, context: CallbackContext):
    """處理按鈕選單的文字訊息"""
    text = update.message.text
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    
    # 將按鈕文字轉換為對應的功能
    if text == '🛍️ 購物車':
        cart.show_cart(update, context)
    elif text == '🔍 瀏覽商品':
        products.browse_products(update, context)
    elif text == '📦 我的訂單':
        orders.show_my_orders(update, context)
    elif text == '❤️ 我的收藏':
        products.show_favorites_text(update, context)
    elif text == '📞 聯繫客服':
        update.message.reply_text(
            "📞 **客服聯絡方式**\n\n"
            "• Telegram: @support\n"
            "• Email: support@shop.com\n"
            "• 服務時間: 09:00-18:00",
            parse_mode='Markdown'
        )
    
    # 管理員功能
    elif is_admin and text == '📦 商品管理':
        product_management.product_management_menu(update, context)
    elif is_admin and text == '🗂️ 分類管理':
        category_management.category_management_menu(update, context)
    elif is_admin and text == '📋 訂單管理':
        order_management.order_management_menu(update, context)
    elif is_admin and text == '📊 銷售統計':
        statistics.show_statistics_menu(update, context)
    else:
        # 預設顯示主選單
        keyboard = get_main_menu_keyboard(is_admin)
        update.message.reply_text("請選擇功能：", reply_markup=keyboard)

def handle_text_message(update: Update, context: CallbackContext):
    """處理文字訊息"""
    # 處理商品搜尋
    if products.handle_search_text(update, context):
        return
    
    # 處理商品數量輸入
    if products.handle_quantity_input(update, context):
        return
    
    # 處理按鈕訊息
    handle_button_message(update, context)

def error_handler(update: Update, context: CallbackContext):
    """處理錯誤"""
    logger.warning(f'Update {update} caused error {context.error}')
    
    # 通知用戶
    try:
        if update and update.effective_message:
            update.effective_message.reply_text(
                "❌ 發生錯誤，請稍後再試。如果問題持續，請聯繫客服。"
            )
    except:
        pass

def admin_command(update: Update, context: CallbackContext):
    """管理員指令"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ 您沒有權限使用此功能")
        return
    
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
            InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    admin_count = len(ADMIN_IDS)
    
    text = f"""🔐 **管理員選單**

👤 管理員數量：{admin_count}
🤖 機器人狀態：運行中

請選擇功能："""
    
    update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

def main():
    """主程式"""
    updater = Updater(API_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # 註冊處理器
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", show_help))
    dp.add_handler(CommandHandler("menu", menu))
    dp.add_handler(CommandHandler("cart", cart.show_cart))
    dp.add_handler(CommandHandler("orders", orders.show_my_orders))
    dp.add_handler(CommandHandler("search", products.search_products))
    
    # 結帳對話處理器（簡化版）
    checkout_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(orders.start_checkout, pattern='^START_CHECKOUT$'),
            CallbackQueryHandler(orders.start_checkout, pattern='^CHECKOUT$'),
            CommandHandler('checkout', orders.checkout)
        ],
        states={
            WAITING_NAME: [MessageHandler(Filters.text & ~Filters.command, process_name)],
            WAITING_PHONE: [MessageHandler(Filters.text & ~Filters.command, process_phone)],
            WAITING_STORE: [MessageHandler(Filters.text & ~Filters.command, process_store)]
        },
        fallbacks=[
            CommandHandler('cancel', orders.cancel_order),
            CallbackQueryHandler(orders.cancel_order, pattern='^CANCEL_CHECKOUT$')
        ],
        allow_reentry=True
    )
    
    dp.add_handler(checkout_handler)
    
    # 商品管理對話處理器（新版）
    add_product_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(product_management.start_add_product, pattern='^ADD_PRODUCT$')
        ],
        states={
            PROD_NAME: [MessageHandler(Filters.text & ~Filters.command, handle_product_name)],
            PROD_PRICE: [MessageHandler(Filters.text & ~Filters.command, handle_product_price)],
            PROD_STOCK: [MessageHandler(Filters.text & ~Filters.command, handle_product_stock)],
            PROD_CATEGORY: [
                CallbackQueryHandler(
                    lambda u, c: product_management.handle_category_selection(
                        u.callback_query, 
                        int(u.callback_query.data.replace("SELECT_CAT_", ""))
                    ),
                    pattern='^SELECT_CAT_'
                )
            ],
            PROD_DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, handle_product_description)],
            PROD_IMAGE: [MessageHandler(Filters.text & ~Filters.command, handle_product_image)]
        },
        fallbacks=[CommandHandler('cancel', cancel_add_product)],
        allow_reentry=True
    )
    
    dp.add_handler(add_product_handler)
    
    # 訂單狀態更新處理器
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command & Filters.user(ADMIN_IDS),
        lambda u, c: (
            order_management.handle_shipping_number(u, c) 
            if c.user_data.get('shipping_order')
            else order_management.handle_customer_notification(u, c)
            if c.user_data.get('notify_order')
            else None
        )
    ))
    
    # 一般文字訊息處理器（處理數量輸入等）
    dp.add_handler(MessageHandler(
        Filters.text & ~Filters.command,
        handle_text_message
    ))
    
    # Callback 處理器 - 使用 handlers 模組中的統一處理器
    from handlers import handle_callback
    dp.add_handler(CallbackQueryHandler(handle_callback))
    
    # API Key 更換對話處理器
    api_key_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: admin.start_change_api_key(u.callback_query), pattern='^CHANGE_API_KEY$')
        ],
        states={
            WAITING_API_KEY: [MessageHandler(Filters.text & ~Filters.command, handle_new_api_key)]
        },
        fallbacks=[CommandHandler('cancel', cancel_operation)],
        allow_reentry=True
    )
    
    dp.add_handler(api_key_handler)
    
    # 新增管理員對話處理器
    add_admin_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: admin.start_add_admin(u.callback_query), pattern='^ADD_ADMIN$')
        ],
        states={
            WAITING_NEW_ADMIN: [MessageHandler(Filters.text & ~Filters.command, handle_new_admin)]
        },
        fallbacks=[CommandHandler('cancel', cancel_operation)],
        allow_reentry=True
    )
    
    dp.add_handler(add_admin_handler)
    
    # 推播訊息對話處理器
    broadcast_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(lambda u, c: admin.start_broadcast(u.callback_query), pattern='^BROADCAST$')
        ],
        states={
            WAITING_BROADCAST: [MessageHandler(Filters.text & ~Filters.command, handle_broadcast_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel_operation)],
        allow_reentry=True
    )
    
    dp.add_handler(broadcast_handler)
    
    # 錯誤處理器
    dp.add_error_handler(error_handler)
    
    # 啟動機器人
    logging.info("機器人啟動中...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main() 