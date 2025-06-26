# 機器人功能修復指南

## 診斷結果
- ✅ 資料庫正常（6個分類，19個商品）
- ✅ 配置正確（Bot Token 和管理員已設定）
- ✅ 有用戶和購物車資料

## 常見問題解決方案

### 1. 購物車功能問題

**症狀**：點擊「加入購物車」沒反應

**解決步驟**：
```bash
# 1. 重啟機器人
python main.py

# 2. 在 Telegram 中測試
/start
→ 點擊「🔍 瀏覽商品」
→ 選擇分類
→ 點擊商品（不是售罄的）
→ 輸入數量（如：1）
→ 應該會顯示「已加入購物車」
```

**可能原因**：
- 商品庫存為 0（售罄）
- 機器人未正確啟動
- 網路連接問題

### 2. 後台新增商品問題

**症狀**：管理員無法新增商品

**解決步驟**：
```bash
# 1. 確認您是管理員
# 檢查 config.py 中的 ADMIN_IDS 是否包含您的 Telegram ID

# 2. 正確的操作流程
/start
→ 點擊「📦 商品管理」（管理員專用）
→ 點擊「➕ 新增商品」
→ 按照 6 個步驟輸入：
   1. 商品名稱
   2. 價格
   3. 庫存
   4. 選擇分類
   5. 描述（可輸入「無」）
   6. 圖片網址（可輸入「無」）
```

### 3. 快速測試

運行以下命令確保機器人正常：

```bash
# 1. 停止現有的機器人進程
# Windows: 在工作管理員中結束 python.exe
# Linux: pkill -f main.py

# 2. 清理並重新初始化
python init_db.py

# 3. 啟動機器人
python main.py
```

### 4. 檢查日誌

如果問題持續，請查看控制台輸出的錯誤訊息。常見錯誤：

1. **"Conflict: terminated by other getUpdates request"**
   - 表示有多個機器人實例在運行
   - 解決：確保只有一個 main.py 在運行

2. **"Network error"**
   - 網路連接問題
   - 解決：檢查防火牆和代理設定

3. **"Invalid token"**
   - Bot Token 錯誤
   - 解決：檢查 config.py 中的 API_TOKEN

## 緊急修復腳本

如果上述方法都無效，執行以下腳本：

```python
# repair_bot.py
from models import SessionLocal, Base, engine
from config import API_TOKEN, ADMIN_IDS

# 重建資料庫表格
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

# 重新初始化
import subprocess
subprocess.run(["python", "init_db.py"])

print("✅ 修復完成，請重新啟動機器人")
```

## 聯繫支援

如果問題仍未解決，請提供：
1. 錯誤訊息截圖
2. `python check_bot.py` 的輸出
3. 操作步驟的詳細描述 