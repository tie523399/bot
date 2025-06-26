"""購物車處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models import SessionLocal, CartItem, Product
from utils.keyboards import get_cart_keyboard

def show_cart(update: Update, context: CallbackContext):
    """顯示購物車（改進版）"""
    user_id = update.effective_user.id
    session = SessionLocal()
    
    cart_items = session.query(CartItem).filter_by(user_id=user_id).all()
    
    if not cart_items:
        text = "🛒 您的購物車是空的"
        keyboard = [[
            InlineKeyboardButton("🛍️ 去購物", callback_data="CATEGORIES"),
            InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        else:
            update.message.reply_text(text, reply_markup=reply_markup)
        session.close()
        return
    
    # 計算總價和商品數量
    total_price = 0
    total_items = 0
    cart_text = "🛒 **購物車清單**\n\n"
    
    for item in cart_items:
        product = session.query(Product).get(item.product_id)
        if product:
            item_price = product.price
            # 計算選項價格
            for opt in item.options:
                item_price += opt.price
            
            subtotal = item_price * item.quantity
            total_price += subtotal
            total_items += item.quantity
            
            cart_text += f"📦 {product.name}\n"
            cart_text += f"   單價: ${item_price} × {item.quantity} = ${subtotal}\n"
            if item.options:
                opt_names = [opt.name for opt in item.options]
                cart_text += f"   選項: {', '.join(opt_names)}\n"
            cart_text += "\n"
    
    # 添加統計資訊
    cart_text += "─" * 20 + "\n"
    cart_text += f"📊 **統計資訊**\n"
    cart_text += f"商品種類：{len(cart_items)} 種\n"
    cart_text += f"商品總數：{total_items} 件\n"
    cart_text += f"💰 **總金額：${total_price}**"
    
    # 購買和返回按鈕
    keyboard = [
        [
            InlineKeyboardButton("💳 購買", callback_data="START_CHECKOUT"),
            InlineKeyboardButton("🔙 返回", callback_data="CART_LIST")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        update.callback_query.message.edit_text(cart_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        update.message.reply_text(cart_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    session.close()

def show_cart_list(query):
    """顯示購物車詳細列表（可編輯數量）"""
    user_id = query.from_user.id
    session = SessionLocal()
    
    cart_items = session.query(CartItem).filter_by(user_id=user_id).all()
    
    if not cart_items:
        query.message.edit_text("🛒 您的購物車是空的")
        session.close()
        return
    
    cart_text = "🛒 **購物車管理**\n\n"
    keyboard = []
    
    for item in cart_items:
        product = session.query(Product).get(item.product_id)
        if product:
            cart_text += f"📦 {product.name} (數量: {item.quantity})\n"
            
            # 增減數量按鈕
            row = [
                InlineKeyboardButton("➖", callback_data=f"CART_DEC_{item.id}"),
                InlineKeyboardButton(f"{item.quantity}", callback_data=f"CART_QTY_{item.id}"),
                InlineKeyboardButton("➕", callback_data=f"CART_INC_{item.id}"),
                InlineKeyboardButton("🗑️", callback_data=f"CART_DEL_{item.id}")
            ]
            keyboard.append(row)
    
    # 操作按鈕
    keyboard.append([
        InlineKeyboardButton("💳 結帳", callback_data="START_CHECKOUT"),
        InlineKeyboardButton("🗑️ 清空", callback_data="CLEAR_CART")
    ])
    keyboard.append([
        InlineKeyboardButton("🛍️ 繼續購物", callback_data="CATEGORIES"),
        InlineKeyboardButton("🔙 返回摘要", callback_data="VIEW_CART")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(cart_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    session.close()

def handle_cart_action(update: Update, context: CallbackContext):
    """處理購物車操作"""
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    session = SessionLocal()
    
    if data == "CLEAR_CART":
        session.query(CartItem).filter_by(user_id=user_id).delete()
        session.commit()
        session.close()
        query.message.edit_text("🗑️ 購物車已清空")
        return
    
    # 處理增減刪除
    if data.startswith("CART_"):
        action, item_id = data.replace("CART_", "").split("_", 1)
        item_id = int(item_id)
        
        cart_item = session.query(CartItem).filter_by(id=item_id, user_id=user_id).first()
        
        if not cart_item:
            session.close()
            query.message.edit_text("❌ 找不到該商品")
            return
        
        if action == "INC":
            product = session.query(Product).get(cart_item.product_id)
            if product and cart_item.quantity < product.stock:
                cart_item.quantity += 1
                session.commit()
            else:
                query.answer("庫存不足", show_alert=True)
        
        elif action == "DEC":
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                session.commit()
            else:
                query.answer("數量不能少於1", show_alert=True)
        
        elif action == "DEL":
            session.delete(cart_item)
            session.commit()
    
    session.close()
    
    # 重新顯示購物車
    show_cart(update, context)

def add_to_cart(product_id: int, user_id: int, quantity: int = 1, options: list = None):
    """添加商品到購物車（加強版，含庫存檢查）"""
    session = SessionLocal()
    
    # 檢查商品是否存在和有足夠庫存
    product = session.query(Product).get(product_id)
    if not product:
        session.close()
        return False, "商品不存在"
    
    if not product.is_active:
        session.close()
        return False, "商品已下架"
    
    # 計算購物車中已有的數量
    existing_cart = session.query(CartItem).filter_by(
        user_id=user_id,
        product_id=product_id
    ).first()
    
    current_qty = existing_cart.quantity if existing_cart else 0
    total_qty = current_qty + quantity
    
    # 檢查庫存
    if total_qty > product.stock:
        available = product.stock - current_qty
        session.close()
        if available <= 0:
            return False, f"商品庫存不足（庫存：{product.stock}）"
        else:
            return False, f"庫存不足，最多還能加入 {available} 件"
    
    # 檢查購買限制
    if hasattr(product, 'max_per_order') and product.max_per_order:
        if total_qty > product.max_per_order:
            session.close()
            return False, f"此商品每單限購 {product.max_per_order} 件"
    
    # 添加到購物車
    if existing_cart:
        existing_cart.quantity = total_qty
    else:
        cart_item = CartItem(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity
        )
        session.add(cart_item)
    
    # 添加選項
    if options and existing_cart:
        for opt in options:
            if opt not in existing_cart.options:
                existing_cart.options.append(opt)
    elif options and not existing_cart:
        cart_item.options = options
    
    session.commit()
    session.close()
    
    return True, f"已加入購物車（共 {total_qty} 件）"

def validate_cart(user_id: int):
    """驗證購物車商品的有效性和庫存"""
    session = SessionLocal()
    cart_items = session.query(CartItem).filter_by(user_id=user_id).all()
    
    issues = []
    updated = False
    
    for item in cart_items:
        product = session.query(Product).get(item.product_id)
        
        if not product or not product.is_active:
            # 商品已下架，從購物車移除
            session.delete(item)
            updated = True
            issues.append(f"「{product.name if product else '未知商品'}」已下架")
            continue
        
        if item.quantity > product.stock:
            # 庫存不足，調整數量
            if product.stock == 0:
                session.delete(item)
                issues.append(f"「{product.name}」已售罄")
            else:
                old_qty = item.quantity
                item.quantity = product.stock
                issues.append(f"「{product.name}」庫存不足，數量調整為 {product.stock} 件")
            updated = True
    
    if updated:
        session.commit()
    
    session.close()
    return issues

def check_out_of_stock_items(user_id: int):
    """檢查購物車中的缺貨商品"""
    session = SessionLocal()
    cart_items = session.query(CartItem).filter_by(user_id=user_id).all()
    
    out_of_stock = []
    insufficient = []
    
    for item in cart_items:
        product = session.query(Product).get(item.product_id)
        if product:
            if product.stock == 0:
                out_of_stock.append(product.name)
            elif item.quantity > product.stock:
                insufficient.append({
                    'name': product.name,
                    'requested': item.quantity,
                    'available': product.stock
                })
    
    session.close()
    return out_of_stock, insufficient 