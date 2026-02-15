# Deployment Plan

## Constraint

GitHub Pagesは静的配信のみ。スクレイピング・比較計算はバックエンドで実行する。

## Target

- Frontend: GitHub Pages
- Backend: Render (Web Service)

## Current Runtime Model

- フロントは静的配信（GitHub Pages）
- API Base URL はフロントコード内で自動選択
- 画面上に API Base URL 入力欄は表示しない
- バックエンドは FastAPI で `/v1/analyze` を提供

API URLの自動選択ルール:

- `localhost` / `127.0.0.1` では `http://localhost:8000`
- それ以外では `https://nk-calculator-api.onrender.com`

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
	- 複数指定: `https://npieju.github.io,https://nk-calc.example.com`

`ALLOWED_ORIGINS` はサーバー側で正規化される。

- 末尾 `/` を除去
- スキーム・ホストを小文字化

これにより `https://Npieju.github.io/` と `https://npieju.github.io` の差異を吸収する。

## 2) Frontend (GitHub Pages)

1. GitHub repository settings で Pages を有効化
2. `main` ブランチに push
3. GitHub Actions `Deploy Frontend to GitHub Pages` が実行される

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

## Troubleshooting

- `Failed to fetch` が続く場合:
	1. Render の最新デプロイが Active か確認
	2. `ALLOWED_ORIGINS` が Pages のオリジンと一致するか確認
	3. ブラウザ DevTools で preflight (`OPTIONS`) の CORS ヘッダを確認
- コード修正後も旧挙動の場合:
	- Render の再デプロイ漏れを最優先で確認する
