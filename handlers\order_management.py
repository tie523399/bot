"""訂單狀態管理處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models import SessionLocal, Order
from config import ADMIN_IDS

ORDER_STATUSES = {
    'pending': '待確認',
    'confirmed': '已確認',
    'shipped': '已出貨',
    'arrived': '已到店',
    'completed': '已完成',
    'cancelled': '已取消'
}

def order_management_menu(update: Update, context: CallbackContext):
    """訂單管理主選單"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ 您沒有權限")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📋 待處理訂單", callback_data="ORDER_PENDING"),
            InlineKeyboardButton("🚚 已出貨訂單", callback_data="ORDER_SHIPPED")
        ],
        [
            InlineKeyboardButton("📦 所有訂單", callback_data="ORDER_ALL"),
            InlineKeyboardButton("🔍 搜尋訂單", callback_data="ORDER_SEARCH")
        ],
        [
            InlineKeyboardButton("📊 訂單統計", callback_data="ORDER_STATS"),
            InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message or update.callback_query.message
    message.reply_text(
        "📦 **訂單管理**\n\n請選擇操作：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def show_orders_by_status(query, status=None):
    """顯示特定狀態的訂單"""
    session = SessionLocal()
    
    if status:
        orders = session.query(Order).filter_by(status=status).order_by(Order.created_at.desc()).limit(20).all()
        title = f"📋 {ORDER_STATUSES.get(status, status)} 訂單"
    else:
        orders = session.query(Order).order_by(Order.created_at.desc()).limit(20).all()
        title = "📦 所有訂單"
    
    if not orders:
        query.message.edit_text(f"{title}\n\n暫無訂單")
        session.close()
        return
    
    keyboard = []
    for order in orders:
        text = f"{order.order_no} - {order.status}"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"ORDER_VIEW_{order.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="ORDER_MGMT")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        f"{title}\n\n點擊查看訂單詳情：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_order_detail(query, order_id):
    """顯示訂單詳情"""
    session = SessionLocal()
    order = session.query(Order).get(order_id)
    
    if not order:
        query.message.edit_text("訂單不存在")
        session.close()
        return
    
    # 計算訂單總額
    total = 0
    items_text = ""
    for item in order.items:
        total += item.price * item.quantity
        items_text += f"• {item.product.name if item.product else 'Unknown'} x{item.quantity} = ${item.price * item.quantity}\n"
    
    text = f"**訂單詳情**\n\n"
    text += f"📋 訂單號：{order.order_no}\n"
    text += f"👤 用戶ID：{order.user_id}\n"
    text += f"📅 下單時間：{order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
    text += f"🏪 取貨門市：{order.store_code}\n"
    text += f"📦 狀態：**{order.status}**\n"
    text += f"💰 總金額：${total}\n\n"
    text += f"**商品明細：**\n{items_text}"
    
    keyboard = [
        [
            InlineKeyboardButton("✏️ 更改狀態", callback_data=f"ORDER_STATUS_{order_id}"),
            InlineKeyboardButton("📤 匯出", callback_data=f"ORDER_EXPORT_{order_id}")
        ],
        [
            InlineKeyboardButton("📨 通知客戶", callback_data=f"ORDER_NOTIFY_{order_id}"),
            InlineKeyboardButton("🔙 返回列表", callback_data="ORDER_ALL")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def change_order_status_menu(query, order_id):
    """更改訂單狀態選單"""
    session = SessionLocal()
    order = session.query(Order).get(order_id)
    
    if not order:
        query.message.edit_text("訂單不存在")
        session.close()
        return
    
    keyboard = []
    
    # 生成狀態按鈕
    for status_key, status_name in ORDER_STATUSES.items():
        if status_key == 'shipped':
            # 出貨需要輸入單號
            keyboard.append([
                InlineKeyboardButton(
                    f"🚚 {status_name}", 
                    callback_data=f"ORDER_SHIP_{order_id}"
                )
            ])
        else:
            keyboard.append([
                InlineKeyboardButton(
                    status_name, 
                    callback_data=f"ORDER_SET_{order_id}_{status_key}"
                )
            ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data=f"ORDER_VIEW_{order_id}")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        f"**更改訂單狀態**\n\n"
        f"訂單號：{order.order_no}\n"
        f"當前狀態：{order.status}\n\n"
        f"請選擇新狀態：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def start_ship_order(query, order_id):
    """開始出貨流程"""
    context = query._context
    context.user_data['shipping_order'] = order_id
    
    query.message.reply_text(
        "請輸入出貨追蹤單號："
    )
    query.answer()

def update_order_status(query, order_id, new_status, tracking_number=None):
    """更新訂單狀態"""
    session = SessionLocal()
    order = session.query(Order).get(order_id)
    
    if not order:
        query.message.edit_text("訂單不存在")
        session.close()
        return
    
    old_status = order.status
    order.status = ORDER_STATUSES.get(new_status, new_status)
    
    # 如果有追蹤單號，保存
    if tracking_number:
        order.tracking_number = tracking_number
    
    session.commit()
    
    # 通知客戶
    notify_text = f"📦 您的訂單 {order.order_no} 狀態已更新：\n"
    notify_text += f"{old_status} → {order.status}"
    
    if tracking_number:
        notify_text += f"\n\n🚚 追蹤單號：{tracking_number}"
    
    if new_status == 'arrived':
        notify_text += "\n\n🏪 您的商品已到達取貨門市，請盡快取貨！"
    
    try:
        query.bot.send_message(order.user_id, notify_text)
        result_text = f"✅ 訂單狀態已更新並通知客戶"
    except:
        result_text = f"✅ 訂單狀態已更新（通知客戶失敗）"
    
    keyboard = [[
        InlineKeyboardButton("查看訂單", callback_data=f"ORDER_VIEW_{order_id}"),
        InlineKeyboardButton("返回列表", callback_data="ORDER_ALL")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        result_text,
        reply_markup=reply_markup
    )
    
    session.close()

def notify_customer(query, order_id):
    """發送自定義通知給客戶"""
    context = query._context
    context.user_data['notify_order'] = order_id
    
    query.message.reply_text(
        "請輸入要發送給客戶的訊息："
    )
    query.answer()

def handle_shipping_number(update: Update, context: CallbackContext):
    """處理出貨單號輸入"""
    order_id = context.user_data.get('shipping_order')
    if not order_id:
        return
    
    tracking_number = update.message.text.strip()
    
    # 清除狀態
    context.user_data.pop('shipping_order', None)
    
    # 創建一個假的query對象來重用update_order_status
    class FakeQuery:
        def __init__(self, message, bot):
            self.message = message
            self.bot = bot
            self._context = context
        
        def answer(self):
            pass
    
    fake_query = FakeQuery(update.message, context.bot)
    update_order_status(fake_query, order_id, 'shipped', tracking_number)

def handle_customer_notification(update: Update, context: CallbackContext):
    """處理客戶通知"""
    order_id = context.user_data.get('notify_order')
    if not order_id:
        return
    
    message_text = update.message.text.strip()
    
    # 清除狀態
    context.user_data.pop('notify_order', None)
    
    session = SessionLocal()
    order = session.query(Order).get(order_id)
    
    if not order:
        update.message.reply_text("訂單不存在")
        session.close()
        return
    
    try:
        # 發送訊息給客戶
        context.bot.send_message(
            order.user_id,
            f"📢 **訂單通知**\n\n"
            f"訂單編號：{order.order_no}\n\n"
            f"{message_text}"
        )
        
        update.message.reply_text("✅ 已成功發送通知給客戶")
    except:
        update.message.reply_text("❌ 發送通知失敗（客戶可能已封鎖機器人）")
    
    session.close() 