FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app

RUN pip install --trusted-host pypi.python.org -r requirements.txt

COPY ./app/ /app

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]