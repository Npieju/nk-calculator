# Architecture

## Context

既存の

- nk-tracer: オッズ取得
- nr-scope: 比較計算

を統合し、単一のWeb体験を提供する。

## High-level Design

- Frontend (static SPA)
  - URL入力
  - 進捗表示
  - 比較テーブル表示
  - 結果ダウンロード
- Backend API (FastAPI)
  - URL検証
  - オッズ取得実行
  - 比較計算
  - 結果整形
- Core package (pure Python)
  - 取得・正規化・比較ロジック
  - UI非依存

## Runtime Flow

1. FrontendがレースURLを送信
2. Backendがrace_id抽出と入力検証
3. Coreのscraperでオッズ取得
4. Coreのpredictorで比較テーブルを生成
5. Backendが統合レスポンスを返却
6. Frontendが表形式で表示

## Component Boundaries

### apps/frontend

- 役割: 表示と操作のみ
- 禁止: スクレイピング・業務ロジック

### apps/backend

- 役割: API提供、例外処理、レート制御
- 依存: `packages/core`

### packages/core

- 役割: ドメインロジック
- 要件: 副作用を最小化、テストしやすい関数設計

## Data Contracts

- 入力: race URL
- 出力: raceメタ情報、券種別オッズ、比較1/2/3、ステータス

## Non-functional Requirements

- Timeout: API 30秒上限（MVP）
- Retry: 取得時に短い再試行
- Cache: race_id単位で短期キャッシュ
- Observability: request_id、処理時間、失敗理由

## Evolution Plan

- Phase 1 (MVP): 同期API
- Phase 2: 非同期ジョブ（queue）
- Phase 3: 履歴保存・認証・監視強化
