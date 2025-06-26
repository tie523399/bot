"""銷售統計和推播處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models import SessionLocal, Order, OrderItem, Product, User
from config import ADMIN_IDS
from sqlalchemy import func, extract
from datetime import datetime, timedelta
import calendar

def show_statistics_menu(update: Update, context: CallbackContext):
    """統計主選單（別名）"""
    return statistics_menu(update, context)

def statistics_menu(update: Update, context: CallbackContext):
    """統計主選單"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ 您沒有權限")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📊 今日統計", callback_data="STATS_TODAY"),
            InlineKeyboardButton("📈 本月統計", callback_data="STATS_MONTH")
        ],
        [
            InlineKeyboardButton("🏆 熱銷商品", callback_data="STATS_HOT"),
            InlineKeyboardButton("📉 銷售趨勢", callback_data="STATS_TREND")
        ],
        [
            InlineKeyboardButton("📢 推播訊息", callback_data="BROADCAST"),
            InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message or update.callback_query.message
    message.reply_text(
        "📊 **銷售統計**\n\n請選擇操作：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def show_today_stats(query):
    """顯示今日統計"""
    session = SessionLocal()
    today = datetime.now().date()
    
    # 今日訂單
    today_orders = session.query(Order).filter(
        func.date(Order.created_at) == today
    ).all()
    
    # 計算統計數據
    order_count = len(today_orders)
    total_revenue = 0
    product_sold = 0
    
    for order in today_orders:
        for item in order.items:
            total_revenue += item.price * item.quantity
            product_sold += item.quantity
    
    # 昨日對比
    yesterday = today - timedelta(days=1)
    yesterday_orders = session.query(Order).filter(
        func.date(Order.created_at) == yesterday
    ).all()
    
    yesterday_revenue = 0
    for order in yesterday_orders:
        for item in order.items:
            yesterday_revenue += item.price * item.quantity
    
    revenue_change = total_revenue - yesterday_revenue
    change_percent = (revenue_change / yesterday_revenue * 100) if yesterday_revenue > 0 else 0
    
    text = f"📊 **今日統計**\n"
    text += f"日期：{today}\n\n"
    text += f"📦 訂單數：{order_count}\n"
    text += f"🛍️ 售出商品：{product_sold} 件\n"
    text += f"💰 營業額：${total_revenue}\n\n"
    
    if revenue_change >= 0:
        text += f"📈 較昨日：+${revenue_change} (+{change_percent:.1f}%)"
    else:
        text += f"📉 較昨日：${revenue_change} ({change_percent:.1f}%)"
    
    keyboard = [[
        InlineKeyboardButton("📊 查看其他統計", callback_data="STATS_MENU"),
        InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_month_stats(query):
    """顯示本月統計"""
    session = SessionLocal()
    now = datetime.now()
    current_month = now.month
    current_year = now.year
    
    # 本月訂單
    month_orders = session.query(Order).filter(
        extract('month', Order.created_at) == current_month,
        extract('year', Order.created_at) == current_year
    ).all()
    
    # 計算統計數據
    order_count = len(month_orders)
    total_revenue = 0
    product_sold = 0
    daily_revenue = {}
    
    for order in month_orders:
        order_date = order.created_at.date()
        if order_date not in daily_revenue:
            daily_revenue[order_date] = 0
        
        for item in order.items:
            revenue = item.price * item.quantity
            total_revenue += revenue
            daily_revenue[order_date] += revenue
            product_sold += item.quantity
    
    # 找出最佳和最差日期
    if daily_revenue:
        best_day = max(daily_revenue, key=daily_revenue.get)
        worst_day = min(daily_revenue, key=daily_revenue.get)
        avg_daily = total_revenue / len(daily_revenue)
    else:
        best_day = worst_day = None
        avg_daily = 0
    
    text = f"📈 **本月統計**\n"
    text += f"月份：{current_year}年{current_month}月\n\n"
    text += f"📦 訂單數：{order_count}\n"
    text += f"🛍️ 售出商品：{product_sold} 件\n"
    text += f"💰 總營業額：${total_revenue}\n"
    text += f"📊 日均營業額：${avg_daily:.0f}\n\n"
    
    if best_day:
        text += f"🏆 最佳日期：{best_day} (${daily_revenue[best_day]})\n"
        text += f"📉 最差日期：{worst_day} (${daily_revenue[worst_day]})"
    
    keyboard = [[
        InlineKeyboardButton("📊 查看其他統計", callback_data="STATS_MENU"),
        InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_hot_products(query):
    """顯示熱銷商品"""
    session = SessionLocal()
    
    # 統計最近30天的銷售
    thirty_days_ago = datetime.now() - timedelta(days=30)
    
    # 查詢熱銷商品
    hot_products = session.query(
        Product.id,
        Product.name,
        func.sum(OrderItem.quantity).label('total_sold'),
        func.sum(OrderItem.quantity * OrderItem.price).label('total_revenue')
    ).join(
        OrderItem, Product.id == OrderItem.product_id
    ).join(
        Order, OrderItem.order_id == Order.id
    ).filter(
        Order.created_at >= thirty_days_ago
    ).group_by(
        Product.id, Product.name
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()
    
    if not hot_products:
        query.message.edit_text("🏆 最近30天沒有銷售記錄")
        session.close()
        return
    
    text = "🏆 **熱銷商品TOP10**\n"
    text += "（最近30天）\n\n"
    
    for i, (prod_id, name, sold, revenue) in enumerate(hot_products, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {name}\n"
        text += f"   銷量：{sold} 件 | 營收：${revenue}\n\n"
    
    keyboard = [[
        InlineKeyboardButton("📊 查看其他統計", callback_data="STATS_MENU"),
        InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_sales_trend(query):
    """顯示銷售趨勢"""
    session = SessionLocal()
    
    # 獲取最近7天的數據
    trends = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        
        day_orders = session.query(Order).filter(
            func.date(Order.created_at) == date
        ).all()
        
        day_revenue = 0
        for order in day_orders:
            for item in order.items:
                day_revenue += item.price * item.quantity
        
        trends.append((date, day_revenue))
    
    text = "📉 **最近7天銷售趨勢**\n\n"
    
    # 簡單的圖表展示
    max_revenue = max(revenue for _, revenue in trends) if trends else 0
    
    for date, revenue in trends:
        # 計算條形圖長度
        if max_revenue > 0:
            bar_length = int((revenue / max_revenue) * 10)
        else:
            bar_length = 0
        
        bar = "█" * bar_length + "░" * (10 - bar_length)
        
        text += f"{date.strftime('%m/%d')} {bar} ${revenue}\n"
    
    text += f"\n📊 7日總營收：${sum(r for _, r in trends)}"
    
    keyboard = [[
        InlineKeyboardButton("📊 查看其他統計", callback_data="STATS_MENU"),
        InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def start_broadcast(query):
    """開始推播訊息"""
    context = query._context
    context.user_data['broadcasting'] = True
    
    query.message.reply_text(
        "📢 **推播訊息**\n\n"
        "請輸入要推播給所有顧客的訊息內容："
    )
    query.answer()

def send_broadcast(update: Update, context: CallbackContext):
    """發送推播訊息"""
    if not context.user_data.get('broadcasting'):
        return
    
    message_text = update.message.text
    context.user_data['broadcasting'] = False
    
    session = SessionLocal()
    
    # 獲取所有用戶
    users = session.query(User).all()
    
    success_count = 0
    fail_count = 0
    
    # 發送訊息給每個用戶
    for user in users:
        try:
            context.bot.send_message(user.user_id, f"📢 **商店公告**\n\n{message_text}")
            success_count += 1
        except:
            fail_count += 1
    
    keyboard = [[
        InlineKeyboardButton("🔙 返回統計", callback_data="STATS_MENU")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"✅ 推播完成\n\n"
        f"成功：{success_count} 人\n"
        f"失敗：{fail_count} 人",
        reply_markup=reply_markup
    )
    
    session.close() 