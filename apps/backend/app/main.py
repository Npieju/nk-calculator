from fastapi import FastAPI

app = FastAPI(title="nk-calculator-api", version="0.1.0")


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
