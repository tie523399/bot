"""
搜尋流程處理器 v2 - 使用 ConversationHandler
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, Product

# 狀態定義
SEARCH_INPUT = 4
SEARCH_RESULT = 5
INPUT_QUANTITY = 3  # 重用購物流程的數量輸入狀態

def start_search(update: Update, context: CallbackContext):
    """開始搜尋"""
    text = """🔍 **商品搜尋**

請輸入要搜尋的商品名稱或關鍵字：

💡 提示：
- 可以輸入部分名稱
- 不區分大小寫
- 輸入 /cancel 取消搜尋"""
    
    if update.message:
        update.message.reply_text(text, parse_mode='Markdown')
    else:
        update.callback_query.answer()
        update.callback_query.message.reply_text(text, parse_mode='Markdown')
    
    return SEARCH_INPUT

def process_search_input(update: Update, context: CallbackContext):
    """處理搜尋輸入"""
    search_text = update.message.text.strip()
    
    if not search_text:
        update.message.reply_text("❌ 請輸入搜尋關鍵字")
        return SEARCH_INPUT
    
    # 保存搜尋關鍵字
    context.user_data['search_keyword'] = search_text
    
    session = SessionLocal()
    products = session.query(Product).filter(
        Product.name.ilike(f'%{search_text}%'),
        Product.is_active == True
    ).all()
    session.close()
    
    if not products:
        keyboard = [[
            InlineKeyboardButton("🔍 重新搜尋", callback_data="SEARCH"),
            InlineKeyboardButton("🛍️ 瀏覽商品", callback_data="BROWSE"),
            InlineKeyboardButton("🏠 返回主選單", callback_data="MAIN_MENU")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"❌ 找不到包含「{search_text}」的商品\n\n"
            "請嘗試其他關鍵字或瀏覽商品分類",
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    
    # 顯示搜尋結果
    return show_search_results(update, context, products)

def show_search_results(update: Update, context: CallbackContext, products=None):
    """顯示搜尋結果"""
    if products is None:
        # 從資料庫重新獲取（用於分頁等情況）
        search_text = context.user_data.get('search_keyword', '')
        session = SessionLocal()
        products = session.query(Product).filter(
            Product.name.ilike(f'%{search_text}%'),
            Product.is_active == True
        ).all()
        session.close()
    
    keyboard = []
    
    # 限制顯示前20個結果
    display_products = products[:20]
    
    for product in display_products:
        btn_text = f"{product.name} - ${product.price}"
        if product.stock <= 0:
            btn_text += " (售罄)"
            callback_data = "OUT_OF_STOCK"
        else:
            callback_data = f"SELECT_PRODUCT_{product.id}"
        
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=callback_data)
        ])
    
    if len(products) > 20:
        keyboard.append([
            InlineKeyboardButton(
                f"📌 共找到 {len(products)} 個商品（顯示前20個）", 
                callback_data="NONE"
            )
        ])
    
    # 操作按鈕
    keyboard.append([
        InlineKeyboardButton("🔍 重新搜尋", callback_data="SEARCH"),
        InlineKeyboardButton("🛍️ 瀏覽商品", callback_data="BROWSE")
    ])
    keyboard.append([
        InlineKeyboardButton("❌ 取消", callback_data="CANCEL")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""🔎 **搜尋結果**

關鍵字：「{context.user_data.get('search_keyword', '')}」
找到 {len(products)} 個商品

請選擇商品："""
    
    if update.message:
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.callback_query.message.edit_text(
            text, 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )
    
    return SEARCH_RESULT 