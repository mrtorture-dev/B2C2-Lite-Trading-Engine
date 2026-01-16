import os
from celery import Celery

# Establecer el módulo de configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Usar la configuración de Django (namespace='CELERY')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Cargar tareas de todas las apps registradas
app.autodiscover_tasks()