# Deployment Plan

## Constraint

GitHub Pagesは静的配信のみ。バックエンドは別ホスティングが必要。

## Recommended

- Frontend: GitHub Pages
- Backend: Render または Fly.io
- Optional Cache/DB: Redis / Postgres

## Environments

- dev: ローカルDocker or 直接実行
- stg: 低コストインスタンス
- prod: APIスケール設定あり

## CI/CD (proposed)

### Frontend Workflow

- push to main
- build static assets
- deploy to GitHub Pages

### Backend Workflow

- push to main
- run tests/lint
- build container
- deploy to Render/Fly

## Configuration

Frontend env:

- `VITE_API_BASE_URL` (or `NEXT_PUBLIC_API_BASE_URL`)

Backend env:

- `REQUEST_TIMEOUT_SECONDS`
- `CACHE_TTL_SECONDS`
- `ALLOWED_ORIGINS`

## Security Notes

- CORSはfrontend originのみに限定
- 外部URLはドメイン許可リストで検証
- レート制限とログ監視を有効化
