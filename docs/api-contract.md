# API Contract

## POST /v1/analyze

### Request

```json
{
  "race_url": "https://race.netkeiba.com/race/shutuba.html?race_id=202608020611&rf=race_list",
  "excluded_horses": ["5", "9"],
  "force_refresh": false
}
```

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
- 比較テーブル生成（compare1〜6, all_market_compare, extended）はフロントエンドで実行
- フロントは同一URLならキャッシュしたAPIレスポンスを再利用し、消し馬再計算をAPI未呼び出しで行う

## Odds key examples

- `単勝`, `複勝`, `枠連`, `馬連`, `ワイド`, `馬単`, `三連複`, `三連単`
- 各値は `[{ "組み合わせ": "...", "オッズ": "..." }, ...]` 形式

### Errors

- `400`: URL不正（`/race/shutuba.html?race_id=...` 以外）
- `500`: 予期しないサーバー障害

## GET /v1/health

- 目的: liveness/readiness確認
- 返却: `{ "status": "ok" }`
