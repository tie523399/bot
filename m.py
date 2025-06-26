#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 購物機器人主程式 v2 - 完整 ConversationHandler 版本
"""

from telegram import Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, 
    CallbackQueryHandler, ConversationHandler, CallbackContext
)
import logging
from datetime import datetime

from config import API_TOKEN, ADMIN_IDS
from models import Base, engine, SessionLocal, User
from utils.keyboards import get_main_menu_keyboard

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 初始化資料庫
Base.metadata.create_all(engine)

# ============= 全局狀態定義 =============
# 購物流程
BROWSE_CATEGORY = 1
SELECT_PRODUCT = 2
INPUT_QUANTITY = 3

# 搜尋流程
SEARCH_INPUT = 4
SEARCH_RESULT = 5

# 結帳流程
CHECKOUT_NAME = 6
CHECKOUT_PHONE = 7
CHECKOUT_STORE = 8

# 商品管理
PRODUCT_NAME = 9
PRODUCT_PRICE = 10
PRODUCT_STOCK = 11
PRODUCT_CATEGORY = 12
PRODUCT_DESCRIPTION = 13
PRODUCT_IMAGE = 14

# 編輯商品
EDIT_PRODUCT_FIELD = 15
EDIT_PRODUCT_VALUE = 16

# 分類管理
CATEGORY_NAME = 17
CATEGORY_ICON = 18
CATEGORY_DESCRIPTION = 19
CATEGORY_PHOTO = 20

# 訂單管理
ORDER_STATUS = 21
ORDER_TRACKING = 22
ORDER_NOTIFICATION = 23

# 管理員功能
ADMIN_BROADCAST = 24
ADMIN_ADD_ID = 25
ADMIN_API_KEY = 26

# ============= 基本命令處理器 =============
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
        db_user.username = user.username
        db_user.first_name = user.first_name
        db_user.last_name = user.last_name
        db_user.last_active = datetime.now()
        session.commit()
    
    session.close()
    
    # 清除所有對話狀態
    context.user_data.clear()
    
    welcome_text = f"""
👋 歡迎使用購物機器人，{user.first_name}！

{"🔐 您擁有管理員權限" if is_admin else ""}

請選擇您要的功能：
"""
    
    keyboard = get_main_menu_keyboard(is_admin)
    update.message.reply_text(welcome_text, reply_markup=keyboard)
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    """取消當前操作"""
    context.user_data.clear()
    
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    keyboard = get_main_menu_keyboard(is_admin)
    
    if update.message:
        update.message.reply_text("❌ 操作已取消", reply_markup=keyboard)
    elif update.callback_query:
        update.callback_query.answer()
        update.callback_query.message.edit_text("❌ 操作已取消")
        update.callback_query.message.reply_text("請選擇功能：", reply_markup=keyboard)
    
    return ConversationHandler.END

def timeout(update: Update, context: CallbackContext):
    """對話超時處理"""
    update.message.reply_text("⏰ 操作超時，請重新開始")
    return ConversationHandler.END

# ============= 匯入處理器模組 =============
from handlers.shopping_v2 import (
    start_browse, show_categories, show_products, 
    request_quantity, process_quantity, add_to_cart_confirm
)

from handlers.search_v2 import (
    start_search, process_search_input, show_search_results
)

from handlers.checkout_v2 import (
    start_checkout, process_name, process_phone, 
    process_store, confirm_order
)

from handlers.product_mgmt_v2 import (
    start_add_product, get_product_name, get_product_price,
    get_product_stock, get_product_category, get_product_description,
    get_product_image, create_product,
    start_edit_product, select_edit_field, process_edit_value
)

from handlers.category_mgmt_v2 import (
    start_add_category, get_category_name, get_category_icon,
    get_category_description, get_category_photos, create_category
)

from handlers.order_mgmt_v2 import (
    start_order_management, select_order_action,
    update_order_status, input_tracking_number,
    send_order_notification
)

from handlers.admin_v2 import (
    start_broadcast, process_broadcast_message,
    start_add_admin, process_admin_id,
    start_change_api_key, process_new_api_key
)

# ============= ConversationHandler 定義 =============

def create_shopping_handler():
    """創建購物對話處理器"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('browse', start_browse),
            CallbackQueryHandler(start_browse, pattern='^BROWSE$')
        ],
        states={
            BROWSE_CATEGORY: [
                CallbackQueryHandler(show_products, pattern='^CATEGORY_')
            ],
            SELECT_PRODUCT: [
                CallbackQueryHandler(request_quantity, pattern='^SELECT_PRODUCT_')
            ],
            INPUT_QUANTITY: [
                MessageHandler(Filters.text & ~Filters.command, process_quantity)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL$')
        ],
        conversation_timeout=300  # 5分鐘超時
    )

