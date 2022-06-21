# Numerai universe updater

This is a simple Cloud Function that downloads the latest Numerai Universe (from Numerai S3 url)
and parse it into a list, then uploading it to gs://signals-stocks-lists/numerai-universe.txt

## Schedule
The cloud function it triggered by Cloud Scheduler every day at 23:00 UTC