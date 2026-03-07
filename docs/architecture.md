# Architecture

## Context

既存の `nk-tracer`（取得）と `nr-scope`（比較）を統合し、
中央 / 地方タブからレース選択して分析まで完了する単一体験を提供する。
URL入力は副機能として残す。

## High-level Design

- Frontend (static SPA)
  - 中央 / 地方 / 海外タブ
  - 今日のレース表示
  - 日付 + レース場での絞り込み
  - URL入力（副機能）
  - 進捗表示
  - 比較計算（消し馬反映）
  - 比較テーブル表示
  - CSV/HTML出力
- Backend API (FastAPI)
  - URL検証
  - レース一覧取得
  - オッズ取得実行
  - スクレイプ結果返却
- Core package (pure Python)
  - 取得・正規化ロジック
  - UI非依存

## Runtime Flow

1. Frontendが `GET /v1/race-selector` で中央 / 地方の日次レース一覧を取得、またはURL入力を使う
2. Frontendが選択レースのURLを `POST /v1/analyze` へ送信
3. Backendがrace_id抽出と入力検証を行い、必要ならURLを出馬表URLへ正規化
4. Coreのscraperでオッズ取得、または日次レース一覧を取得
5. Backendが `race / entries / odds_status / odds` または race selector 用の meeting 一覧を返却
6. Frontendが比較テーブル（all / c1〜c6 / extended）を計算
7. Frontendが表形式で表示

## Component Boundaries

### apps/frontend

- 役割: レース選択UI、表示、比較計算、エクスポート、同一URL再計算
- キャッシュ:
  - メモリキャッシュ（同一URLでAPI未呼び出し再計算）
  - `sessionStorage` 永続化（リロード後も再利用）
  - レース一覧キャッシュ（scope + date 単位の再利用）

### apps/backend

- 役割: API提供、URL正規化、日次レース一覧取得、スクレイプキャッシュ、例外処理
- 依存: `packages/core`

### packages/core

- 役割: ドメインロジック
- 要件: 副作用を最小化、テストしやすい関数設計

## Data Contracts

- 入力: race URL + 除外馬番、または scope + date
- 出力: raceメタ情報、entries、券種別オッズ、取得ステータス、meeting一覧
- 比較列キー: フロント内部は英語、UI表示で日本語ラベル化

## Odds Table Design

順不同券種を順序展開して、欠けのないテーブルへ正規化する。

- 馬連/ワイド: `a-b` と `b-a` を保持
- 三連複: 6順列を保持
- 馬単/三連単: 元々順序ありのためそのまま

この設計により、`馬名A` 側の抽出・集計が一貫する。

## Flow Synthesis Strategy (Frontend)

流し合成は先頭列（A側）基準で算出する。

- 馬連/ワイド: 先頭馬ごと
- 三連複: 先頭馬 + 後続ソートキーで重複順列を圧縮
- 比較3: 馬連は方向付きで保持し、馬単裏表は逆数和逆数で比較

比較結果は `spread = (行内最大オッズ / 基準列) * 100` で算出する。

## Non-functional Requirements

- Timeout: 外部取得20秒（現設定）
- Observability: `odds_updated_at` / `analyzed_at` を返却
- Resilience:
  - CORS origin正規化（大小文字・末尾スラッシュ差異を吸収）
  - URL正規化（`race.sp.netkeiba.com` / `nar.sp.netkeiba.com` をdesktop hostへ統一し、`race_id` から出馬表URLへ変換）
  - 三層キャッシュ（backend race-list cache + backend scrape cache + frontend same-URL cache）

## Evolution Plan

- Phase 1 (MVP): 同期API
- Phase 2: 非同期ジョブ（queue）
- Phase 3: 履歴保存・認証・監視強化
