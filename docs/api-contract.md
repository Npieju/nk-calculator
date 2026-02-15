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
    "race_id": "202608020611",
    "race_name": "京都記念",
    "race_date": "2026-02-15"
  },
  "odds_status": {
    "単勝": {"status": "ok", "rows": 12, "message": "..."}
  },
  "odds": {
    "単勝": [{"馬番": "1", "馬名": "ヘデントール", "オッズ": "3.7"}]
  },
  "comparisons": {
    "compare1": [{"馬番": 1, "馬名": "...", "単勝オッズ": 3.7}],
    "compare2": [{"馬番": 1, "馬名": "...", "複勝オッズ": 1.6, "三連複流し合成オッズ": 1.50}],
    "compare3": [{"馬番A": 1, "馬番B": 2, "馬連オッズ": 19.4, "馬単表裏合成オッズ": 19.27}]
  }
}
```

### Errors

- `400`: URL不正、入力不備
- `422`: 取得結果の欠損で比較不能
- `504`: 外部取得タイムアウト
- `500`: 予期しないサーバー障害

## GET /v1/health

- 目的: liveness/readiness確認
- 返却: `{ "status": "ok" }`
