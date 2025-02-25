import os

from django.conf import settings
from celery import Celery
from celery.schedules import crontab

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'youpay.settings.base')
app = Celery('youpay')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


app.conf.beat_schedule = {
    # Scheduler Name
    'expire-transactions': {
        # Task Name (Name Specified in Decorator)
        'task': 'set_transaction_expired',
        # Schedule
        # Execute at: every 1 minute
        'schedule': crontab(minute="*/1"),
        # Function Arguments
        'args': ()
    },
    'sync-configurations': {
            # Task Name (Name Specified in Decorator)
            'task': 'sync_configuration_data',
            # Schedule
            # Execute at: every 5 hours
            'schedule': crontab(minute="*/300"),
            # Function Arguments
            'args': ()
        },
    'fetch-groupgift-order-id': {
        'task': 'fetch_groupgift_order_id',
        'schedule': crontab(minute="*/1"),
        'args': ()
    }
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
