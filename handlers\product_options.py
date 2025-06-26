"""商品選項處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models import SessionLocal, Product, Option, CartItem

def show_product_options(query, product_id, user_id):
    """顯示商品選項"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    options = product.options
    
    if not options:
        # 沒有選項，直接加入購物車
        from handlers.cart import add_to_cart
        if add_to_cart(product_id, user_id):
            query.answer("✅ 已加入購物車", show_alert=True)
            show_add_success(query, product)
        session.close()
        return
    
    # 有選項，顯示選項選擇
    keyboard = []
    
    # 儲存選擇狀態
    if 'selected_options' not in query.message.reply_markup:
        selected_options = set()
    else:
        selected_options = set()  # 從之前的選擇恢復
    
    for opt in options:
        is_selected = opt.id in selected_options
        check = "✅" if is_selected else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                f"{check} {opt.name} (+${opt.price})",
                callback_data=f"TOGGLE_OPT_{product_id}_{opt.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🛒 確認加入購物車", callback_data=f"CONFIRM_ADD_{product_id}"),
        InlineKeyboardButton("❌ 取消", callback_data=f"PROD_{product_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"**{product.name}**\n\n"
    text += "請選擇商品選項（可多選）："
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    session.close()

def toggle_option_selection(query, data):
    """切換選項選擇狀態"""
    parts = data.replace("TOGGLE_OPT_", "").split("_")
    product_id = int(parts[0])
    option_id = int(parts[1])
    
    # 從按鈕狀態中讀取已選擇的選項
    selected_options = set()
    current_markup = query.message.reply_markup
    
    if current_markup and current_markup.inline_keyboard:
        for row in current_markup.inline_keyboard:
            for button in row:
                if button.callback_data and button.callback_data.startswith("TOGGLE_OPT_"):
                    if "✅" in button.text:
                        # 提取選項ID
                        btn_data = button.callback_data.split("_")
                        if len(btn_data) >= 4:
                            selected_options.add(int(btn_data[3]))
    
    # 切換當前選項
    if option_id in selected_options:
        selected_options.remove(option_id)
    else:
        selected_options.add(option_id)
    
    # 重新生成鍵盤
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    keyboard = []
    for opt in product.options:
        is_selected = opt.id in selected_options
        check = "✅" if is_selected else "⬜"
        keyboard.append([
            InlineKeyboardButton(
                f"{check} {opt.name} (+${opt.price})",
                callback_data=f"TOGGLE_OPT_{product_id}_{opt.id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🛒 確認加入購物車", callback_data=f"CONFIRM_ADD_{product_id}_{','.join(map(str, selected_options))}"),
        InlineKeyboardButton("❌ 取消", callback_data=f"PROD_{product_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # 計算總價
    base_price = product.price
    option_price = sum(session.query(Option).get(opt_id).price for opt_id in selected_options)
    total_price = base_price + option_price
    
    text = f"**{product.name}**\n\n"
    text += "請選擇商品選項（可多選）：\n\n"
    text += f"💰 總價：${total_price}"
    
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    session.close()
    query.answer()

def confirm_add_to_cart(query, product_id, selected_options):
    """確認加入購物車"""
    user_id = query.from_user.id
    session = SessionLocal()
    
    product = session.query(Product).get(product_id)
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    # 獲取選中的選項對象
    options = []
    for opt_id in selected_options:
        option = session.query(Option).get(opt_id)
        if option:
            options.append(option)
    
    # 加入購物車（使用更新的函數）
    from handlers.cart import add_to_cart
    success, message = add_to_cart(product_id, user_id, 1, options)
    
    if success:
        keyboard = [
            [
                InlineKeyboardButton("繼續購物", callback_data="CATEGORIES"),
                InlineKeyboardButton("查看購物車", callback_data="VIEW_CART")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.edit_text(
            f"✅ {message}\n\n商品：{product.name}",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [
                InlineKeyboardButton("返回商品", callback_data=f"PRODUCT_{product_id}"),
                InlineKeyboardButton("查看購物車", callback_data="VIEW_CART")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.edit_text(
            f"❌ {message}",
            reply_markup=reply_markup
        )
    
    session.close()

def show_add_success(query, product):
    """顯示加入成功訊息"""
    keyboard = [
        [
            InlineKeyboardButton("🛍️ 查看購物車", callback_data="VIEW_CART"),
            InlineKeyboardButton("🛒 繼續購物", callback_data=f"CAT_{product.category_id}")
        ],
        [
            InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        f"✅ 已將「{product.name}」加入購物車！\n\n請選擇下一步：",
        reply_markup=reply_markup
    ) 