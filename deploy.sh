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
    echo "${red}Please specify a tag for deployment using the -t arg${reset}"
    exit 1
fi

if [ -z "${GEMFURY_PULL}" ]; then
    echo "${red}env variable GEMFURY_PULL is not set, cannot continue${reset}"
    exit 1
fi

echo "Building image with tag $tag"
bash build.sh -t $tag
if [ $? != 0 ]; then
    echo "${red}Failed building docker image. Please check why and retry${reset}"
    exit 1
fi

echo "Tagging the image before pushing to the repository"
docker tag ticker-map-updater:$tag eu.gcr.io/trend-master-1612506394802/ticker-map-updater:$tag

echo "Pushing the image to GCP container repository"
docker push eu.gcr.io/trend-master-1612506394802/ticker-map-updater:$tag

# echo "Deploying the new version to Cloud Run"
# gcloud run deploy ticker-map-updater --image=eu.gcr.io/trend-master-1612506394802/signals-predictor-api:$tag --memory=8G --cpu=4 --region=europe-west4

echo "${green}The image with tag $tag is built and pushed. ${reset}"
