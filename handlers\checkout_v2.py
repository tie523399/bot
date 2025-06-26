"""
結帳流程處理器 v2 - 使用 ConversationHandler
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, CartItem, Product, Order, OrderItem, User
from datetime import datetime
import re
import random
import string

# 狀態定義
CHECKOUT_NAME = 6
CHECKOUT_PHONE = 7
CHECKOUT_STORE = 8

def start_checkout(update: Update, context: CallbackContext):
    """開始結帳流程"""
    user_id = update.effective_user.id
    
    session = SessionLocal()
    cart_items = session.query(CartItem).filter_by(user_id=user_id).all()
    
    if not cart_items:
        text = "❌ 購物車是空的，無法結帳"
        keyboard = [[
            InlineKeyboardButton("🛍️ 去購物", callback_data="BROWSE"),
            InlineKeyboardButton("🏠 返回主選單", callback_data="MAIN_MENU")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            update.message.reply_text(text, reply_markup=reply_markup)
        else:
            update.callback_query.answer()
            update.callback_query.message.edit_text(text, reply_markup=reply_markup)
        
        session.close()
        return ConversationHandler.END
    
    # 檢查庫存
    out_of_stock = []
    insufficient = []
    total_price = 0
    
    for item in cart_items:
        product = session.query(Product).get(item.product_id)
        if not product or not product.is_active:
            out_of_stock.append(item.product.name if item.product else "未知商品")
        elif product.stock < item.quantity:
            insufficient.append({
                'name': product.name,
                'requested': item.quantity,
                'available': product.stock
            })
        else:
            total_price += product.price * item.quantity
    
    # 如果有問題商品
    if out_of_stock or insufficient:
        text = "❌ **無法結帳**\n\n"
        
        if out_of_stock:
            text += "**已下架商品：**\n"
            for name in out_of_stock:
                text += f"• {name}\n"
            text += "\n"
        
        if insufficient:
            text += "**庫存不足：**\n"
            for item in insufficient:
                text += f"• {item['name']} (需要 {item['requested']}，庫存 {item['available']})\n"
        
        text += "\n請調整購物車後再試"
        
        keyboard = [[
            InlineKeyboardButton("🛒 查看購物車", callback_data="VIEW_CART"),
            InlineKeyboardButton("❌ 取消", callback_data="CANCEL")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            update.callback_query.answer()
            update.callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        session.close()
        return ConversationHandler.END
    
    # 保存購物車資訊
    context.user_data['checkout_items'] = []
    for item in cart_items:
        product = session.query(Product).get(item.product_id)
        context.user_data['checkout_items'].append({
            'product_id': product.id,
            'product_name': product.name,
            'price': product.price,
            'quantity': item.quantity,
            'subtotal': product.price * item.quantity
        })
    
    context.user_data['total_price'] = total_price
    session.close()
    
    # 開始收集資訊
    text = f"""💳 **開始結帳**

訂單金額：${total_price}

**步驟 1/3**
請輸入您的姓名（真實姓名，2-10個中文字）：

