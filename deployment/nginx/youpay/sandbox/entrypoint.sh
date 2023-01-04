#!/bin/bash
set -m



# SIGTERM handler
term_handler() {
  echo "Caught SIGTERM signal!"
  echo "Caught SIGTERM signal!" >> /var/log/nginx/error.log
  sleep 1
  if [ $pid -ne 0 ]; then
    kill -QUIT "$pid"
    wait "$pid"
  fi
  exit 143;
}

trap 'term_handler' SIGTERM

./sbin/nginx -p /ygag/nginx/ >> /var/log/nginx/error.log 2>&1 &

pid="$!"

# wait indefinitely
wait
