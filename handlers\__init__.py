"""處理器模組"""

# 匯出所有處理器
from . import products, cart, orders, admin
from . import product_options, product_management
from . import order_management, category_management
from . import statistics

def handle_callback(update, context):
    """統一的 callback 處理器"""
    query = update.callback_query
    data = query.data
    
    # 主選單
    if data == "MAIN_MENU":
        from utils.keyboards import get_main_menu_keyboard
        from config import ADMIN_IDS
        is_admin = query.from_user.id in ADMIN_IDS
        keyboard = get_main_menu_keyboard(is_admin)
        query.message.edit_text("請選擇功能：", reply_markup=keyboard)
        query.answer()
        return
    
    # 空操作
    elif data == "NONE":
        query.answer()
        return
    
    # 商品瀏覽
    elif data == "CATEGORIES":
        products.show_categories(query)
    elif data == "BROWSE":
        products.show_categories(query)
    elif data.startswith("CATEGORY_"):
        category_id = int(data.replace("CATEGORY_", ""))
        products.show_products_by_category(query, category_id)
    elif data.startswith("CAT_PHOTO_"):
        # 處理分類照片導航
        parts = data.replace("CAT_PHOTO_", "").split("_")
        category_id = int(parts[0])
        photo_index = int(parts[1])
        products.show_category_with_photos(query, category_id, photo_index)
    elif data.startswith("SELECT_PRODUCT_"):
        # 處理商品選擇（請求數量）
        product_id = int(data.replace("SELECT_PRODUCT_", ""))
        products.handle_product_selection(query, product_id)
    elif data == "OUT_OF_STOCK":
        query.answer("此商品已售罄", show_alert=True)
    elif data.startswith("PRODUCT_"):
        product_id = int(data.replace("PRODUCT_", ""))
        products.show_product_detail(query, product_id)
    elif data.startswith("ADD_TO_CART_"):
        product_id = int(data.replace("ADD_TO_CART_", ""))
        products.add_product_to_cart(query, product_id)
    elif data.startswith("TOGGLE_FAV_"):
        product_id = int(data.replace("TOGGLE_FAV_", ""))
        products.toggle_favorite(query, product_id)
    elif data == "ALL_PRODUCTS":
        products.show_all_products(query, page=1)
    elif data.startswith("ALL_PRODUCTS_PAGE_"):
        page = int(data.replace("ALL_PRODUCTS_PAGE_", ""))
        products.show_all_products(query, page)
    
    # 商品選項
    elif data.startswith("ADD_WITH_OPTIONS_"):
        product_id = int(data.replace("ADD_WITH_OPTIONS_", ""))
        product_options.show_product_options(query, product_id)
    elif data.startswith("TOGGLE_OPTION_"):
        product_options.handle_option_toggle(query, data)
    elif data.startswith("CONFIRM_ADD_"):
        parts = data.replace("CONFIRM_ADD_", "").split("_", 1)
        product_id = int(parts[0])
        selected_options = []
        if len(parts) > 1 and parts[1]:
            selected_options = [int(x) for x in parts[1].split(",") if x]
        product_options.confirm_add_to_cart(query, product_id, selected_options)
    
    # 購物車
    elif data == "VIEW_CART":
        cart.show_cart(update, context)
    elif data == "CART_LIST":
        cart.show_cart_list(query)
    elif data == "START_CHECKOUT":
        # 開始簡化的結帳流程
        from telegram.ext import ConversationHandler
        result = orders.start_simple_checkout(query)
        if result == ConversationHandler.END:
            return
        # 設置對話狀態
        context.user_data['checkout_state'] = result
    elif data.startswith("CART_"):
        cart.handle_cart_action(update, context)
    elif data == "CLEAR_CART":
        cart.handle_cart_action(update, context)
    
    # 訂單
    elif data == "MY_ORDERS":
        orders.view_my_orders_inline(query)
    elif data.startswith("VIEW_ORDER_"):
        order_id = int(data.replace("VIEW_ORDER_", ""))
        orders.view_order_detail(query, order_id)
    
    # 管理員功能
    elif data == "ADMIN_MENU":
        admin.show_admin_menu(query)
    elif data == "SYSTEM_SETTINGS":
        admin.show_system_settings(query)
    elif data == "RESTART_BOT":
        admin.restart_bot(query)
    elif data == "CONFIRM_RESTART" or data == "RESTART_NOW":
        admin.confirm_restart(query)
    elif data == "CHANGE_API_KEY":
        admin.start_change_api_key(query)
    elif data == "MANAGE_ADMINS":
        admin.show_admin_management(query)
    elif data == "ADD_ADMIN":
        admin.start_add_admin(query)
    elif data == "VIEW_ALL_USERS":
        admin.view_all_users(query)
    elif data == "BOT_INFO":
        admin.show_bot_info(query)
    elif data == "BACKUP_DB":
        admin.backup_database(query)
    elif data == "EXPORT_ORDERS":
        admin.export_orders(query)
    elif data == "BROADCAST":
        admin.start_broadcast(query)
    elif data == "MANAGE_PRODUCTS":
        product_management.product_management_menu(update, context)
    elif data == "PRODUCT_LIST":
        product_management.show_product_list(query)
    elif data == "SEARCH_PRODUCT":
        product_management.search_product(query)
    elif data == "STOCK_REPORT":
        product_management.show_stock_report(query)
    elif data.startswith("EDIT_PRODUCT_"):
        product_id = int(data.replace("EDIT_PRODUCT_", ""))
        product_management.show_edit_menu(query, product_id)
    elif data.startswith("TOGGLE_ACTIVE_"):
        product_management.handle_edit_action(query, data)
    elif data.startswith("EDIT_"):
        product_management.handle_edit_action(query, data)
    elif data.startswith("DELETE_PRODUCT_"):
        product_id = int(data.replace("DELETE_PRODUCT_", ""))
        product_management.delete_product(query, product_id)
    elif data.startswith("CONFIRM_DELETE_"):
        product_id = int(data.replace("CONFIRM_DELETE_", ""))
        product_management.confirm_delete_product(query, product_id)
    
    # 分類管理
    elif data == "MANAGE_CATEGORIES":
        category_management.category_management_menu(update, context)
    elif data == "CATEGORY_LIST":
        category_management.show_category_list(query)
    elif data == "ADD_CATEGORY":
        category_management.start_add_category(query)
    elif data.startswith("EDIT_CATEGORY_"):
        category_id = int(data.replace("EDIT_CATEGORY_", ""))
        category_management.show_edit_category_menu(query, category_id)
    elif data.startswith("CAT_EDIT_"):
        category_management.handle_category_edit(query, data)
    elif data.startswith("DELETE_CATEGORY_"):
        category_id = int(data.replace("DELETE_CATEGORY_", ""))
        category_management.delete_category(query, category_id)
    elif data.startswith("CONFIRM_DELETE_CAT_"):
        category_id = int(data.replace("CONFIRM_DELETE_CAT_", ""))
        category_management.confirm_delete_category(query, category_id)
    
    # 訂單管理
    elif data == "MANAGE_ORDERS":
        order_management.order_management_menu(update, context)
    elif data == "ORDER_MGMT":
        order_management.order_management_menu(update, context)
    elif data == "ORDER_PENDING":
        order_management.show_orders_by_status(query, 'pending')
    elif data == "ORDER_SHIPPED":
        order_management.show_orders_by_status(query, 'shipped')
    elif data == "ORDER_ALL":
        order_management.show_orders_by_status(query)
    elif data.startswith("ORDER_VIEW_"):
        order_id = int(data.replace("ORDER_VIEW_", ""))
        order_management.show_order_detail(query, order_id)
    elif data.startswith("ORDER_STATUS_"):
        order_id = int(data.replace("ORDER_STATUS_", ""))
        order_management.change_order_status_menu(query, order_id)
    elif data.startswith("ORDER_SET_"):
        parts = data.replace("ORDER_SET_", "").split("_", 1)
        order_id = int(parts[0])
        status = parts[1]
        order_management.update_order_status(query, order_id, status)
    elif data.startswith("ORDER_SHIP_"):
        order_id = int(data.replace("ORDER_SHIP_", ""))
        order_management.start_ship_order(query, order_id)
    elif data.startswith("ORDER_NOTIFY_"):
        order_id = int(data.replace("ORDER_NOTIFY_", ""))
        order_management.notify_customer(query, order_id)
    
    # 統計報表
    elif data == "VIEW_STATS":
        statistics.show_statistics_menu(update, context)
    elif data == "STATS_TODAY":
        statistics.show_today_stats(query)
    elif data == "STATS_MONTH":
        statistics.show_month_stats(query)
    elif data == "STATS_PRODUCTS":
        statistics.show_product_stats(query)
    elif data == "STATS_TRENDS":
        statistics.show_sales_trends(query)
    
    # 推播功能
    elif data == "BROADCAST":
        admin.start_broadcast(query)
    
    else:
        query.answer("未知的操作")

__all__ = [
    'products', 'cart', 'orders', 'admin',
    'product_options', 'product_management',
    'order_management', 'category_management',
    'statistics', 'handle_callback'
] 