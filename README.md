# FEATERA 影音課程行事曆 V2
Railway：從 GitHub 部署此目錄，加入 PostgreSQL，設定 DATABASE_URL（引用 PostgreSQL 的 DATABASE_URL）、ADMIN_USERNAME、ADMIN_PASSWORD、SECRET_KEY（長隨機值）。公開網址使用 HTTPS。勿將密碼提交 GitHub。
目前支援單影片、訪客閱讀、管理員編輯、雲端儲存、JSON 匯出。外部假日及 oEmbed 服務失敗時有提示。尚未支援播放清單、PWA、搜尋及內嵌播放器。多人同時修改同一天可能互相覆蓋，建議單一管理員編輯。
