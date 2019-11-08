FROM python:3.7.5-slim

COPY requirements.txt /requirements.txt

RUN pip install -r /requirements.txt --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/

COPY . /app

WORKDIR /app

CMD ["gunicorn", "app:app", "-c", "gunicorn.conf.py"]
