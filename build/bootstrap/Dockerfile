FROM docker

# poetry because we need it to run
# git because we need it to get version data
# the others because we need them for psutil
RUN apk add poetry git build-base linux-headers python3-dev

ENV POETRY_VIRTUALENVS_PATH=/tmp/poetry/venv
ENV POETRY_CACHE_DIR=/tmp/poetry/cache
