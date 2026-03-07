# frontend

GitHub Pagesへデプロイする静的フロントエンド。

## Responsibilities

- 中央 / 地方 / 海外タブのレース選択UI
- URL入力（副機能）
- `/v1/race-selector` と `/v1/analyze` の呼び出し
- APIレスポンスを使った比較計算（all / c1〜c6 / extended）
- 消し馬再計算、CSV / HTML出力、失敗理由表示

## Next

- Vite + React + TypeScript で初期化
- selector UI をコンポーネント分割しやすい形へ再整理
