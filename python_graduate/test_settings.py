from .settings import *

SECRET_KEY = 'd38cb68a49c01b12f1b930ef5217d30d'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3')
    }
}