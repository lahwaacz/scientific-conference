# an adaptation of the standalone multistage pattern from
# https://github.com/astral-sh/uv-docker-example/blob/main/standalone.Dockerfile
# (the builder tag pins the uv version that wrote uv.lock)

# first, build the application in the /app directory
FROM ghcr.io/astral-sh/uv:0.12.24-trixie-slim@sha256:71b09e37995e49a5aed44c63be80d3e15dcb39e18e31c24a2925b66d4b6d5980 AS builder

# compile bytecode while installing (faster startup), copy files from the
# cache mount instead of hardlinking (it is a separate filesystem)
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# omit development dependencies
ENV UV_NO_DEV=1

# configure the Python directory so it is consistent across stages
ENV UV_PYTHON_INSTALL_DIR=/python

# only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# install the interpreter pinned by .python-version (3.13, same as dev/CI)
# before the project, for caching
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.python-version,target=.python-version \
    uv python install

WORKDIR /app

# install dependencies from the locked set in a layer keyed on the lock
# files only, so source changes do not reinstall them
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=.python-version,target=.python-version \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# copy the entire project source tree
COPY . /app

# create the project environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

# then, use a final image without uv
FROM debian:trixie-slim@sha256:a29215f6a35e51e22adffa17f89e9d2ef06214e64a2bad10d765c46aea49f11f

# setup a non-root user
RUN groupadd --gid 1000 nonroot \
 && useradd --gid 1000 --uid 1000 --create-home nonroot

# copy the Python installation from the builder
COPY --from=builder /python /python

# copy the application from the builder
COPY --from=builder --chown=nonroot:nonroot /app /app

# place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# NOTE: this does not work with gunicorn - it does not serve static files
# collect static files into the STATIC_ROOT directory
# see https://docs.djangoproject.com/en/6.1/howto/static-files/
#RUN python manage.py collectstatic
# NOTE: when combined with the VOLUME instruction below, changes in the files
#       from the RUN command would not affect the existing volume

# create a directory for staticfiles (will be mounted as a volume)
#RUN mkdir /app/staticfiles
#VOLUME /app/staticfiles

# the MEDIA_ROOT directory exists in the project but must be set as a volume
# (the content from git will initialize the container volume when it is created)
#VOLUME /app/media

# use the non-root user to run our application
USER nonroot

# use /app as the working directory
WORKDIR /app

# publish a port on which the application should be accessible from the host
# (and other containers)
EXPOSE 8000

# collect static files (frontend nginx serves them from DJANGO_STATIC_ROOT),
# perform database migrations and run the webserver; exec makes gunicorn PID 1
# so it receives SIGTERM directly (graceful worker shutdown)
ENTRYPOINT ["/app/docker-entrypoint.sh"]
