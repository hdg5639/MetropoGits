import pandas as pd
from .models import Value
values = pd.DataFrame({'value': [Value('example').name]})
