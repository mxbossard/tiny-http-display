FROM python:3.9-slim-buster
MAINTAINER Maxime Bossard <mxbossard@pm.me>

RUN apt update ; apt upgrade -y
RUN apt install -y build-essential
RUN pip install pandas
RUN pip install CherryPy

EXPOSE 8080

COPY *.py .

ENTRYPOINT ["python", "server.py"]
