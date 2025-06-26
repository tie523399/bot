"""商品管理處理器"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from models import SessionLocal, Product, Category, Option
from config import ADMIN_IDS
import re
from sqlalchemy import func

# 對話狀態
WAITING_NAME = 1
WAITING_PRICE = 2
WAITING_STOCK = 3
WAITING_CATEGORY = 4
WAITING_DESCRIPTION = 5
WAITING_IMAGE = 6

def product_management_menu(update: Update, context: CallbackContext):
    """商品管理主選單"""
    if update.effective_user.id not in ADMIN_IDS:
        if update.message:
            update.message.reply_text("❌ 您沒有權限")
        else:
            update.callback_query.answer("您沒有權限", show_alert=True)
        return
    
    keyboard = [
        [
            InlineKeyboardButton("➕ 新增商品", callback_data="ADD_PRODUCT"),
            InlineKeyboardButton("📋 商品列表", callback_data="PRODUCT_LIST")
        ],
        [
            InlineKeyboardButton("🔍 搜尋商品", callback_data="SEARCH_PRODUCT"),
            InlineKeyboardButton("📊 庫存報表", callback_data="STOCK_REPORT")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data="ADMIN_MENU")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📦 **商品管理**\n\n請選擇操作："
    
    if update.callback_query:
        update.callback_query.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        update.message.reply_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

def start_add_product(query):
    """開始新增商品流程"""
    query.message.reply_text(
        "🆕 **新增商品**\n\n"
        "步驟 1/6：請輸入商品名稱："
    )
    query.answer()
    return WAITING_NAME

def handle_product_name(update: Update, context: CallbackContext):
    """處理商品名稱輸入"""
    name = update.message.text.strip()
    
    # 驗證名稱
    if len(name) < 2:
        update.message.reply_text("❌ 商品名稱至少需要2個字，請重新輸入：")
        return WAITING_NAME
    
    if len(name) > 50:
        update.message.reply_text("❌ 商品名稱不能超過50個字，請重新輸入：")
        return WAITING_NAME
    
    # 檢查是否已存在同名商品
    session = SessionLocal()
    existing = session.query(Product).filter_by(name=name).first()
    session.close()
    
    if existing:
        update.message.reply_text(
            f"⚠️ 已存在同名商品「{name}」\n"
            "請輸入不同的名稱："
        )
        return WAITING_NAME
    
    context.user_data['new_product'] = {'name': name}
    
    update.message.reply_text(
        f"✅ 商品名稱：{name}\n\n"
        "步驟 2/6：請輸入商品價格（數字）："
    )
    
    return WAITING_PRICE

def handle_product_price(update: Update, context: CallbackContext):
    """處理商品價格輸入"""
    text = update.message.text.strip()
    
    try:
        price = float(text)
        if price <= 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("❌ 請輸入有效的價格（大於0的數字）：")
        return WAITING_PRICE
    
    if price > 999999:
        update.message.reply_text("❌ 價格不能超過999,999，請重新輸入：")
        return WAITING_PRICE
    
    context.user_data['new_product']['price'] = price
    
    update.message.reply_text(
        f"✅ 商品價格：${price}\n\n"
        "步驟 3/6：請輸入商品庫存數量："
    )
    
    return WAITING_STOCK

def handle_product_stock(update: Update, context: CallbackContext):
    """處理商品庫存輸入"""
    text = update.message.text.strip()
    
    try:
        stock = int(text)
        if stock < 0:
            raise ValueError
    except ValueError:
        update.message.reply_text("❌ 請輸入有效的庫存數量（0或正整數）：")
        return WAITING_STOCK
    
    if stock > 99999:
        update.message.reply_text("❌ 庫存數量不能超過99,999，請重新輸入：")
        return WAITING_STOCK
    
    context.user_data['new_product']['stock'] = stock
    
    # 顯示分類選擇
    session = SessionLocal()
    categories = session.query(Category).filter_by(is_active=True).all()
    session.close()
    
    if not categories:
        update.message.reply_text("❌ 沒有可用的分類，請先創建分類")
        return ConversationHandler.END
    
    keyboard = []
    for cat in categories:
        text = f"{cat.icon} {cat.name}" if cat.icon else cat.name
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"SELECT_CAT_{cat.id}")
        ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(
        f"✅ 商品庫存：{stock}\n\n"
        "步驟 4/6：請選擇商品分類：",
        reply_markup=reply_markup
    )
    
    return WAITING_CATEGORY

def handle_category_selection(query, category_id):
    """處理分類選擇"""
    context = query._context
    
    session = SessionLocal()
    category = session.query(Category).get(category_id)
    
    if not category:
        query.answer("分類不存在", show_alert=True)
        session.close()
        return WAITING_CATEGORY
    
    context.user_data['new_product']['category_id'] = category_id
    context.user_data['new_product']['category_name'] = f"{category.icon} {category.name}"
    
    session.close()
    
    query.message.edit_text(
        f"✅ 商品分類：{context.user_data['new_product']['category_name']}\n\n"
        "步驟 5/6：請輸入商品描述（可選）\n"
        "如不需要描述，請輸入「無」："
    )
    
    query.answer()
    return WAITING_DESCRIPTION

def handle_product_description(update: Update, context: CallbackContext):
    """處理商品描述輸入"""
    text = update.message.text.strip()
    
    if text == "無":
        description = None
    else:
        if len(text) > 500:
            update.message.reply_text("❌ 描述不能超過500字，請重新輸入：")
            return WAITING_DESCRIPTION
        description = text
    
    context.user_data['new_product']['description'] = description
    
    update.message.reply_text(
        f"✅ 商品描述：{'無' if not description else description[:50] + '...' if len(description) > 50 else description}\n\n"
        "步驟 6/6：請輸入商品圖片網址（可選）\n"
        "如不需要圖片，請輸入「無」："
    )
    
    return WAITING_IMAGE

def handle_product_image(update: Update, context: CallbackContext):
    """處理商品圖片輸入並創建商品"""
    text = update.message.text.strip()
    
    if text == "無":
        image_url = None
    else:
        # 簡單驗證URL格式
        if not text.startswith(('http://', 'https://')):
            update.message.reply_text("❌ 請輸入有效的圖片網址（http://或https://開頭）：")
            return WAITING_IMAGE
        image_url = text
    
    # 創建商品
    session = SessionLocal()
    
    try:
        product = Product(
            name=context.user_data['new_product']['name'],
            price=context.user_data['new_product']['price'],
            stock=context.user_data['new_product']['stock'],
            category_id=context.user_data['new_product']['category_id'],
            description=context.user_data['new_product']['description'],
            image_url=image_url,
            is_active=True
        )
        
        session.add(product)
        session.commit()
        
        # 顯示成功訊息
        success_msg = f"""✅ **商品創建成功！**

