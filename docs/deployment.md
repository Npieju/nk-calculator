# Deployment Plan

## Constraint

GitHub Pagesは静的配信のみ。スクレイピング・比較計算はバックエンドで実行する。

## Target

- Frontend: GitHub Pages
- Backend: Render (Web Service)

## Implemented Files

- Frontend deploy workflow: `.github/workflows/deploy-pages.yml`
- Render blueprint: `render.yaml`

## 1) Backend (Render)

1. Renderで `New +` → `Blueprint` を選択し、このリポジトリを指定
2. `render.yaml` から `nk-calculator-api` が作成される
3. Deploy完了後、API URLを控える（例: `https://nk-calculator-api.onrender.com`）

### Required Env Vars

- `ALLOWED_ORIGINS`: フロントのオリジンを指定
	- 例: `https://Npieju.github.io`

## 2) Frontend (GitHub Pages)

1. GitHub repository settings で Pages を有効化
2. Environment / Repository variable を追加
	 - `API_BASE_URL`: Render API URL（例: `https://nk-calculator-api.onrender.com`）
3. `main` ブランチに push
4. GitHub Actions `Deploy Frontend to GitHub Pages` が実行される

workflowでは `apps/frontend/index.html` の初期API URLを `API_BASE_URL` に置換してPagesへ配信する。

## 3) Local smoke test

### Backend

```bash
cd apps/backend
/workspace/.venv/bin/pip install -r requirements.txt
/workspace/.venv/bin/uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd apps/frontend
/workspace/.venv/bin/python -m http.server 5173
```

ブラウザで `http://localhost:5173` を開いて実行。

## Security Notes

- 本番では `ALLOWED_ORIGINS` を `*` にしない
- `race.netkeiba.com` 以外のURLはAPI側で拒否する
- 連続実行対策として将来的にレート制限を追加する
