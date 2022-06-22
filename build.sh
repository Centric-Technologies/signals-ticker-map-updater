#!/bin/bash

OPTIND=1
red=$(tput setaf 1)
green=$(tput setaf 2)
reset=$(tput sgr0)

unset tag

while getopts :t: o; do
    case "${o}" in
    t)
        tag=${OPTARG}
        ;;
    esac
done

if [ -z $tag ]; then
    echo "${red}Please specify a tag for build using the -t arg${reset}"
    exit 1
fi

if [ -z $GEMFURY_PULL ]; then
    echo "${red}No Gemfury token is set. Please export GEMFURY_TOKEN and retry${reset}"
    exit 1
fi

echo "Building docker image ticker-map-updater:$tag"
docker build --build-arg GEMFURY_TOKEN=$GEMFURY_PULL -t ticker-map-updater:$tag .

if [ $? != 0 ]; then
    echo "${red}Failed building docker image. Please check why and retry${reset}"
    exit 1
fi
