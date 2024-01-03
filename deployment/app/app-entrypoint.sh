#!/bin/bash
source /vault/secrets/application.env

set -m

# SIGTERM handler
term_handler() {
  echo "Caught SIGTERM signal!"
  echo "$(date) Caught SIGTERM for $HOSTNAME" >> /ygag/logs/app.out.gunicorn.console.log
  sleep 1
  if [ $pid -ne 0 ]; then
    kill -TERM "$pid"
    wait "$pid"
  fi
  echo "$(date) Exiting container $HOSTNAME" >> /ygag/logs/app.out.gunicorn.console.log
  exit 143;
}

trap 'term_handler' SIGTERM

gunicorn youpay.wsgi -b :8000 --keep-alive 10 --graceful-timeout 30 --thread 10 \
  --max-requests 300 --max-requests-jitter 1000 --timeout 120 --log-level=debug \
  --worker-class eventlet --backlog 500 -w 3 --worker-connections 300 \
  --access-logfile /ygag/logs/app.out.gunicorn.access.log \
  --error-logfile /ygag/logs/app.out.gunicorn.error.log >> /ygag/logs/app.out.gunicorn.console.log 2>&1 &

pid="$!"

# wait indefinitely
wait
