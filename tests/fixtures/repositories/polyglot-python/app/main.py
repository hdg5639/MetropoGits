from fastapi import FastAPI as API
from .service import Service

app = API()


@app.get("/health")
async def health():
    return Service().get()


if __name__ == "__main__":
    raise RuntimeError("Must never run this target")
