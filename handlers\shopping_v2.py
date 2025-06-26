"""
購物流程處理器 v2 - 使用 ConversationHandler
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, Product, Category, CartItem, User
from datetime import datetime

# 從主程式匯入狀態
BROWSE_CATEGORY = 1
SELECT_PRODUCT = 2
INPUT_QUANTITY = 3

def start_browse(update: Update, context: CallbackContext):
    """開始瀏覽商品"""
    session = SessionLocal()
    categories = session.query(Category).filter_by(is_active=True).order_by(Category.display_order).all()
    session.close()
    
    if not categories:
        if update.message:
            update.message.reply_text("暫無商品分類")
        else:
            update.callback_query.answer()
            update.callback_query.message.edit_text("暫無商品分類")
        return ConversationHandler.END
    
    keyboard = []
    for cat in categories:
        button_text = f"{cat.icon} {cat.name}" if cat.icon else cat.name
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"CATEGORY_{cat.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("❌ 取消", callback_data="CANCEL")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "🛍️ **請選擇商品分類：**"
    
    if update.message:
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.callback_query.answer()
        update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return BROWSE_CATEGORY

def show_categories(update: Update, context: CallbackContext):
    """顯示分類（用於返回）"""
    return start_browse(update, context)

def show_products(update: Update, context: CallbackContext):
    """顯示分類中的商品"""
    query = update.callback_query
    query.answer()
    
    category_id = int(query.data.replace("CATEGORY_", ""))
    context.user_data['current_category'] = category_id
    
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    products = session.query(Product).filter_by(
        category_id=category_id,
        is_active=True
    ).all()
    session.close()
    
    if not products:
        query.message.edit_text(
            f"❌ {category.name} 分類暫無商品",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 返回分類", callback_data="BACK_TO_CATEGORIES")
            ]])
        )
        return BROWSE_CATEGORY
    
    # 建立商品按鈕網格
    keyboard = []
    row = []
    for i, product in enumerate(products):
        btn_text = f"{product.name} ${product.price}"
        if product.stock <= 0:
            btn_text += " (售罄)"
            callback_data = "OUT_OF_STOCK"
        else:
            callback_data = f"SELECT_PRODUCT_{product.id}"
        
        row.append(InlineKeyboardButton(btn_text, callback_data=callback_data))
        
        if (i + 1) % 2 == 0:  # 每行2個按鈕
            keyboard.append(row)
            row = []
    
    if row:  # 添加剩餘的按鈕
        keyboard.append(row)
    
    # 添加返回按鈕
    keyboard.append([
        InlineKeyboardButton("🔙 返回分類", callback_data="BACK_TO_CATEGORIES"),
        InlineKeyboardButton("❌ 取消", callback_data="CANCEL")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"**{category.icon} {category.name}**\n\n請選擇商品："
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return SELECT_PRODUCT

def request_quantity(update: Update, context: CallbackContext):
    """請求輸入商品數量"""
    query = update.callback_query
    
    if query.data == "OUT_OF_STOCK":
        query.answer("此商品已售罄", show_alert=True)
        return SELECT_PRODUCT
    
    if query.data == "BACK_TO_CATEGORIES":
        return show_categories(update, context)
    
    query.answer()
    
    product_id = int(query.data.replace("SELECT_PRODUCT_", ""))
    context.user_data['selected_product_id'] = product_id
    
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product or product.stock <= 0:
        query.answer("商品不存在或已售罄", show_alert=True)
        session.close()
        return SELECT_PRODUCT
    
    # 檢查購物車中已有的數量
    user_id = query.from_user.id
    existing_cart = session.query(CartItem).filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    current_qty = existing_cart.quantity if existing_cart else 0
    available = product.stock - current_qty
    
    text = f"""📦 **{product.name}**
💰 單價：${product.price}
📦 庫存：{product.stock}
🛒 購物車已有：{current_qty}

請輸入購買數量（1-{min(available, 99)}）：

💡 輸入 /cancel 取消操作"""
    
    # 儲存商品資訊供後續使用
    context.user_data['product_name'] = product.name
    context.user_data['product_price'] = product.price
    context.user_data['product_stock'] = product.stock
    context.user_data['current_qty'] = current_qty
    context.user_data['available'] = available
    
    session.close()
    
    query.message.edit_text(text, parse_mode='Markdown')
    
    return INPUT_QUANTITY

def process_quantity(update: Update, context: CallbackContext):
    """處理數量輸入"""
    user_id = update.effective_user.id
    product_id = context.user_data.get('selected_product_id')
    
    if not product_id:
        update.message.reply_text("❌ 操作已過期，請重新開始")
        return ConversationHandler.END
    
    try:
        quantity = int(update.message.text.strip())
    except ValueError:
        update.message.reply_text("❌ 請輸入有效的數字")
        return INPUT_QUANTITY
    
    if quantity < 1:
        update.message.reply_text("❌ 數量必須至少為1")
        return INPUT_QUANTITY
    
    available = context.user_data.get('available', 0)
    if quantity > available:
        update.message.reply_text(
            f"❌ 庫存不足\n"
            f"最多還能加入：{available} 件"
        )
        return INPUT_QUANTITY
    
    # 確保用戶存在
    ensure_user_exists(user_id)
    
    # 加入購物車
    session = SessionLocal()
    try:
        # 檢查現有購物車項目
        cart_item = session.query(CartItem).filter_by(
            user_id=user_id,
            product_id=product_id
        ).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity
            )
            session.add(cart_item)
        
        session.commit()
        
        # 計算總數和小計
        total_qty = cart_item.quantity
        product_price = context.user_data.get('product_price', 0)
        subtotal = product_price * quantity
        
        # 成功訊息
        keyboard = [
            [
                InlineKeyboardButton("🛍️ 繼續購物", callback_data="CONTINUE_SHOPPING"),
                InlineKeyboardButton("🛒 查看購物車", callback_data="VIEW_CART")
            ],
            [
                InlineKeyboardButton("💳 直接結帳", callback_data="START_CHECKOUT"),
                InlineKeyboardButton("🏠 返回主選單", callback_data="MAIN_MENU")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            f"""✅ **已加入購物車**

📦 {context.user_data.get('product_name', '商品')}
💰 ${product_price} × {quantity} = ${subtotal}
🛒 購物車內共 {total_qty} 件

請選擇下一步操作：""",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # 清理用戶數據
        context.user_data.clear()
        
        session.close()
        return ConversationHandler.END
        
    except Exception as e:
        session.rollback()
        session.close()
        update.message.reply_text(f"❌ 加入購物車失敗：{str(e)}")
        return ConversationHandler.END

def add_to_cart_confirm(update: Update, context: CallbackContext):
    """確認加入購物車（用於回調處理）"""
    query = update.callback_query
    
    if query.data == "CONTINUE_SHOPPING":
        # 返回分類選擇
        return start_browse(update, context)
    
    # 其他選項由簡單回調處理器處理
    return ConversationHandler.END

def ensure_user_exists(user_id):
    """確保用戶存在於資料庫"""
    session = SessionLocal()
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if not user:
        user = User(
            user_id=user_id,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        session.add(user)
        session.commit()
    
    session.close() 