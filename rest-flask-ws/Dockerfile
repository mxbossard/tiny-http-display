FROM python:3.8-alpine
MAINTAINER Maxime Bossard <mxbossard@pm.me>

RUN apk add --update py3-setuptools
RUN pip3 install --upgrade pip

RUN apk add gcc
RUN apk add musl-dev

RUN pip install flask-restful

ENV FLASK_APP app
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

EXPOSE 5000

RUN mkdir /home/flaskapp
WORKDIR /home/flaskapp

#COPY $PWD/flask_app /home/flaskapp
COPY *.py /home/flaskapp/
RUN pip3 install -r requirements.txt || true
#CMD ["gunicorn","--bind","0.0.0.0:5000","wsgi:app"]

ENV FLASK_ENV=development

ENTRYPOINT ["python"]
CMD ["server.py"]
