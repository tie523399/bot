# Linux 版本專案整理總結

## 已完成的整理工作

### 刪除的檔案
1. **版本相關檔案**
   - `requirements_windows.txt` - Windows 版本依賴
   - `requirements_py310.txt` - 重複的 Python 3.10 版本
   - `main_v20.py` - 舊版主程式

2. **臨時檔案**
   - `fix_cart.py` - 購物車修復測試檔
   - `test_bot.py` - 測試程式

3. **過時文檔**
   - `ENVIRONMENT_GUIDE.md` - 多版本環境指南
   - `QUICK_FIX.md` - 快速修復文檔
   - `TROUBLESHOOTING.md` - 疑難排解（含Windows內容）
   - `CART_FIX_SUMMARY.md` - 購物車修復總結
   - `README_NEW.md` - 重複的 README

### 保留的核心檔案
- `main.py` - 主程式
- `requirements.txt` - Linux 版本依賴（使用穩定版本）
- `models.py` - 資料庫模型
- `config.py` - 設定檔
- `init_db.py` - 資料庫初始化
- `handlers/` - 處理模組目錄
- `utils/` - 工具模組目錄

### 依賴版本（Linux 相容）
```
python-telegram-bot==13.15
SQLAlchemy==1.4.46
pandas==1.5.3
numpy==1.24.3
openpyxl==3.0.10
certifi==2023.11.17
urllib3==1.26.18
```

## 部署說明
1. 使用 Python 3.8+ 在 Linux 環境
2. 執行 `pip install -r requirements.txt` 安裝依賴
3. 設定 `config.py` 中的 Bot Token
4. 執行 `python init_db.py` 初始化資料庫
5. 執行 `python main.py` 啟動機器人

## 注意事項
- 本專案已優化為 Linux 環境專用版本
- 使用經過驗證的穩定版本套件，避免相容性問題
- 建議使用 systemd 服務方式部署，確保穩定運行 