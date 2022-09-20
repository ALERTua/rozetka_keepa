FROM python:3.10.6
MAINTAINER ALERT <alexey.rubasheff@gmail.com>

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --progress-bar=off --no-cache-dir -U pip setuptools wheel && pip install --progress-bar=off --no-cache-dir -r /app/requirements.txt

COPY entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

COPY rozetka_keepa /app/rozetka_keepa/

ENV \
    PYTHONIOENCODING=utf-8 \
    LC_ALL=en_US.UTF-8 \
    LANG=en_US.UTF-8 \
    LANGUAGE=en_US.UTF-8

CMD ["/app/entrypoint.sh"]
