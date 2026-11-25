# FEATERA 影音課程行事曆 V2
Railway：從 GitHub 部署此目錄，加入 PostgreSQL，設定 DATABASE_URL（引用 PostgreSQL 的 DATABASE_URL）、ADMIN_USERNAME、ADMIN_PASSWORD、SECRET_KEY（長隨機值）。公開網址使用 HTTPS。勿將密碼提交 GitHub。
目前支援單影片、訪客閱讀、管理員編輯、雲端儲存、JSON 匯出。外部假日及 oEmbed 服務失敗時有提示。尚未支援播放清單、PWA、搜尋及內嵌播放器。多人同時修改同一天可能互相覆蓋，建議單一管理員編輯。

## V3
既有 PostgreSQL courses 表保留，新增 branding 表。管理員可上傳 PNG/JPG/WebP LOGO 或恢復預設，所有裝置共用。播放清單以單一卡片顯示，可修改名稱；點擊開啟 YouTube 清單。自動讀取清單標題、縮圖及影片數量需在 Railway Web 服務新增 YOUTUBE_API_KEY（Google Cloud 啟用 YouTube Data API v3 並限制金鑰用途）。未設定時仍可手動輸入標題儲存清單連結。私人清單不支援。JSON 備份仍僅包含課程，不含 LOGO。既有單片課程兼容。