📦 商品名稱：{product.name}
💰 價格：${product.price}
📊 庫存：{product.stock}
🗂️ 分類：{context.user_data['new_product']['category_name']}
📝 描述：{'無' if not product.description else product.description[:50] + '...' if len(product.description) > 50 else product.description}
🖼️ 圖片：{'無' if not product.image_url else '已設定'}

商品ID：#{product.id}"""

        keyboard = [
            [
                InlineKeyboardButton("➕ 繼續新增", callback_data="ADD_PRODUCT"),
                InlineKeyboardButton("📋 查看列表", callback_data="PRODUCT_LIST")
            ],
            [
                InlineKeyboardButton("🔙 返回管理", callback_data="MANAGE_PRODUCTS")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            success_msg,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # 清理用戶數據
        context.user_data.pop('new_product', None)
        
        session.close()
        return ConversationHandler.END
        
    except Exception as e:
        session.rollback()
        session.close()
        
        update.message.reply_text(
            f"❌ 創建商品失敗：{str(e)}\n"
            "請聯繫技術支援"
        )
        
        return ConversationHandler.END

def cancel_add_product(update: Update, context: CallbackContext):
    """取消新增商品"""
    context.user_data.pop('new_product', None)
    
    text = "❌ 已取消新增商品"
    
    if update.message:
        update.message.reply_text(text)
    else:
        update.callback_query.answer()
        update.callback_query.message.edit_text(text)
    
    return ConversationHandler.END

def show_product_list(query):
    """顯示商品列表"""
    session = SessionLocal()
    products = session.query(Product).filter_by(is_active=True).all()
    
    if not products:
        query.message.edit_text("📦 暫無商品")
        session.close()
        return
    
    keyboard = []
    for prod in products[:20]:  # 限制顯示20個
        text = f"{prod.name} - ${prod.price} (庫存:{prod.stock})"
        keyboard.append([
            InlineKeyboardButton(text, callback_data=f"EDIT_PRODUCT_{prod.id}")
        ])
    
    if len(products) > 20:
        keyboard.append([
            InlineKeyboardButton(f"📌 共 {len(products)} 個商品", callback_data="NONE")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 返回", callback_data="MANAGE_PRODUCTS")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        "📦 **商品列表**\n\n點擊商品進行編輯：",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def show_product_detail_admin(query, product_id):
    """顯示商品詳情（管理員）"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    text = f"**商品詳情**\n\n"
    text += f"ID: {product.id}\n"
    text += f"名稱: {product.name}\n"
    text += f"價格: ${product.price}\n"
    text += f"庫存: {product.stock}\n"
    text += f"分類: {product.category}\n"
    
    if product.description:
        text += f"描述: {product.description}\n"
    
    # 顯示選項
    if product.options:
        text += "\n選項:\n"
        for opt in product.options:
            text += f"• {opt.name} (+${opt.price})\n"
    
    keyboard = [
        [
            InlineKeyboardButton("✏️ 編輯", callback_data=f"PROD_EDIT_{product_id}"),
            InlineKeyboardButton("🗑️ 刪除", callback_data=f"PROD_DEL_CONFIRM_{product_id}")
        ],
        [
            InlineKeyboardButton("➕ 新增選項", callback_data=f"OPT_ADD_{product_id}"),
            InlineKeyboardButton("🔙 返回列表", callback_data="PROD_LIST")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def edit_product_menu(query, product_id):
    """編輯商品選單"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    keyboard = [
        [
            InlineKeyboardButton("📝 編輯名稱", callback_data=f"EDIT_NAME_{product_id}"),
            InlineKeyboardButton("💰 編輯價格", callback_data=f"EDIT_PRICE_{product_id}")
        ],
        [
            InlineKeyboardButton("📦 編輯庫存", callback_data=f"EDIT_STOCK_{product_id}"),
            InlineKeyboardButton("📝 編輯描述", callback_data=f"EDIT_DESC_{product_id}")
        ],
        [
            InlineKeyboardButton("🔙 返回", callback_data=f"PROD_VIEW_{product_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"✏️ **編輯商品**\n\n"
    text += f"商品：{product.name}\n"
    text += f"價格：${product.price}\n"
    text += f"庫存：{product.stock}\n\n"
    text += "請選擇要編輯的項目："
    
    query.message.edit_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def delete_product_confirm(query, product_id):
    """確認刪除商品"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    keyboard = [
        [
            InlineKeyboardButton("⚠️ 確認刪除", callback_data=f"PROD_DEL_YES_{product_id}"),
            InlineKeyboardButton("❌ 取消", callback_data=f"PROD_VIEW_{product_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        f"⚠️ **確認刪除**\n\n"
        f"確定要刪除商品「{product.name}」嗎？\n"
        f"此操作無法復原！",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    session.close()

def delete_product(query, product_id):
    """執行刪除商品"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("商品不存在")
        session.close()
        return
    
    product_name = product.name
    
    # 刪除相關的購物車項目、選項等
    from models import CartItem
    session.query(CartItem).filter_by(product_id=product_id).delete()
    session.query(Option).filter_by(product_id=product_id).delete()
    
    # 刪除商品
    session.delete(product)
    session.commit()
    
    keyboard = [[
        InlineKeyboardButton("📋 返回商品列表", callback_data="PROD_LIST")
    ]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.message.edit_text(
        f"✅ 商品「{product_name}」已成功刪除",
        reply_markup=reply_markup
    )
    
    session.close()

def start_edit_product(update: Update, context: CallbackContext, field: str, product_id: int):
    """開始編輯商品流程"""
    query = update.callback_query
    
    field_names = {
        'name': '名稱',
        'price': '價格',
        'stock': '庫存',
        'desc': '描述'
    }
    
    context.user_data['editing_product'] = {
        'id': product_id,
        'field': field
    }
    
    query.message.reply_text(
        f"請輸入新的{field_names.get(field, field)}："
    )
    query.answer()

def handle_product_edit(update: Update, context: CallbackContext):
    """處理商品編輯輸入"""
    product_data = context.user_data.get('editing_product')
    if not product_data:
        return
    
    text = update.message.text.strip()
    field = product_data['field']
    product_id = product_data['id']
    
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        update.message.reply_text("商品不存在")
        context.user_data.pop('editing_product', None)
        session.close()
        return
    
    try:
        if field == 'name':
            product.name = text
        elif field == 'price':
            product.price = float(text)
        elif field == 'stock':
            product.stock = int(text)
        elif field == 'desc':
            product.description = text
        
        session.commit()
        update.message.reply_text(f"✅ 商品{field}已更新為：{text}")
        
        # 清除編輯狀態
        context.user_data.pop('editing_product', None)
        
    except ValueError:
        update.message.reply_text("❌ 輸入格式錯誤，請重新輸入")
    except Exception as e:
        update.message.reply_text(f"❌ 更新失敗：{str(e)}")
    
    session.close()

def show_edit_menu(query, product_id):
    """顯示商品編輯選單"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("❌ 商品不存在")
        session.close()
        return
    
    category_info = f"{product.category.icon} {product.category.name}" if product.category else "未分類"
    
    text = f"""📦 **商品詳情**

🏷️ 名稱：{product.name}
💰 價格：${product.price}
📊 庫存：{product.stock}
🗂️ 分類：{category_info}
📝 描述：{product.description if product.description else '無'}
🖼️ 圖片：{'已設定' if product.image_url else '無'}
📅 創建時間：{product.created_at.strftime('%Y-%m-%d %H:%M')}
🔖 狀態：{'啟用' if product.is_active else '停用'}

請選擇操作："""

    keyboard = [
        [
            InlineKeyboardButton("✏️ 編輯名稱", callback_data=f"EDIT_NAME_{product_id}"),
            InlineKeyboardButton("💰 編輯價格", callback_data=f"EDIT_PRICE_{product_id}")
        ],
        [
            InlineKeyboardButton("📊 編輯庫存", callback_data=f"EDIT_STOCK_{product_id}"),
            InlineKeyboardButton("🗂️ 更改分類", callback_data=f"EDIT_CATEGORY_{product_id}")
        ],
        [
            InlineKeyboardButton("📝 編輯描述", callback_data=f"EDIT_DESC_{product_id}"),
            InlineKeyboardButton("🖼️ 編輯圖片", callback_data=f"EDIT_IMAGE_{product_id}")
        ],
        [
            InlineKeyboardButton(
                "🔴 停用商品" if product.is_active else "🟢 啟用商品", 
                callback_data=f"TOGGLE_ACTIVE_{product_id}"
            ),
            InlineKeyboardButton("🗑️ 刪除商品", callback_data=f"DELETE_PRODUCT_{product_id}")
        ],
        [
            InlineKeyboardButton("🔙 返回列表", callback_data="PRODUCT_LIST")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    session.close()

def handle_edit_action(query, data):
    """處理編輯操作"""
    if data.startswith("TOGGLE_ACTIVE_"):
        product_id = int(data.replace("TOGGLE_ACTIVE_", ""))
        toggle_product_active(query, product_id)
    else:
        query.answer("請使用文字訊息輸入新的值", show_alert=True)
        # TODO: 實現對話式編輯流程

def toggle_product_active(query, product_id):
    """切換商品啟用狀態"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.answer("商品不存在", show_alert=True)
        session.close()
        return
    
    product.is_active = not product.is_active
    session.commit()
    
    status = "啟用" if product.is_active else "停用"
    query.answer(f"商品已{status}")
    
    session.close()
    show_edit_menu(query, product_id)

def delete_product(query, product_id):
    """刪除商品確認"""
    session = SessionLocal()
    product = session.query(Product).get(product_id)
    
    if not product:
        query.message.edit_text("❌ 商品不存在")
        session.close()
        return
    
    text = f"""⚠️ **確認刪除商品**

您確定要刪除以下商品嗎？

🏷️ 名稱：{product.name}
💰 價格：${product.price}
📊 庫存：{product.stock}

⚠️ 此操作無法撤銷！"""

    keyboard = [
        [
            InlineKeyboardButton("✅ 確認刪除", callback_data=f"CONFIRM_DELETE_{product_id}"),
            InlineKeyboardButton("❌ 取消", callback_data=f"EDIT_PRODUCT_{product_id}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    session.close()

def confirm_delete_product(query, product_id):
    """確認刪除商品"""
    session = SessionLocal()
    
    try:
        product = session.query(Product).get(product_id)
        if not product:
            query.message.edit_text("❌ 商品不存在")
            return
        
        product_name = product.name
        session.delete(product)
        session.commit()
        
        keyboard = [
            [
                InlineKeyboardButton("📋 返回列表", callback_data="PRODUCT_LIST"),
                InlineKeyboardButton("➕ 新增商品", callback_data="ADD_PRODUCT")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        query.message.edit_text(
            f"✅ 商品「{product_name}」已成功刪除",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        query.message.edit_text(f"❌ 刪除失敗：{str(e)}")
    finally:
        session.close()

def search_product(query):
    """搜尋商品"""
    query.message.reply_text(
        "🔍 請輸入要搜尋的商品名稱關鍵字："
    )
    # TODO: 實現搜尋對話流程

def show_stock_report(query):
    """顯示庫存報表"""
    session = SessionLocal()
    
    # 取得低庫存商品（庫存 < 10）
    low_stock = session.query(Product).filter(
        Product.stock < 10,
        Product.is_active == True
    ).all()
    
    # 取得無庫存商品
    no_stock = session.query(Product).filter(
        Product.stock == 0,
        Product.is_active == True
    ).all()
    
    # 統計
    total_products = session.query(Product).filter_by(is_active=True).count()
    total_value = session.query(Product).filter_by(is_active=True).with_entities(
        func.sum(Product.price * Product.stock)
    ).scalar() or 0
    
    text = f"""📊 **庫存報表**

📦 總商品數：{total_products}
💰 總庫存價值：${total_value:,.2f}

🔴 **無庫存商品** ({len(no_stock)} 項)"""
    
    if no_stock:
        for p in no_stock[:5]:
            text += f"\n• {p.name}"
        if len(no_stock) > 5:
            text += f"\n... 還有 {len(no_stock) - 5} 項"
    else:
        text += "\n無"
    
    text += f"\n\n🟡 **低庫存商品** (< 10) ({len(low_stock)} 項)"
    
    if low_stock:
        for p in low_stock[:5]:
            text += f"\n• {p.name} (剩餘:{p.stock})"
        if len(low_stock) > 5:
            text += f"\n... 還有 {len(low_stock) - 5} 項"
    else:
        text += "\n無"
    
    keyboard = [
        [InlineKeyboardButton("🔙 返回", callback_data="MANAGE_PRODUCTS")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.message.edit_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    session.close() 