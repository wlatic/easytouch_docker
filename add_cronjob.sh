#!/bin/bash

# Add the cron job with the schedule from the environment variable
echo "$CRON_SCHEDULE root python /usr/src/app/read.py >> /var/log/cron.log 2>&1" > /etc/cron.d/microair-cron

# Give execution rights on the cron job
chmod 0644 /etc/cron.d/microair-cron

# Apply cron job
crontab /etc/cron.d/microair-cron

# Create the log file to be able to run tail
touch /var/log/cron.log

# Start cron in the foreground (useful for debugging)
cron -f
