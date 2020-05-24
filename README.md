# REST API для сервиса b2b продаж: дипломный проект для университета Нетологии

### Описание

Дипломная состоит из:
1. Приложения Django
2. Application-сервера Gunicorn
3. Очереди задач Celery
4. Менеджера процессов Supervisor
5. БД PostgreSQL
6. БД Redis
7. Реверс-прокси сервера Nginx

### Запуск
Для запуска всего этого цирка используется Docker Compose.

```
$ git clone https://github.com/Klavionik/python_gradwork.git
$ cd python_gradwork
$ docker-compose up
```

После успешного запуска сервисов провести миграцию.  

```
$ docker-compose exec app python manage.py migrate
```

Приложение будет доступно с хоста по адресу `127.0.0.1:5555`.

### Использование

[Документация и демонстрационные запросы Postman](https://documenter.getpostman.com/view/9813544/Szt8eppQ)
