# nk-calculator

URL入力からオッズ取得・比較計算までを一気通貫で実行するWebアプリ。

## Goal

- ユーザーがレースURLを入力
- サーバーでオッズを取得
- 比較テーブル（比較1/2/3）を計算
- ブラウザで結果を表示
- スマホでも比較しやすく表示

## Monorepo Layout

- `apps/frontend`: GitHub Pages配信用フロントエンド（静的）
- `apps/backend`: APIサーバー（FastAPI）
- `packages/core`: 取得・計算の共通ドメインロジック
- `docs`: アーキテクチャ、API契約、デプロイ設計

## Current Features

- 入力は `netkeiba` 出馬表URL（`/race/shutuba.html?race_id=...`）
- 消し馬は `1〜18` チェックボックスで指定
- 比較1/2/3 は行内の高値・低値を強調表示
- 各比較テーブルで列ソート可能
- 比較3は `馬名A` フィルターあり（全表示も可能）
- レース情報に `odds_updated_at` / `analyzed_at` を表示

## Data Notes

- APIの比較テーブル列キーは英語
- フロント表示は日本語ラベルへ変換
- 順不同券種は順序展開して欠けのない行列化
	- 馬連/ワイド: 2倍展開
	- 三連複: 6倍展開

## Why this split

GitHub Pagesは静的ホスティングのみのため、スクレイピングや計算処理は `apps/backend` で実行します。
フロントエンドは `apps/backend` のAPIを呼び出す構成にします。

## Quick Start (MVP)

### 1) Backend

```bash
cd apps/backend
/workspace/.venv/bin/pip install -r requirements.txt
/workspace/.venv/bin/uvicorn app.main:app --reload --port 8000
```

### 2) Frontend (static)

任意の静的サーバーで `apps/frontend/index.html` を配信します。

```bash
cd apps/frontend
/workspace/.venv/bin/python -m http.server 5173
```

ブラウザで `http://localhost:5173` を開いて実行します。

フロントはAPI URLを内部で自動選択します。

- localhost: `http://localhost:8000`
- それ以外: `https://nk-calculator-api.onrender.com`

そのため画面上に `API Base URL` 入力欄はありません。

詳細は以下:

- [Architecture](docs/architecture.md)
- [API Contract](docs/api-contract.md)
- [Deployment](docs/deployment.md)

## Deploy

- Frontend: GitHub Pages（`.github/workflows/deploy-pages.yml`）
- Backend: Render（`render.yaml`）
