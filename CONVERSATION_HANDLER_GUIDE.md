# ConversationHandler 架構重構指南

## 概述

本次重構將所有多步驟的用戶互動改為使用 ConversationHandler 管理，提供更好的狀態管理和用戶體驗。

## 架構優勢

### 1. 狀態管理
- **明確的對話狀態**：每個對話流程都有清晰的狀態定義
- **自動超時處理**：設定對話超時，避免資源浪費
- **狀態持久化**：使用 context.user_data 保存對話數據

### 2. 錯誤處理
- **統一的取消操作**：所有對話都可以用 /cancel 取消
- **優雅的錯誤恢復**：對話中斷後可以重新開始
- **防止狀態混亂**：每個對話獨立管理，不會相互干擾

### 3. 用戶體驗
- **流暢的對話流程**：用戶清楚知道當前步驟
- **即時反饋**：每步都有明確的提示和驗證
- **靈活的導航**：可以在對話中返回上一步或取消

## 已實現的對話流程

### 1. 購物流程 (shopping_v2.py)
```
開始瀏覽 → 選擇分類 → 選擇商品 → 輸入數量 → 加入購物車
```

### 2. 搜尋流程 (search_v2.py)
```
開始搜尋 → 輸入關鍵字 → 顯示結果 → 選擇商品 → 輸入數量
```

### 3. 結帳流程 (checkout_v2.py)
```
開始結帳 → 輸入姓名 → 輸入電話 → 輸入門市 → 確認訂單
```

## 待實現的對話流程

### 4. 商品管理 (product_mgmt_v2.py)
- 新增商品：6步收集商品資訊
- 編輯商品：選擇欄位 → 輸入新值

### 5. 分類管理 (category_mgmt_v2.py)
- 新增分類：名稱 → 圖標 → 描述 → 照片

### 6. 訂單管理 (order_mgmt_v2.py)
- 更新狀態：選擇訂單 → 選擇狀態 → 輸入物流號

### 7. 管理員功能 (admin_v2.py)
- 推播訊息：輸入訊息內容
- 新增管理員：輸入 ID
- 更改 API Key：輸入新 Key

## 實施步驟

### 第一階段：核心功能（已完成）
1. ✅ 創建 main_v2.py 主程式架構
2. ✅ 實現購物流程處理器
3. ✅ 實現搜尋流程處理器
4. ✅ 實現結帳流程處理器

### 第二階段：管理功能
1. 實現商品管理處理器
2. 實現分類管理處理器
3. 實現訂單管理處理器
4. 實現管理員功能處理器

### 第三階段：整合測試
1. 整合所有處理器
2. 測試對話流程
3. 優化用戶體驗
4. 部署上線

## 程式碼範例

### 定義 ConversationHandler
```python
def create_shopping_handler():
    return ConversationHandler(
        entry_points=[
            CommandHandler('browse', start_browse),
            CallbackQueryHandler(start_browse, pattern='^BROWSE$')
        ],
        states={
            BROWSE_CATEGORY: [
                CallbackQueryHandler(show_products, pattern='^CATEGORY_')
            ],
            SELECT_PRODUCT: [
                CallbackQueryHandler(request_quantity, pattern='^SELECT_PRODUCT_')
            ],
            INPUT_QUANTITY: [
                MessageHandler(Filters.text & ~Filters.command, process_quantity)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CallbackQueryHandler(cancel, pattern='^CANCEL$')
        ],
        conversation_timeout=300  # 5分鐘超時
    )
```

### 狀態轉換
```python
def show_products(update, context):
    # 處理邏輯...
    return SELECT_PRODUCT  # 進入下一個狀態

def process_quantity(update, context):
    # 處理邏輯...
    return ConversationHandler.END  # 結束對話
```

## 注意事項

1. **優先順序**：ConversationHandler 應該在一般 Handler 之前註冊
2. **狀態清理**：對話結束時清理 context.user_data
3. **超時處理**：設定合理的 conversation_timeout
4. **錯誤處理**：每個狀態都要處理可能的錯誤
5. **回調衝突**：避免 callback_data 模式重複

## 遷移建議

1. **逐步遷移**：不需要一次性替換所有功能
2. **保持兼容**：新舊版本可以並存運行
3. **充分測試**：每個對話流程都要完整測試
4. **文檔更新**：及時更新使用說明

## 總結

使用 ConversationHandler 架構後，機器人的對話管理更加專業和穩定。用戶體驗得到顯著提升，開發和維護也更加容易。建議逐步將所有多步驟互動都改為這種架構。 