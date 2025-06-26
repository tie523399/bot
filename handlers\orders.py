"""訂單處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, Order, OrderItem, CartItem, Product, Store, PaymentLog
from config import ADMIN_IDS
from datetime import datetime
import random
import string
import re
from handlers.cart import validate_cart

# 結帳流程狀態
WAITING_NAME = 1
WAITING_PHONE = 2
WAITING_STORE = 3

def start_simple_checkout(query):
    """開始簡化的結帳流程"""
    user_id = query.from_user.id
    
    # 驗證購物車
    issues = validate_cart(user_id)
    if issues:
        text = "⚠️ **購物車有以下變更：**\n\n"
        for issue in issues:
            text += f"• {issue}\n"
        text += "\n請重新檢查購物車"
        query.message.edit_text(text, parse_mode='Markdown')
        return ConversationHandler.END
    
    query.message.edit_text(
        "📝 **開始結帳**\n\n"
        "請輸入您的姓名："
    )
    query.answer()
    
    return WAITING_NAME

def process_name(update: Update, context: CallbackContext):
    """處理姓名輸入（含驗證）"""
    name = update.message.text.strip()
    
    # 姓名驗證
    if len(name) < 2:
        update.message.reply_text("❌ 姓名至少需要2個字，請重新輸入：")
        return WAITING_NAME
    
    if len(name) > 20:
        update.message.reply_text("❌ 姓名不能超過20個字，請重新輸入：")
        return WAITING_NAME
    
    # 檢查是否包含特殊字符
    if not re.match(r'^[\u4e00-\u9fa5a-zA-Z\s]+$', name):
        update.message.reply_text("❌ 姓名只能包含中文、英文和空格，請重新輸入：")
        return WAITING_NAME
    
    context.user_data['customer_name'] = name
    update.message.reply_text(
        f"✅ 姓名：{name}\n\n"
        "請輸入您的手機號碼（格式：0912345678）："
    )
    
    return WAITING_PHONE

def process_phone(update: Update, context: CallbackContext):
    """處理電話輸入（含驗證）"""
    phone = update.message.text.strip()
    
    # 移除可能的分隔符號
    phone = phone.replace('-', '').replace(' ', '')
    
    # 電話驗證
    if not re.match(r'^09\d{8}$', phone):
        update.message.reply_text(
            "❌ 手機號碼格式錯誤\n"
            "請輸入10碼手機號碼（格式：0912345678）："
        )
        return WAITING_PHONE
    
    context.user_data['customer_phone'] = phone
    
    # 提供7-11店號查詢連結
    keyboard = [[
        InlineKeyboardButton(
            "🔍 查詢7-11門市", 
            url="https://emap.pcsc.com.tw/emap.aspx"
        )
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"✅ 電話：{phone}\n\n"
        "請點擊下方按鈕查詢7-11門市店號\n"
        "查詢完成後，請直接輸入店號：",
        reply_markup=reply_markup
    )
    
    return WAITING_STORE

def process_store(update: Update, context: CallbackContext):
    """處理店號輸入並建立訂單"""
    user_id = update.effective_user.id
    store_code = update.message.text.strip()
    
    # 基本驗證店號
    if not store_code:
        update.message.reply_text("❌ 請輸入有效的店號")
        return WAITING_STORE
    
    session = SessionLocal()
    
    # 再次驗證購物車
    issues = validate_cart(user_id)
    if issues:
        text = "⚠️ **庫存已變更，無法完成訂單：**\n\n"
        for issue in issues:
            text += f"• {issue}\n"
        update.message.reply_text(text, parse_mode='Markdown')
        session.close()
        return ConversationHandler.END
    
    # 生成訂單號：TDR+YYYYMMDD+時分+隨機2碼
    now = datetime.now()
    order_no = f"TDR{now.strftime('%Y%m%d%H%M')}{random.randint(10, 99)}"
    
    # 創建訂單
    order = Order(
        order_no=order_no,
        user_id=user_id,
        store_code=store_code,
        status='待處理',
        payment_method='cod',
        payment_status='pending',
        customer_name=context.user_data['customer_name'],
        customer_phone=context.user_data['customer_phone'],
        created_at=now
    )
    
    session.add(order)
    session.flush()
    
    # 轉移購物車項目到訂單
    cart_items = session.query(CartItem).filter_by(user_id=user_id).all()
    total_price = 0
    order_details = []
    
    for cart_item in cart_items:
        product = session.query(Product).get(cart_item.product_id)
        if not product:
            continue
        
        # 最後檢查庫存
        if cart_item.quantity > product.stock:
            session.rollback()
            update.message.reply_text(
                f"❌ 商品「{product.name}」庫存不足，無法完成訂單"
            )
            session.close()
            return ConversationHandler.END
        
        # 計算價格
        item_price = product.price
        for opt in cart_item.options:
            item_price += opt.price
        
        subtotal = item_price * cart_item.quantity
        total_price += subtotal
        
        # 創建訂單項目
        order_item = OrderItem(
            order_id=order.id,
            product_id=cart_item.product_id,
            quantity=cart_item.quantity,
            price=item_price
        )
        
        # 複製選項
        for opt in cart_item.options:
            order_item.options.append(opt)
        
        session.add(order_item)
        
        # 扣減庫存
        product.stock -= cart_item.quantity
        
        # 記錄訂單明細
        order_details.append({
            'name': product.name,
            'quantity': cart_item.quantity,
            'price': item_price,
            'subtotal': subtotal
        })
    
    # 更新訂單總金額
    order.payment_amount = total_price
    
    # 清空購物車
    session.query(CartItem).filter_by(user_id=user_id).delete()
    
    session.commit()
    
    # 發送確認訊息給客戶
    confirmation_msg = f"""✅ **訂單已成功建立！**

