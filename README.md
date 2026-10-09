# hhvm-images

_A public github container registry mirror of the docker hub hhvm builds_

## GHCR

Docker hub remains the preferred distribution channel for hhvm images.
This GHCR mirror exists for use in github actions, where pulling from docker
hundreds of times per hour is not cached, and encounters rate limits.
