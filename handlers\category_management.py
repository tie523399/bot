"""分類管理處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from models import SessionLocal, Category, Product
from config import ADMIN_IDS

def category_management_menu(update: Update, context: CallbackContext):
    """分類管理主選單"""
    if update.effective_user.id not in ADMIN_IDS:
        update.message.reply_text("❌ 您沒有權限")
        return
    
    keyboard = [
        [
            InlineKeyboardButton("➕ 新增分類", callback_data="CAT_ADD"),
            InlineKeyboardButton("📋 分類列表", callback_data="CAT_LIST")
        ],
        [
            InlineKeyboardButton("✏️ 編輯分類", callback_data="CAT_EDIT"),
            InlineKeyboardButton("🗑️ 刪除分類", callback_data="CAT_DELETE")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="MAIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = update.message or update.callback_query.message
    message.reply_text(
        "🗂️ **分類管理**\n\n請選擇操作：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def show_category_list(query):
    """顯示分類列表"""
    session = SessionLocal()
    categories = session.query(Category).order_by(Category.order).all()
    
    if not categories:
        query.message.edit_text("📋 目前沒有分類")
        session.close()
        return
    
    keyboard = []
    for cat in categories:
        # 統計該分類的商品數量
        product_count = session.query(Product).filter_by(category_id=cat.id).count()
        text = f"{cat.icon} {cat.name} ({product_count}個商品)"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"CAT_VIEW_{cat.id}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="CAT_MGMT")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        "📋 **分類列表**\n\n點擊分類查看詳情：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_category_detail(query, category_id):
    """顯示分類詳情"""
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        query.message.edit_text("分類不存在")
        session.close()
        return
    
    product_count = session.query(Product).filter_by(category_id=category.id).count()
    
    text = f"**分類詳情**\n\n"
    text += f"ID: {category.id}\n"
    text += f"名稱: {category.name}\n"
    text += f"圖標: {category.icon}\n"
    text += f"排序: {category.order}\n"
    text += f"商品數量: {product_count}\n"
    
    keyboard = [
        [
            InlineKeyboardButton("✏️ 編輯", callback_data=f"CAT_EDIT_{category_id}"),
            InlineKeyboardButton("🗑️ 刪除", callback_data=f"CAT_DEL_CONFIRM_{category_id}")
        ],
        [
            InlineKeyboardButton("🔢 調整排序", callback_data=f"CAT_ORDER_{category_id}"),
            InlineKeyboardButton("🔙 返回列表", callback_data="CAT_LIST")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def start_add_category(query):
    """開始新增分類"""
    context = query._context
    context.user_data['adding_category'] = {'step': 'name'}
    
    query.message.reply_text(
        "請輸入分類名稱："
    )
    query.answer()

def edit_category_menu(query, category_id):
    """編輯分類選單"""
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        query.message.edit_text("分類不存在")
        session.close()
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📝 編輯名稱", callback_data=f"EDIT_CAT_NAME_{category_id}"),
            InlineKeyboardButton("🎨 編輯圖標", callback_data=f"EDIT_CAT_ICON_{category_id}")
        ],
        [
            InlineKeyboardButton("🔢 編輯排序", callback_data=f"EDIT_CAT_ORDER_{category_id}"),
            InlineKeyboardButton("🔙 返回", callback_data=f"CAT_VIEW_{category_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"✏️ **編輯分類**\n\n"
    text += f"分類：{category.icon} {category.name}\n"
    text += f"排序：{category.order}\n\n"
    text += "請選擇要編輯的項目："
    
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def delete_category_confirm(query, category_id):
    """確認刪除分類"""
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        query.message.edit_text("分類不存在")
        session.close()
        return
    
    product_count = session.query(Product).filter_by(category_id=category.id).count()
    
    if product_count > 0:
        text = f"⚠️ **警告**\n\n"
        text += f"分類「{category.name}」下有 {product_count} 個商品\n"
        text += f"刪除分類將導致這些商品失去分類！\n\n"
        text += f"確定要刪除嗎？"
    else:
        text = f"⚠️ **確認刪除**\n\n"
        text += f"確定要刪除分類「{category.name}」嗎？\n"
        text += f"此操作無法復原！"
    
    keyboard = [
        [
            InlineKeyboardButton("⚠️ 確認刪除", callback_data=f"CAT_DEL_YES_{category_id}"),
            InlineKeyboardButton("❌ 取消", callback_data=f"CAT_VIEW_{category_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def delete_category(query, category_id):
    """執行刪除分類"""
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        query.message.edit_text("分類不存在")
        session.close()
        return
    
    category_name = category.name
    
    # 將該分類下的商品設為無分類
    session.query(Product).filter_by(category_id=category_id).update({'category_id': None})
    
    # 刪除分類
    session.delete(category)
    session.commit()
    
    keyboard = [[
        InlineKeyboardButton("📋 返回分類列表", callback_data="CAT_LIST")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        f"✅ 分類「{category_name}」已成功刪除",
        reply_markup=reply_markup
    )
    
    session.close()

def start_edit_category(update: Update, context: CallbackContext, field: str, category_id: int):
    """開始編輯分類流程"""
    query = update.callback_query
    
    field_names = {
        'name': '名稱',
        'icon': '圖標',
        'order': '排序'
    }
    
    context.user_data['editing_category'] = {
        'id': category_id,
        'field': field
    }
    
    query.message.reply_text(
        f"請輸入新的{field_names.get(field, field)}："
    )
    query.answer()

def handle_category_add(update: Update, context: CallbackContext):
    """處理新增分類輸入"""
    add_data = context.user_data.get('adding_category')
    if not add_data:
        return
    
    text = update.message.text.strip()
    step = add_data['step']
    
    session = SessionLocal()
    
    if step == 'name':
        add_data['name'] = text
        add_data['step'] = 'icon'
        context.user_data['adding_category'] = add_data
        update.message.reply_text("請輸入分類圖標（emoji）：")
    
    elif step == 'icon':
        add_data['icon'] = text
        add_data['step'] = 'order'
        context.user_data['adding_category'] = add_data
        update.message.reply_text("請輸入排序編號（數字）：")
    
    elif step == 'order':
        try:
            order = int(text)
            
            # 創建分類
            category = Category(
                name=add_data['name'],
                icon=add_data['icon'],
                order=order,
                display_order=order
            )
            
            session.add(category)
            session.commit()
            
            update.message.reply_text(
                f"✅ 分類新增成功！\n\n"
                f"名稱：{add_data['name']}\n"
                f"圖標：{add_data['icon']}\n"
                f"排序：{order}"
            )
            
            # 清除狀態
            context.user_data.pop('adding_category', None)
            
        except ValueError:
            update.message.reply_text("❌ 請輸入有效的數字")
    
    session.close()

def handle_category_edit(update: Update, context: CallbackContext):
    """處理分類編輯輸入"""
    edit_data = context.user_data.get('editing_category')
    if not edit_data:
        return
    
    text = update.message.text.strip()
    field = edit_data['field']
    category_id = edit_data['id']
    
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        update.message.reply_text("分類不存在")
        context.user_data.pop('editing_category', None)
        session.close()
        return
    
    try:
        if field == 'name':
            category.name = text
        elif field == 'icon':
            category.icon = text
        elif field == 'order':
            order = int(text)
            category.order = order
            category.display_order = order
        
        session.commit()
        update.message.reply_text(f"✅ 分類{field}已更新為：{text}")
        
        # 清除編輯狀態
        context.user_data.pop('editing_category', None)
        
    except ValueError:
        update.message.reply_text("❌ 輸入格式錯誤，請重新輸入")
    except Exception as e:
        update.message.reply_text(f"❌ 更新失敗：{str(e)}")
    
    session.close() 