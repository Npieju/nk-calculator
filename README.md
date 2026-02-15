# nk-calculator

URL入力からオッズ取得・比較計算までを一気通貫で実行するWebアプリ。

## Goal

- ユーザーがレースURLを入力
- サーバーでオッズを取得
- 比較テーブル（比較1/2/3）を計算
- ブラウザで結果を表示
- 必要ならCSV/JSONをダウンロード

## Monorepo Layout

- `apps/frontend`: GitHub Pages配信用フロントエンド（静的）
- `apps/backend`: APIサーバー（FastAPI）
- `packages/core`: 取得・計算の共通ドメインロジック
- `docs`: アーキテクチャ、API契約、デプロイ設計

## Why this split

GitHub Pagesは静的ホスティングのみのため、スクレイピングや計算処理は `apps/backend` で実行します。
フロントエンドは `apps/backend` のAPIを呼び出す構成にします。

## Quick Start (planned)

1. `apps/backend` を起動
2. `apps/frontend` を起動
3. フロントから `POST /v1/analyze` を実行

詳細は以下:

- [Architecture](docs/architecture.md)
- [API Contract](docs/api-contract.md)
- [Deployment](docs/deployment.md)
