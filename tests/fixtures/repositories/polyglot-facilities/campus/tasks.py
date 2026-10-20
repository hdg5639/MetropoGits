from celery import shared_task
from .models import Value
@shared_task
def transform():
    return Value('task').name