def create_search_handler():
    """創建搜尋對話處理器"""
    return ConversationHandler(
        entry_points=[
            CommandHandler('search', start_search),
            CallbackQueryHandler(start_search, pattern='^SEARCH$')
        ],
        states={
            SEARCH_INPUT: [
                MessageHandler(Filters.text & ~Filters.command, process_search_input)
            ],
            SEARCH_RESULT: [
                CallbackQueryHandler(request_quantity, pattern='^SELECT_PRODUCT_')
            ],
            INPUT_QUANTITY: [
                MessageHandler(Filters.text & ~Filters.command, process_quantity)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL$')
        ],
        conversation_timeout=300
    )

def create_checkout_handler():
    """創建結帳對話處理器"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_checkout, pattern='^START_CHECKOUT$'),
            CommandHandler('checkout', start_checkout)
        ],
        states={
            CHECKOUT_NAME: [
                MessageHandler(Filters.text & ~Filters.command, process_name)
            ],
            CHECKOUT_PHONE: [
                MessageHandler(Filters.text & ~Filters.command, process_phone)
            ],
            CHECKOUT_STORE: [
                MessageHandler(Filters.text & ~Filters.command, process_store)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL_CHECKOUT$')
        ],
        conversation_timeout=600  # 10分鐘超時
    )

def create_product_management_handler():
    """創建商品管理對話處理器"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_product, pattern='^ADD_PRODUCT$'),
            CallbackQueryHandler(start_edit_product, pattern='^EDIT_PRODUCT_')
        ],
        states={
            PRODUCT_NAME: [
                MessageHandler(Filters.text & ~Filters.command, get_product_name)
            ],
            PRODUCT_PRICE: [
                MessageHandler(Filters.text & ~Filters.command, get_product_price)
            ],
            PRODUCT_STOCK: [
                MessageHandler(Filters.text & ~Filters.command, get_product_stock)
            ],
            PRODUCT_CATEGORY: [
                CallbackQueryHandler(get_product_category, pattern='^SELECT_CAT_')
            ],
            PRODUCT_DESCRIPTION: [
                MessageHandler(Filters.text & ~Filters.command, get_product_description)
            ],
            PRODUCT_IMAGE: [
                MessageHandler(Filters.text & ~Filters.command, get_product_image)
            ],
            EDIT_PRODUCT_FIELD: [
                CallbackQueryHandler(select_edit_field, pattern='^EDIT_FIELD_')
            ],
            EDIT_PRODUCT_VALUE: [
                MessageHandler(Filters.text & ~Filters.command, process_edit_value)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL$')
        ],
        conversation_timeout=600
    )

def create_category_management_handler():
    """創建分類管理對話處理器"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_category, pattern='^ADD_CATEGORY$')
        ],
        states={
            CATEGORY_NAME: [
                MessageHandler(Filters.text & ~Filters.command, get_category_name)
            ],
            CATEGORY_ICON: [
                MessageHandler(Filters.text & ~Filters.command, get_category_icon)
            ],
            CATEGORY_DESCRIPTION: [
                MessageHandler(Filters.text & ~Filters.command, get_category_description)
            ],
            CATEGORY_PHOTO: [
                MessageHandler(Filters.text & ~Filters.command, get_category_photos)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL$')
        ],
        conversation_timeout=600
    )

def create_order_management_handler():
    """創建訂單管理對話處理器"""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_order_management, pattern='^ORDER_VIEW_')
        ],
        states={
            ORDER_STATUS: [
                CallbackQueryHandler(update_order_status, pattern='^ORDER_SET_')
            ],
            ORDER_TRACKING: [
                MessageHandler(Filters.text & ~Filters.command, input_tracking_number)
            ],
            ORDER_NOTIFICATION: [
                MessageHandler(Filters.text & ~Filters.command, send_order_notification)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL$')
        ],
        conversation_timeout=300
    )

def create_admin_handlers():
    """創建管理員功能對話處理器"""
    handlers = []
    
    # 推播訊息
    handlers.append(ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_broadcast, pattern='^BROADCAST$')
        ],
        states={
            ADMIN_BROADCAST: [
                MessageHandler(Filters.text & ~Filters.command, process_broadcast_message)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=300
    ))
    
    # 新增管理員
    handlers.append(ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_admin, pattern='^ADD_ADMIN$')
        ],
        states={
            ADMIN_ADD_ID: [
                MessageHandler(Filters.text & ~Filters.command, process_admin_id)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=300
    ))
    
    # 更改 API Key
    handlers.append(ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_change_api_key, pattern='^CHANGE_API_KEY$')
        ],
        states={
            ADMIN_API_KEY: [
                MessageHandler(Filters.text & ~Filters.command, process_new_api_key)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        conversation_timeout=300
    ))
    
    return handlers

# ============= 簡單回調處理器 =============
def handle_simple_callbacks(update: Update, context: CallbackContext):
    """處理不需要對話流程的簡單回調"""
    query = update.callback_query
    data = query.data
    
    # 這裡處理所有不需要對話流程的簡單操作
    # 如：查看購物車、返回主選單等
    from handlers import handle_callback
    handle_callback(update, context)

def main():
    """主程式"""
    updater = Updater(API_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # 註冊 ConversationHandler（優先順序高）
    dp.add_handler(create_shopping_handler())
    dp.add_handler(create_search_handler())
    dp.add_handler(create_checkout_handler())
    dp.add_handler(create_product_management_handler())
    dp.add_handler(create_category_management_handler())
    dp.add_handler(create_order_management_handler())
    
    # 註冊管理員對話處理器
    for handler in create_admin_handlers():
        dp.add_handler(handler)
    
    # 註冊基本命令（這些應該在 ConversationHandler 之後）
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("使用 /start 開始")))
    dp.add_handler(CommandHandler("cancel", cancel))
    
    # 註冊簡單回調處理器（最低優先順序）
    dp.add_handler(CallbackQueryHandler(handle_simple_callbacks))
    
    # 錯誤處理器
    dp.add_error_handler(lambda u, c: logger.error(f"Error: {c.error}"))
    
    # 啟動機器人
    logger.info("機器人啟動中...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
