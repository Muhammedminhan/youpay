import os
from pathlib import Path

# LOGGING
BASE_DIR = Path(__file__).resolve().parent.parent.parent

LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# ElasticBeanstalk python application logs
LOGS_PREFIX = 'app.out.'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        }
    },
    'formatters': {
        'standard': {
            'format': "[%(asctime)s] %(levelname)s %(name)s [%(pathname)s:"
                      "%(lineno)d] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S",
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'standard',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, LOGS_PREFIX + 'ygpay.log'),
            'formatter': 'standard',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db': {
        },
        # 'django.db.backends': {
        #     'level': 'DEBUG',
        #     'handlers': ['console'],
        # },
        'django.request': {
            'handlers': ['mail_admins', 'console'],
            'level': 'ERROR',
            'propagate': True,
        },

    }
}
