FROM python:3.8-alpine
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
RUN mkdir /var/code && mkdir /var/logs
RUN apk update && apk add postgresql-dev gcc python3-dev musl-dev
WORKDIR /var/code
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .