"""鍵盤工具"""
from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from models import SessionLocal, Category

def get_main_menu_keyboard(is_admin=False):
    """獲取主選單鍵盤"""
    keyboard = [
        ['🔍 瀏覽商品', '🛍️ 購物車'],
        ['📦 我的訂單', '❤️ 我的收藏'],
        ['📞 聯繫客服']
    ]
    
    if is_admin:
        # 管理員功能分組
        keyboard.insert(0, ['📦 商品管理', '🗂️ 分類管理'])
        keyboard.insert(1, ['📋 訂單管理', '📊 銷售統計'])
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_admin_menu_keyboard():
    """獲取管理員選單鍵盤（內聯按鈕）"""
    keyboard = [
        [
            InlineKeyboardButton("📦 商品管理", callback_data="PROD_MGMT"),
            InlineKeyboardButton("🗂️ 分類管理", callback_data="CAT_MGMT")
        ],
        [
            InlineKeyboardButton("📋 訂單管理", callback_data="ORDER_MGMT"),
            InlineKeyboardButton("📊 銷售統計", callback_data="STATS_MENU")
        ],
        [
            InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_categories_keyboard():
    """獲取分類鍵盤"""
    session = SessionLocal()
    categories = session.query(Category).filter_by(is_active=True).order_by(Category.order).all()
    
    keyboard = []
    for cat in categories:
        text = f"{cat.icon} {cat.name}" if cat.icon else cat.name
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"CAT_{cat.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
    ])
    
    session.close()
    return InlineKeyboardMarkup(keyboard)

def get_cart_keyboard(has_items=True):
    """獲取購物車鍵盤"""
    keyboard = []
    
    if has_items:
        keyboard = [
            [
                InlineKeyboardButton("💳 結帳", callback_data="CHECKOUT"),
                InlineKeyboardButton("🗑️ 清空", callback_data="CLEAR_CART")
            ],
            [
                InlineKeyboardButton("🛒 繼續購物", callback_data="BROWSE"),
                InlineKeyboardButton("🔙 主選單", callback_data="MAIN_MENU")
            ]
        ]
    else:
        keyboard = [
            [
                InlineKeyboardButton("🛒 去購物", callback_data="BROWSE"),
                InlineKeyboardButton("🔙 主選單", callback_data="MAIN_MENU")
            ]
        ]
    
    return InlineKeyboardMarkup(keyboard)

def get_order_status_keyboard(order_id):
    """獲取訂單狀態鍵盤"""
    keyboard = [
        [
            InlineKeyboardButton("📋 查看詳情", callback_data=f"VIEW_ORDER_{order_id}"),
            InlineKeyboardButton("🔙 返回列表", callback_data="MY_ORDERS")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_back_button(callback_data="MAIN_MENU"):
    """獲取返回按鈕"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 返回", callback_data=callback_data)
    ]]) 