已通知客服處理，稍後會給您7-11訂單號追蹤

📋 訂單編號：`{order_no}`
👤 姓名：{order.customer_name}
📱 電話：{order.customer_phone}
🏪 7-11店號：{store_code}
💰 總金額：${total_price}
📅 下單時間：{order.created_at.strftime('%Y-%m-%d %H:%M')}

感謝您的購買！"""

    update.message.reply_text(confirmation_msg, parse_mode='Markdown')
    
    # 通知所有管理員（商家）
    admin_msg = f"""🔔 **新訂單通知 - 請趕快出貨**

📋 訂單編號：`{order_no}`
👤 客戶：{order.customer_name}
📱 電話：{order.customer_phone}
🏪 7-11店號：{store_code}
💰 金額：${total_price}

**訂單明細：**
"""
    
    for item in order_details:
        admin_msg += f"• {item['name']} x{item['quantity']} = ${item['subtotal']}\n"
    
    admin_msg += f"\n⏰ 下單時間：{order.created_at.strftime('%Y-%m-%d %H:%M')}"
    admin_msg += "\n\n**請盡快處理此訂單！**"
    
    # 發送給所有管理員
    for admin_id in ADMIN_IDS:
        try:
            context.bot.send_message(admin_id, admin_msg, parse_mode='Markdown')
        except:
            pass
    
    session.close()
    
    # 清理 context
    context.user_data.clear()
    
    # 回到主選單
    from utils.keyboards import get_main_menu_keyboard
    is_admin = user_id in ADMIN_IDS
    keyboard = get_main_menu_keyboard(is_admin)
    update.message.reply_text("請選擇功能：", reply_markup=keyboard)
    
    return ConversationHandler.END

def checkout(update: Update, context: CallbackContext):
    """開始結帳流程（兼容舊版）"""
    if update.callback_query:
        return start_simple_checkout(update.callback_query)
    else:
        # 文字命令版本
        user_id = update.effective_user.id
        
        # 驗證購物車
        issues = validate_cart(user_id)
        if issues:
            text = "⚠️ **購物車有以下變更：**\n\n"
            for issue in issues:
                text += f"• {issue}\n"
            text += "\n請重新檢查購物車"
            update.message.reply_text(text, parse_mode='Markdown')
            return ConversationHandler.END
        
        update.message.reply_text(
            "📝 **開始結帳**\n\n"
            "請輸入您的姓名："
        )
        
        return WAITING_NAME

def cancel_order(update: Update, context: CallbackContext):
    """取消訂單處理"""
    context.user_data.clear()
    
    text = "❌ 已取消結帳"
    
    if update.callback_query:
        update.callback_query.answer()
        update.callback_query.message.edit_text(text)
    else:
        update.message.reply_text(text)
    
    return ConversationHandler.END

def start_checkout(update: Update, context: CallbackContext):
    """開始結帳（callback版本）"""
    query = update.callback_query
    query.answer()
    
    return start_simple_checkout(query)

def show_my_orders(update: Update, context: CallbackContext):
    """顯示用戶訂單"""
    user_id = update.effective_user.id
    session = SessionLocal()
    
    orders = session.query(Order).filter_by(user_id=user_id).order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        update.message.reply_text("📦 您還沒有任何訂單")
        session.close()
        return
    
    text = "📦 **我的訂單**\n\n"
    
    for order in orders:
        text += f"📋 訂單號: `{order.order_no}`\n"
        text += f"🏪 門市: {order.store_code}\n"
        text += f"📅 時間: {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        text += f"📦 狀態: **{order.status}**\n"
        
        # 計算總價
        total = 0
        for item in order.items:
            total += item.price * item.quantity
        
        text += f"💰 金額: ${total}\n"
        text += "─" * 20 + "\n\n"
    
    keyboard = [[
        InlineKeyboardButton("📋 查看更多", callback_data="MORE_ORDERS")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def view_my_orders_inline(query):
    """顯示用戶訂單（內聯版本）"""
    user_id = query.from_user.id
    session = SessionLocal()
    
    orders = session.query(Order).filter_by(user_id=user_id).order_by(Order.created_at.desc()).limit(10).all()
    
    if not orders:
        query.message.edit_text("📦 您還沒有任何訂單")
        session.close()
        return
    
    keyboard = []
    
    for order in orders:
        # 計算總價
        total = 0
        for item in order.items:
            total += item.price * item.quantity
        
        text = f"{order.order_no} - ${total} ({order.status})"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"VIEW_ORDER_{order.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回主選單", callback_data="MAIN_MENU")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        "📦 **我的訂單**\n\n選擇訂單查看詳情：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def view_order_detail(query, order_id):
    """顯示訂單詳情"""
    user_id = query.from_user.id
    session = SessionLocal()
    
    order = session.query(Order).filter_by(id=order_id, user_id=user_id).first()
    
    if not order:
        query.message.edit_text("❌ 訂單不存在")
        session.close()
        return
    
    text = f"📋 **訂單詳情**\n\n"
    text += f"訂單號：`{order.order_no}`\n"
    text += f"下單時間：{order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    text += f"取貨門市：{order.store_code}\n"
    text += f"訂單狀態：**{order.status}**\n"
    
    if order.tracking_number:
        text += f"追蹤單號：`{order.tracking_number}`\n"
    
    text += "\n**商品明細：**\n"
    
    total = 0
    for item in order.items:
        product = session.query(Product).get(item.product_id)
        if product:
            subtotal = item.price * item.quantity
            total += subtotal
            text += f"• {product.name} x{item.quantity} = ${subtotal}\n"
            
            if item.options:
                opt_names = [opt.name for opt in item.options]
                text += f"  選項：{', '.join(opt_names)}\n"
    
    text += f"\n💰 **總計：${total}**"
    
    keyboard = [[
        InlineKeyboardButton("🔙 返回訂單列表", callback_data="MY_ORDERS"),
        InlineKeyboardButton("🔙 主選單", callback_data="MAIN_MENU")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close() 