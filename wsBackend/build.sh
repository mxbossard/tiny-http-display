#! /bin/sh
SCRIPT_DIR=$( dirname $( readlink -f $0 ) )

tag=${1:-latest}

cd $SCRIPT_DIR
docker build -t ws-backend:$tag .
