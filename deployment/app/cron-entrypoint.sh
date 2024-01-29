#!/bin/bash

set -m

# SIGTERM handler
term_handler() {
  echo "Caught SIGTERM signal!"
  echo "$(date) Caught SIGTERM for $HOSTNAME" >> /ygag/logs/cron.out.celery.console.log
  sleep 1
  if [ $pid -ne 0 ]; then
    kill -TERM "$pid"
    wait "$pid"
  fi
  echo "$(date) Exiting container $HOSTNAME" >> /ygag/logs/cron.out.celery.console.log
  exit 143;
}

trap 'term_handler' SIGTERM

celery -A youpay beat -l INFO -f /ygag/logs/cron.out.celery.log >> /ygag/logs/cron.out.celery.console.log 2>&1 &

pid="$!"

# wait indefinitely
wait
