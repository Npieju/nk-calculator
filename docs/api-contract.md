# API Contract (MVP)

## POST /v1/analyze

### Request

```json
{
  "race_url": "https://race.netkeiba.com/race/shutuba.html?race_id=202608020611&rf=race_list",
  "excluded_horses": ["5", "9"]
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
    "analyzed_at": "2026-02-15T09:00:26.433008+00:00"
  },
  "odds_status": {
    "単勝": {"status": "ok", "rows": 12, "message": "..."}
  },
  "odds": {
    "単勝": [{"馬番": "1", "馬名": "ヘデントール", "オッズ": "3.7"}]
  },
  "comparisons": {
    "all_market_compare": [
      {
        "horse_no": 1,
        "horse_name": "ヘデントール",
        "win_odds": 3.7,
        "exacta_second_flow_odds": 21.4,
        "trifecta_second_flow_odds": 186.1,
        "trifecta_third_flow_odds": 205.3
      }
    ],
    "compare1": [{"horse_no": 1, "horse_name": "...", "win_odds": 3.7, "spread": 12.3}],
    "compare2": [{"horse_no": 1, "horse_name": "...", "place_odds": 1.6, "trio_flow_odds": 1.5, "spread": 0.1}],
    "compare3": [{"horse_no_a": 1, "horse_name_a": "...", "horse_no_b": 2, "quinella_odds": 19.4, "exacta_both_flow_odds": 19.27, "spread": 0.13}]
  }
}
```

## Column Key Policy

- API: 英語キー（安定契約）
- Frontend: 日本語ラベルへ変換して表示

主要キー例:

- `win_odds`, `place_odds`
- `quinella_flow_odds`, `wide_flow_odds`
- `exacta_first_flow_odds`, `exacta_second_flow_odds`
- `trio_flow_odds`
- `trifecta_first_flow_odds`, `trifecta_second_flow_odds`, `trifecta_third_flow_odds`
- `spread`

### Errors

- `400`: URL不正（`/race/shutuba.html?race_id=...` 以外）
- `422`: 取得結果の欠損で比較不能
- `500`: 予期しないサーバー障害

## GET /v1/health

- 目的: liveness/readiness確認
- 返却: `{ "status": "ok" }`
