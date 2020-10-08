#! /bin/sh -e
SCRIPT_DIR=$( dirname $( readlink -f $0 ) )
cd $SCRIPT_DIR

IMAGE_PREFIX="mby/"
projectName="${PWD##*/}"
image="$IMAGE_PREFIX$projectName"
ctName="$projectName"

usage() {
	>&2 echo "usage: $0 [-r] [tag] [args]"
	>&2 echo ""
	>&2 echo "Run current project image."
	>&2 echo "By default tag is latest. If first command arg is an existing tag, will consume it as a tag."
	>&2 echo ""
	>&2 echo "	-r : renew the build kill and start the fresh image."
	>&2 echo ""
	>&2 echo "examples:"
        >&2 echo "	$0 latest foo bar baz"
	>&2 echo "	$0 foo bar baz"
	exit 1
}

renew=false
if [ "$1" = "-r" ]
then
	renew=true
	shift 1
	>&2 echo "Killing container: [$ctName] ..."
	docker kill $ctName || true
fi

>&2 echo "List of existing images:"
if $renew || ! docker image ls $image | tail -n-1 | grep "$image"
then
	$renew || >&2 echo "Docker image $projectName not found. Launching build ..."
	./build.sh latest
fi

tag="$1"
args="$@"
if docker image ls $image:$tag | tail -n-1 | grep "$image:$tag" > /dev/null
then
	# First arg is an existing tag consume it
	image="$image:$tag"
	shift 1
	args="$@"
fi

>&2 echo "Launching container: [$ctName] with image: [$image] and args: [$args] ..."

cmd="docker run --rm -d --name=$ctName -p3000:5000 $image $args"
>&2 echo "$cmd"
eval "$cmd"
docker logs -f $ctName
