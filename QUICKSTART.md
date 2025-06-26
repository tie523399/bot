# 🚀 快速啟動指南

## 1. 安裝依賴
```bash
pip install -r requirements.txt
```

## 2. 初始化資料庫
```bash
python init_db.py
```

## 3. 啟動機器人
```bash
python bot.py
```

## 4. 測試機器人
1. 在 Telegram 中搜尋您的機器人
2. 發送 `/start` 開始使用
3. 瀏覽商品分類並測試購物功能

## ⚠️ 注意事項
- 確保 `config.py` 中的 Bot Token 正確
- 將您的 Telegram 用戶 ID 加入管理員列表
- 首次運行建議執行 `init_db.py` 創建示例數據

## 🔧 常見問題
1. **機器人無回應**：檢查 Bot Token 和網路連線
2. **無法看到管理功能**：確認您的用戶 ID 在 ADMIN_IDS 中
3. **資料庫錯誤**：刪除 `orders.db` 並重新運行 `init_db.py`

## 📞 需要幫助？
查看完整文檔：[README.md](README.md) 