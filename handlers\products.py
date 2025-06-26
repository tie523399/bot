"""商品處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, Product, Category, Favorite, CartItem, User
from handlers.cart import add_to_cart
from datetime import datetime

# 狀態定義
WAITING_QUANTITY = 1

def browse_products(update: Update, context: CallbackContext):
    """瀏覽商品分類"""
    session = SessionLocal()
    categories = session.query(Category).filter_by(is_active=True).order_by(Category.display_order).all()
    
    if not categories:
        update.message.reply_text("暫無商品分類")
        session.close()
        return
    
    keyboard = []
    for cat in categories:
        button_text = f"{cat.icon} {cat.name}" if cat.icon else cat.name
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"CATEGORY_{cat.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "🛍️ **請選擇商品分類：**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_category_with_photos(query, category_id, photo_index=1):
    """顯示分類照片和商品按鈕"""
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        query.message.edit_text("分類不存在")
        session.close()
        return
    
    # 獲取分類的照片
    photos = []
    for i in range(1, 6):
        photo_url = getattr(category, f'photo_{i}', None)
        if photo_url:
            photos.append(photo_url)
    
    # 獲取該分類的商品
    products = session.query(Product).filter_by(
        category_id=category_id, 
        is_active=True
    ).all()
    
    # 創建商品按鈕
    keyboard = []
    row = []
    for i, product in enumerate(products):
        btn_text = f"{product.name} ${product.price}"
        if product.stock <= 0:
            btn_text += " (售罄)"
        
        row.append(InlineKeyboardButton(
            btn_text, 
            callback_data=f"SELECT_PRODUCT_{product.id}" if product.stock > 0 else "OUT_OF_STOCK"
        ))
        
        # 每3個商品一行
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    
    # 添加剩餘的按鈕
    if row:
        keyboard.append(row)
    
    # 照片導航按鈕（如果有多張照片）
    if len(photos) > 1:
        nav_row = []
        if photo_index > 1:
            nav_row.append(InlineKeyboardButton("⬅️", callback_data=f"CAT_PHOTO_{category_id}_{photo_index-1}"))
        nav_row.append(InlineKeyboardButton(f"{photo_index}/{len(photos)}", callback_data="NONE"))
        if photo_index < len(photos):
            nav_row.append(InlineKeyboardButton("➡️", callback_data=f"CAT_PHOTO_{category_id}_{photo_index+1}"))
        keyboard.append(nav_row)
    
    # 返回按鈕
    keyboard.append([
        InlineKeyboardButton("🔙 返回分類", callback_data="CATEGORIES")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 發送或更新訊息
    text = f"**{category.icon} {category.name}**\n\n"
    if category.description:
        text += f"{category.description}\n\n"
    text += "請選擇商品："
    
    if photos and photo_index <= len(photos):
        # 有照片，發送照片
        photo_url = photos[photo_index - 1]
        try:
            # 嘗試刪除原訊息並發送新照片
            query.message.delete()
            query.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=photo_url,
                caption=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except:
            # 如果失敗，只更新文字
            query.message.edit_text(
                text + f"\n\n[照片 {photo_index}]",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    else:
        # 沒有照片，只顯示文字
        query.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    session.close()

def show_products_by_category(query, category_id):
    """顯示分類商品（調用照片展示版本）"""
    show_category_with_photos(query, category_id, 1)

def handle_product_selection(query, product_id):
    """處理商品選擇，請求輸入數量"""
    context = query._context
    user_id = query.from_user.id
    
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.answer("商品不存在", show_alert=True)
        session.close()
        return
    
    # 檢查庫存
    if product.stock <= 0:
        query.answer("商品已售罄", show_alert=True)
        session.close()
        return
    
    # 保存選中的商品ID
    context.user_data['selected_product_id'] = product_id
    context.user_data['waiting_quantity'] = True
    
    # 請求輸入數量
    query.message.reply_text(
        f"📦 **{product.name}**\n"
        f"💰 單價：${product.price}\n"
        f"📦 庫存：{product.stock}\n\n"
        f"請輸入購買數量（1-{min(product.stock, 99)}）："
    )
    
    query.answer()
    session.close()

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

def handle_quantity_input(update: Update, context: CallbackContext):
    """處理數量輸入"""
    if not context.user_data.get('waiting_quantity'):
        return False
    
    user_id = update.effective_user.id
    product_id = context.user_data.get('selected_product_id')
    
    if not product_id:
        return False
    
    try:
        quantity = int(update.message.text.strip())
    except ValueError:
        update.message.reply_text("❌ 請輸入有效的數字")
        return True
    
    if quantity < 1:
        update.message.reply_text("❌ 數量必須至少為1")
        return True
    
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        update.message.reply_text("❌ 商品不存在")
        context.user_data.clear()
        session.close()
        return True
    
    # 檢查庫存
    if quantity > product.stock:
        update.message.reply_text(
            f"❌ 庫存不足\n"
            f"目前庫存：{product.stock} 件"
        )
        session.close()
        return True
    
    # 檢查購物車中已有的數量
    existing_cart = session.query(CartItem).filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    current_qty = existing_cart.quantity if existing_cart else 0
    total_qty = current_qty + quantity
    
    if total_qty > product.stock:
        available = product.stock - current_qty
        update.message.reply_text(
            f"❌ 庫存不足\n"
            f"購物車已有：{current_qty} 件\n"
            f"最多還能加入：{available} 件"
        )
        session.close()
        return True
    
    # 確保用戶存在
    ensure_user_exists(user_id)
    
    # 加入購物車
    success, message = add_to_cart(product_id, user_id, quantity)
    
    if success:
        # 計算小計
        subtotal = product.price * quantity
        update.message.reply_text(
            f"✅ **已加入購物車**\n\n"
            f"📦 {product.name}\n"
            f"💰 ${product.price} × {quantity} = ${subtotal}\n"
            f"🛒 購物車內共 {total_qty} 件",
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(f"❌ {message}")
    
    # 清理狀態
    context.user_data.pop('waiting_quantity', None)
    context.user_data.pop('selected_product_id', None)
    
    # 顯示選項
    keyboard = [
        [
            InlineKeyboardButton("🛍️ 繼續購物", callback_data="CATEGORIES"),
            InlineKeyboardButton("🛒 查看購物車", callback_data="VIEW_CART")
        ],
        [
            InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "請選擇下一步操作：",
        reply_markup=reply_markup
    )
    
    session.close()
    return True

def show_favorites_text(update: Update, context: CallbackContext):
    """顯示用戶收藏（文字版）"""
    user_id = update.effective_user.id
    session = SessionLocal()
    
    favorites = session.query(Favorite).filter_by(user_id=user_id).all()
    
    if favorites:
        text = "❤️ **我的收藏**\n\n"
        for fav in favorites:
            if fav.product:
                text += f"• {fav.product.name} - ${fav.product.price}\n"
        update.message.reply_text(text, parse_mode='Markdown')
    else:
        update.message.reply_text("您還沒有收藏商品")
    
    session.close()

def add_product_to_cart(query, product_id):
    """將商品加入購物車"""
    user_id = query.from_user.id
    
    from handlers.cart import add_to_cart
    success, message = add_to_cart(product_id, user_id, 1)
    
    if success:
        query.answer(message, show_alert=False)
    else:
        query.answer(message, show_alert=True)
    
    # 重新顯示商品詳情
    show_product_detail(query, product_id)

def show_categories(query):
    """顯示商品分類（內聯版本）"""
    session = SessionLocal()
    categories = session.query(Category).filter_by(is_active=True).order_by(Category.display_order).all()
    
    if not categories:
        query.message.edit_text("暫無商品分類")
        session.close()
        return
    
    keyboard = []
    for cat in categories:
        button_text = f"{cat.icon} {cat.name}" if cat.icon else cat.name
        keyboard.append([
            InlineKeyboardButton(button_text, callback_data=f"CATEGORY_{cat.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        "🛍️ **請選擇商品分類：**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_product_detail(query, product_id):
    """顯示商品詳情（保留以兼容）"""
    user_id = query.from_user.id
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    # 檢查是否已收藏
    is_favorite = session.query(Favorite).filter_by(
        user_id=user_id,
        product_id=product_id
    ).first() is not None
    
    text = f"**{product.name}**\n\n"
    text += f"💰 價格: ${product.price}\n"
    text += f"📦 庫存: {product.stock}\n"
    
    if product.description:
        text += f"\n📝 {product.description}\n"
    
    keyboard = []
    
    # 購買按鈕 - 改為觸發數量輸入
    if product.stock > 0:
        keyboard.append([
            InlineKeyboardButton("🛒 加入購物車", callback_data=f"SELECT_PRODUCT_{product.id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("❌ 已售完", callback_data="OUT_OF_STOCK")
        ])
    
    # 收藏按鈕
    fav_text = "💔 取消收藏" if is_favorite else "❤️ 加入收藏"
    keyboard.append([
        InlineKeyboardButton(fav_text, callback_data=f"TOGGLE_FAV_{product.id}")
    ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data=f"CATEGORY_{product.category_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 如果有圖片URL，嘗試發送圖片
    if product.image_url and query.message.text:
        try:
            query.message.delete()
            query.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=product.image_url,
                caption=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except:
            query.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    else:
        query.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    session.close()

def toggle_favorite(query, product_id):
    """切換收藏狀態"""
    user_id = query.from_user.id
    session = SessionLocal()
    
    # 檢查現有收藏
    favorite = session.query(Favorite).filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    if favorite:
        # 取消收藏
        session.delete(favorite)
        session.commit()
        query.answer("已取消收藏", show_alert=True)
    else:
        # 加入收藏
        new_fav = Favorite(
            user_id=user_id,
            product_id=product_id
        )
        session.add(new_fav)
        session.commit()
        query.answer("已加入收藏", show_alert=True)
    
    session.close()
    
    # 重新顯示商品詳情
    show_product_detail(query, product_id)

def search_products(update: Update, context: CallbackContext):
    """商品搜尋功能"""
    if update.message:
        update.message.reply_text("請輸入要搜尋的商品名稱：")
        context.user_data['searching'] = True
    
def handle_search_text(update: Update, context: CallbackContext):
    """處理搜尋文字"""
    if not context.user_data.get('searching'):
        return False
    
    search_text = update.message.text.strip()
    context.user_data['searching'] = False
    
    session = SessionLocal()
    products = session.query(Product).filter(
        Product.name.ilike(f'%{search_text}%')
    ).all()
    
    if not products:
        update.message.reply_text(f"❌ 找不到包含「{search_text}」的商品")
        session.close()
        return True
    
    keyboard = []
    for prod in products[:10]:  # 限制顯示10個
        text = f"{prod.name} - ${prod.price}"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"PRODUCT_{prod.id}")
        ])
    
    if len(products) > 10:
        keyboard.append([
            InlineKeyboardButton(f"📌 共找到 {len(products)} 個商品", callback_data="NONE")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"🔎 搜尋結果：「{search_text}」",
        reply_markup=reply_markup
    )
    
    session.close()
    return True

def show_all_products(query, page=1):
    """顯示所有商品（分頁）"""
    session = SessionLocal()
    
    # 每頁顯示數量
    per_page = 10
    offset = (page - 1) * per_page
    
    # 獲取商品總數
    total_products = session.query(Product).filter_by(is_active=True).count()
    total_pages = (total_products + per_page - 1) // per_page
    
    # 獲取當前頁商品
    products = session.query(Product).filter_by(is_active=True).offset(offset).limit(per_page).all()
    
    if not products:
        query.message.edit_text("暫無商品")
        session.close()
        return
    
    keyboard = []
    for prod in products:
        text = f"{prod.name} - ${prod.price}"
        if prod.stock <= 0:
            text += " (已售完)"
        
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"PRODUCT_{prod.id}")
        ])
    
    # 分頁按鈕
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ 上一頁", callback_data=f"ALL_PRODUCTS_PAGE_{page-1}"))
    nav_row.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="NONE"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("➡️ 下一頁", callback_data=f"ALL_PRODUCTS_PAGE_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        f"📦 **所有商品** (第 {page} 頁，共 {total_pages} 頁)",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close() 