💡 輸入 /cancel 可隨時取消"""
    
    if update.message:
        update.message.reply_text(text, parse_mode='Markdown')
    else:
        update.callback_query.answer()
        update.callback_query.message.edit_text(text, parse_mode='Markdown')
    
    return CHECKOUT_NAME

def process_name(update: Update, context: CallbackContext):
    """處理姓名輸入"""
    name = update.message.text.strip()
    
    # 驗證姓名（2-10個中文字）
    if not re.match(r'^[\u4e00-\u9fa5]{2,10}$', name):
        update.message.reply_text(
            "❌ 姓名格式不正確\n"
            "請輸入2-10個中文字的真實姓名："
        )
        return CHECKOUT_NAME
    
    context.user_data['customer_name'] = name
    
    update.message.reply_text(
        f"✅ 姓名：{name}\n\n"
        "**步驟 2/3**\n"
        "請輸入您的手機號碼（格式：09XXXXXXXX）："
    )
    
    return CHECKOUT_PHONE

def process_phone(update: Update, context: CallbackContext):
    """處理電話輸入"""
    phone = update.message.text.strip()
    
    # 驗證電話格式
    if not re.match(r'^09\d{8}$', phone):
        update.message.reply_text(
            "❌ 電話格式不正確\n"
            "請輸入正確格式（09XXXXXXXX）："
        )
        return CHECKOUT_PHONE
    
    context.user_data['customer_phone'] = phone
    
    update.message.reply_text(
        f"✅ 電話：{phone}\n\n"
        "**步驟 3/3**\n"
        "請選擇 7-11 門市：\n\n"
        "1️⃣ 點擊下方連結查詢門市\n"
        "https://emap.pcsc.com.tw/\n\n"
        "2️⃣ 查詢到門市後，請輸入門市代號（6位數字）："
    )
    
    return CHECKOUT_STORE

def process_store(update: Update, context: CallbackContext):
    """處理門市代號輸入"""
    store_code = update.message.text.strip()
    
    # 驗證門市代號（6位數字）
    if not re.match(r'^\d{6}$', store_code):
        update.message.reply_text(
            "❌ 門市代號格式不正確\n"
            "請輸入6位數字的門市代號："
        )
        return CHECKOUT_STORE
    
    context.user_data['store_code'] = store_code
    
    # 生成訂單編號
    order_no = generate_order_no()
    
    # 創建訂單
    return confirm_order(update, context, order_no)

def generate_order_no():
    """生成訂單編號"""
    # 格式：TDR + 日期時間 + 3位隨機碼
    now = datetime.now()
    date_str = now.strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.digits, k=3))
    return f"TDR{date_str}{random_str}"

def confirm_order(update: Update, context: CallbackContext, order_no):
    """確認並創建訂單"""
    user_id = update.effective_user.id
    
    session = SessionLocal()
    
    try:
        # 創建訂單
        order = Order(
            order_no=order_no,
            user_id=user_id,
            customer_name=context.user_data['customer_name'],
            customer_phone=context.user_data['customer_phone'],
            store_code=context.user_data['store_code'],
            status='待付款',
            payment_amount=context.user_data['total_price'],
            created_at=datetime.now()
        )
        session.add(order)
        session.flush()
        
        # 創建訂單項目並更新庫存
        for item in context.user_data['checkout_items']:
            # 創建訂單項目
            order_item = OrderItem(
                order_id=order.id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
            session.add(order_item)
            
            # 更新商品庫存
            product = session.query(Product).get(item['product_id'])
            if product:
                product.stock -= item['quantity']
        
        # 清空購物車
        session.query(CartItem).filter_by(user_id=user_id).delete()
        
        session.commit()
        
        # 發送成功訊息
        text = f"""✅ **訂單建立成功！**

📋 訂單編號：{order_no}
👤 姓名：{context.user_data['customer_name']}
📱 電話：{context.user_data['customer_phone']}
🏪 門市：{context.user_data['store_code']}
💰 金額：${context.user_data['total_price']}
📅 時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}

⏰ 請於24小時內至門市取貨付款

感謝您的購買！"""
        
        keyboard = [[
            InlineKeyboardButton("📦 查看訂單", callback_data=f"VIEW_ORDER_{order.id}"),
            InlineKeyboardButton("🏠 返回主選單", callback_data="MAIN_MENU")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # 通知管理員
        notify_admins_new_order(session, order, context)
        
        # 清理用戶數據
        context.user_data.clear()
        
        session.close()
        return ConversationHandler.END
        
    except Exception as e:
        session.rollback()
        session.close()
        
        update.message.reply_text(
            f"❌ 訂單建立失敗：{str(e)}\n"
            "請稍後再試或聯繫客服"
        )
        
        return ConversationHandler.END

def notify_admins_new_order(session, order, context):
    """通知管理員有新訂單"""
    from config import ADMIN_IDS
    
    # 構建訂單詳情
    items_text = ""
    for item in context.user_data['checkout_items']:
        items_text += f"• {item['product_name']} × {item['quantity']} = ${item['subtotal']}\n"
    
    message = f"""🔔 **新訂單通知**

訂單編號：{order.order_no}
客戶：{order.customer_name}
電話：{order.customer_phone}
門市：{order.store_code}

**商品明細：**
{items_text}
總金額：${order.payment_amount}

⚡ 請趕快出貨！"""
    
    # 發送給所有管理員
    for admin_id in ADMIN_IDS:
        try:
            context.bot.send_message(
                chat_id=admin_id,
                text=message,
                parse_mode='Markdown'
            )
        except:
            pass 