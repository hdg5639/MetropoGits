from fastapi import FastAPI
from .model import Payload
from .service import run
app = FastAPI()
@app.get('/value')
def get_value():
    return run(Payload('example'))
