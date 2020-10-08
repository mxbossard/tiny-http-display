#! /bin/sh
SCRIPT_DIR=$( dirname $( readlink -f $0 ) )
cd $SCRIPT_DIR

projectName=${PWD##*/}
tag=${1:-latest}

docker build -t mby/$projectName:$tag .
