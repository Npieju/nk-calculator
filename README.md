# nk-calculator

netkeiba の出馬表URLを入力すると、オッズ取得から比較表示までを行うWebアプリです。

## Goal

- ユーザーがレースURLを入力
- サーバーはスクレイプ結果（entries / odds / status）を返却
- フロントエンドで比較計算を実行
- ブラウザで比較テーブルを表示・再計算・出力

## Monorepo Layout

- `apps/frontend`: GitHub Pages配信用フロントエンド（静的）
- `apps/backend`: APIサーバー（FastAPI）
- `packages/core`: 取得・正規化の共通ロジック
- `docs`: アーキテクチャ、API契約、デプロイ設計

## Current Features

- 入力URLは `race.netkeiba.com` / `race.sp.netkeiba.com` / `nar.netkeiba.com` の出馬表URL
- `race.sp.netkeiba.com` は自動で `race.netkeiba.com` に正規化
- 消し馬は `1〜18` チェックボックスで指定
- 全比較テーブル（all / c1〜c6 + 拡張）を表示
- 行内の高値・低値を強調表示（拡張比較の一部は別色ハイライト対応）
- 列ソート / 馬A・馬B絞り込み / 拡張パターントグル
- CSV / HTML 出力（直近計算結果を再利用）
- 同一URLはフロントキャッシュから再計算し、API再取得を省略（最新取得ON時は強制再取得）
- レース情報に `odds_updated_at` / `source_fetched_at` / `analyzed_at` を表示

## Data/Compute Notes

- APIは `race / entries / odds_status / odds` を返却
- 比較計算（all_market_compare, compare1〜6, 各extended）はフロントで実行
- フロント表示は英語キーを日本語ラベルへ変換
- 順不同券種は順序展開して欠けのない行列化
	- 馬連/ワイド: 2倍展開
	- 三連複: 6倍展開

## Why this split

GitHub Pagesは静的ホスティングのみのため、スクレイピングは `apps/backend` で実行します。
比較計算はフロントで行うことで、同一URLに対する消し馬の再計算をAPI未呼び出しで実現します。

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
- [Release Notes](docs/release-notes.md)

## Deploy

- Frontend: GitHub Pages（`.github/workflows/deploy-pages.yml`）
- Backend: Render（`render.yaml`）
