FROM python:3.9-slim

ARG GEMFURY_TOKEN

WORKDIR /app
# pip upgrade
RUN pip install --upgrade pip

COPY requirements.txt requirements.txt
COPY requirements-private.txt requirements-private.txt


RUN pip install -r requirements.txt
RUN pip install -q --index-url https://${GEMFURY_TOKEN}:@pypi.fury.io/centrictechnologiesltd/ -r requirements-private.txt 

COPY . /app

ENTRYPOINT ["python3", "main.py"]