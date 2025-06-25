# Render 部署指南

## 🚀 快速部署步驟

### 1. 準備 GitHub 倉庫

1. **創建 GitHub 倉庫**
   - 登入 GitHub 並創建新倉庫
   - 倉庫名稱建議：`evidence-pdf-processor-web`
   - 設為 Public（免費方案要求）

2. **上傳檔案到 GitHub**
   ```bash
   Git
   git init
   git add .
   git commit -m "Initial commit: Evidence PDF processor web app"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/evidence-pdf-processor-web.git
   git push -u origin main
   ```

### 2. 在 Render 上部署

1. **註冊 Render 帳號**
   - 前往 [render.com](https://render.com)
   - 使用 GitHub 帳號註冊/登入

2. **連接 GitHub 倉庫**
   - 點擊 "New +"
   - 選擇 "Web Service"
   - 連接您的 GitHub 帳號
   - 選擇剛創建的倉庫

3. **配置部署設定**
   - **Name**: `evidence-pdf-processor`
   - **Region**: Singapore（已在 render.yaml 中設定）
   - **Branch**: `main`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`

4. **環境變數設定**（自動從 render.yaml 讀取）
   - `FLASK_ENV`: `production`
   - `MAX_CONTENT_LENGTH`: `104857600`

5. **開始部署**
   - 點擊 "Create Web Service"
   - 等待部署完成（約 3-5 分鐘）

### 3. 部署後驗證

1. **健康檢查**
   - 訪問 `https://your-app-name.onrender.com/health`
   - 應該返回 JSON 狀態資訊

2. **功能測試**
   - 訪問主頁面
   - 測試檔案上傳功能
   - 測試批次處理功能

## 📋 檔案清單檢查

確保以下檔案都在您的倉庫中：

- ✅ `app.py` - 主要 Flask 應用
- ✅ `evidence_pdf_converter.py` - 核心轉換邏輯
- ✅ `batch_processor.py` - 批次處理器
- ✅ `requirements.txt` - Python 依賴
- ✅ `render.yaml` - Render 配置
- ✅ `kaiu.ttf` - 中文字型檔案
- ✅ `templates/index.html` - 前端頁面
- ✅ `static/` - 靜態資源（如果有）
- ✅ `.gitignore` - Git 忽略檔案
- ✅ `README.md` - 專案說明

## 🔧 故障排除

### 常見問題

1. **部署失敗：找不到模組**
   - 檢查 `requirements.txt` 是否包含所有依賴
   - 確認模組名稱拼寫正確

2. **字型檔案問題**
   - 確認 `kaiu.ttf` 已上傳到倉庫
   - 檢查字型檔案路徑是否正確

3. **記憶體不足**
   - Render 免費方案限制 512MB RAM
   - 考慮優化圖片處理邏輯

4. **檔案上傳限制**
   - 免費方案有檔案大小限制
   - 已設定 100MB 上傳限制

### 日誌查看

1. 在 Render 控制台中點擊您的服務
2. 選擇 "Logs" 標籤查看即時日誌
3. 查找錯誤訊息進行故障排除

## 💡 最佳實踐

1. **環境變數**
   - 敏感資訊使用環境變數
   - 不要將密鑰提交到 Git

2. **資源管理**
   - 定期清理臨時檔案
   - 監控磁碟空間使用

3. **效能優化**
   - 使用 Gunicorn 多 worker
   - 實施檔案大小限制

4. **安全性**
   - 驗證上傳檔案類型
   - 使用 secure_filename 處理檔名

## 📞 支援資源

- [Render 官方文件](https://render.com/docs)
- [Flask 部署指南](https://flask.palletsprojects.com/en/2.3.x/deploying/)
- [Gunicorn 設定](https://docs.gunicorn.org/en/stable/settings.html)

## 🎯 部署完成後

您的應用將可在以下網址訪問：
`https://evidence-pdf-processor.onrender.com`

**注意**：Render 免費方案會在 15 分鐘無活動後休眠，首次喚醒可能需要 30-60 秒。