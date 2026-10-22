from .model import Payload
from .store import engine
def run(value: Payload) -> str:
    if engine is None:
        raise RuntimeError('storage adapter unavailable')
    return value.value
