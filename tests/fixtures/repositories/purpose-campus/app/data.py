import pandas as pd
from .model import Payload
frame = pd.DataFrame({'value':[Payload('sample').value]})
