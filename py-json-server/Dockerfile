FROM python:3.8-alpine
MAINTAINER Maxime Bossard <mxbossard@pm.me>

RUN apk add --update py3-setuptools
#RUN apk add --update py-pip
RUN pip3 install --upgrade pip

RUN apk add gcc
RUN apk add musl-dev

ARG PIPX_BIN_DIR=/usr/bin
RUN pip3 install --user pipx --no-warn-script-location
#RUN python3 -m pipx ensurepath

RUN /root/.local/bin/pipx install json-server.py

EXPOSE 3000

COPY db.json db.json

CMD ["json-server", "db.json"]
