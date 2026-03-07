# API Contract

## GET /v1/race-selector

中央 / 地方タブのレース選択UIで使う日次レース一覧APIです。

### Query

- `scope`: `jra` または `nar`
- `date`: `YYYYMMDD` または `YYYY-MM-DD`
- `force_refresh`: 省略可。`true` のとき backend キャッシュを無視して再取得

### Response

```json
{
  "scope": "jra",
  "date": "20260307",
  "cache_hit": true,
  "cache_age_seconds": 18,
  "source_fetched_at": "2026-03-07T01:23:45.000000+00:00",
  "cache_stored_at": "2026-03-07T01:23:45.100000+00:00",
  "available_venues": ["中山", "阪神"],
  "meetings": [
    {
      "venue_name": "中山",
      "meeting_title": "2回 中山 3日目",
      "races": [
        {
          "race_id": "202606020301",
          "race_no": 1,
          "race_no_text": "1R",
          "race_title": "3歳未勝利",
          "start_time": "10:05",
          "distance": "ダ1200m",
          "field_size": 16,
          "race_url": "https://race.netkeiba.com/race/shutuba.html?race_id=202606020301"
        }
      ]
    }
  ]
}
```

## POST /v1/analyze

### Request

```json
{
  "race_url": "https://race.netkeiba.com/odds/index.html?type=b1&race_id=202608020611",
  "excluded_horses": ["5", "9"],
  "force_refresh": false
}
```

`race_url` は `race_id` を含む netkeiba のレース関連ページURLを受け付け、内部で出馬表URLへ正規化します。

### Response

```json
{
  "race": {
    "race_url": "https://race.netkeiba.com/race/shutuba.html?race_id=202608020611&rf=race_list",
    "race_id": "202608020611",
    "race_name": "京都記念",
    "race_date": "2026-08-02",
    "odds_updated_at": "2026-02-15 15:37:38",
    "cache_hit": true,
    "cache_age_seconds": 22,
    "source_fetched_at": "2026-02-15T09:00:00.000000+00:00",
    "cache_stored_at": "2026-02-15T09:00:00.100000+00:00",
    "is_past_race": false,
    "refresh_recommended": true,
    "analyzed_at": "2026-02-15T09:00:26.433008+00:00"
  },
  "entries": [
    {"馬番": "1", "馬名": "ヘデントール"}
  ],
  "odds_status": {
    "単勝": {"status": "ok", "rows": 12, "message": "..."}
  },
  "odds": {
    "単勝": [{"馬番": "1", "馬名": "ヘデントール", "オッズ": "3.7"}]
  }
}
```

## Response Policy

- APIはスクレイプ結果（entries / odds / status）を返却
- レース選択UIは `GET /v1/race-selector` を使って日次レース一覧を取得
- 比較テーブル生成（compare1〜6, all_market_compare, extended）はフロントエンドで実行
- フロントは同一URLならキャッシュしたAPIレスポンスを再利用し、消し馬再計算をAPI未呼び出しで行う

## Odds key examples

- `単勝`, `複勝`, `枠連`, `馬連`, `ワイド`, `馬単`, `三連複`, `三連単`
- 各値は `[{ "組み合わせ": "...", "オッズ": "..." }, ...]` 形式

### Errors

- `400`: `scope` / `date` / `race_url` の形式不正、または `race_id` 不足
- `500`: 予期しないサーバー障害

## GET /v1/health

- 目的: liveness/readiness確認
- 返却: `{ "status": "ok" }`
