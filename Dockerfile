ARG PYTHON_VERSION=3.10
ARG NGINX_VERSION=stable

# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:${PYTHON_VERSION}-alpine as django_python

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

# Turns off warning unverified HTTPS request
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"

# COPY docker/docker-healthcheck.sh /usr/local/bin/docker-healthcheck
# RUN chmod +x /usr/local/bin/docker-healthcheck

# HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD ["docker-healthcheck"]

RUN apk add --no-cache python-dev

WORKDIR /srv/app

# Install pip requirements
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python -m manage collectstatic

CMD ["python", "manage.py", "runserver", "0.0.0.0:80"]

FROM django_python AS celery_python

WORKDIR /srv/app

ARG CELERY_BROKER=""
ENV CELERY_BROKER ${CELERY_BROKER}

ARG CELERY_RESULT_BACKEND=""
ENV CELERY_RESULT_BACKEND ${CELERY_RESULT_BACKEND}

CMD ["celery", "-A", "telegram-parser", "worker", "-l", "info"]

FROM django_python AS flower_python

WORKDIR /srv/app

ARG CELERY_BROKER=""
ENV CELERY_BROKER ${CELERY_BROKER}

CMD ["celery", "-A", "telegram-parser", "flower"]

FROM nginx:${NGINX_VERSION}-alpine as django_nginx

WORKDIR /srv/app

COPY --from=django_python /srv/app/public public/
COPY docker/nginx/certs/localhost+2.pem /etc/ssl/certs/localhost+2.pem
COPY docker/nginx/certs/localhost+2-key.pem /etc/ssl/private/localhost+2-key.pem
COPY docker/nginx/certs/root.crt /usr/local/share/ca-certificates/root.crt
COPY docker/nginx/default.conf /etc/nginx/conf.d/default.conf

RUN cat /usr/local/share/ca-certificates/root.crt >> /etc/ssl/ca-certificates.crt && \
    update-ca-certificates