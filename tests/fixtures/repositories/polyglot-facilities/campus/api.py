from fastapi import FastAPI
from .models import Value
app = FastAPI()
@app.get('/health')
def health() -> Value:
    return Value('ok')
