# Architecture

## Context

既存の `nk-tracer`（取得）と `nr-scope`（比較）を統合し、
URL入力だけで分析まで完了する単一体験を提供する。

## High-level Design

- Frontend (static SPA)
  - URL入力
  - 進捗表示
  - 比較テーブル表示
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
4. Coreのpredictorで比較テーブル（比較1/2/3）を生成
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

- 入力: race URL + 除外馬番
- 出力: raceメタ情報、券種別オッズ、比較1/2/3、取得ステータス
- 比較列キー: APIでは英語、UI表示は日本語

## Odds Table Design

順不同券種を順序展開して、欠けのないテーブルへ正規化する。

- 馬連/ワイド: `a-b` と `b-a` を保持
- 三連複: 6順列を保持
- 馬単/三連単: 元々順序ありのためそのまま

この設計により、`馬名A` 側の抽出・集計が一貫する。

## Flow Synthesis Strategy

流し合成は先頭列（A側）基準で算出する。

- 馬連/ワイド: 先頭馬ごと
- 三連複: 先頭馬 + 後続ソートキーで重複順列を圧縮
- 比較3: 馬連は方向付きで保持し、馬単裏表は逆数和逆数で比較

## Non-functional Requirements

- Timeout: 外部取得20秒（現設定）
- Observability: `odds_updated_at` / `analyzed_at` を返却
- Resilience: CORS origin正規化（大小文字・末尾スラッシュ差異を吸収）

## Evolution Plan

- Phase 1 (MVP): 同期API
- Phase 2: 非同期ジョブ（queue）
- Phase 3: 履歴保存・認証・監視強化
