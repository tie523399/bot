# 海水不可斗量 - Telegram 購物機器人

一個功能完整的 Telegram 購物機器人，包含商品管理、購物車、訂單處理等功能。

## 功能特點

### 用戶功能
- 🌊 瀏覽商品分類（海水、不可、斗量）
- 🛍️ 購物車管理（增加、減少、刪除商品）
- 💳 結帳下單
- 📦 查看歷史訂單
- 📞 聯繫客服

### 管理員功能
- ➕ 新增商品
- 🧩 新增商品屬性（選項）
- 📋 查看所有訂單
- ⚙️ 設定訂單狀態
- 📤 匯出訂單 (Excel)
- 📢 推播訊息給所有用戶

## 系統需求

- Python 3.8 或更高版本
- Linux 作業系統

## 安裝說明

1. 安裝依賴套件：
```bash
pip install -r requirements.txt
```

2. 設定 Telegram Bot Token：
   - 在 `config.py` 中設定您的 Bot Token
   - 設定管理員 ID

3. 初始化資料庫（建議執行）：
```bash
python init_db.py
```
這將創建基本的商品分類和示例商品

4. 啟動機器人：
```bash
python main.py
```

## 使用說明

### 一般用戶
1. 在 Telegram 中搜尋您的機器人
2. 發送 `/start` 開始使用
3. 使用主選單按鈕瀏覽商品
4. 點擊「立即購買」將商品加入購物車
5. 查看購物車並結帳

### 管理員
管理員擁有額外的選單選項：
- **新增商品**：輸入商品名稱、分類、價格、圖片、描述、庫存
- **新增屬性**：為商品添加選項（如尺寸、顏色等）
- **管理訂單**：查看所有訂單、更改訂單狀態
- **推播訊息**：向所有下過單的用戶發送通知

## 商品分類

1. **🌊 海水系列**
   - 來自深海的純淨海水
   - 富含礦物質

2. **🚫 不可系列**
   - 神秘配方
   - 限量供應

3. **⚖️ 斗量系列**
   - 精準計量
   - 大容量選擇

## 訂單流程

1. 用戶選擇商品加入購物車
2. 在購物車中調整數量
3. 點擊結帳
4. 輸入取貨門市
5. 系統生成訂單編號
6. 管理員收到新訂單通知
7. 用戶可隨時查看訂單狀態

## 技術架構

- **框架**：python-telegram-bot 13.7
- **資料庫**：SQLite + SQLAlchemy
- **資料匯出**：pandas + openpyxl

## 資料庫結構

- **Product**：商品資料
- **Option**：商品選項/屬性
- **CartItem**：購物車項目
- **Order**：訂單
- **OrderItem**：訂單項目

## 注意事項

- 確保 Bot Token 保密
- 定期備份資料庫檔案 `orders.db`
- 管理員 ID 需要是數字格式的 Telegram 用戶 ID

## 持續運行

### 使用 nohup
```bash
nohup python main.py > bot.log 2>&1 &
```

### 使用 screen
```bash
screen -S telegram_bot
python main.py
# 按 Ctrl+A 然後 D 分離會話
```

### 使用 systemd (推薦)
創建服務檔案 `/etc/systemd/system/telegram-bot.service`：
```ini
[Unit]
Description=Telegram Shopping Bot
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 /path/to/bot/main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

啟動服務：
```bash
sudo systemctl start telegram-bot
sudo systemctl enable telegram-bot
```

## 故障排除

1. **機器人無回應**
   - 檢查網路連線
   - 確認 Bot Token 正確
   - 查看錯誤日誌

2. **資料庫錯誤**
   - 確保有寫入權限
   - 檢查磁碟空間

3. **訂單無法建立**
   - 確認購物車有商品
   - 檢查商品庫存

## 聯絡資訊

如有問題請聯繫系統管理員。 