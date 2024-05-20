# Use a smaller base image
FROM python:3.9-slim as base

# Set the working directory in the container
WORKDIR /usr/src/app

# Install build dependencies in a separate stage
FROM base as build

# Install build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    gcc \
    libglib2.0-dev \
    libbluetooth-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container
COPY . .

# Install Python packages including bluepy
RUN pip install --no-cache-dir -r requirements.txt

# Create an empty status.json file
RUN rm -rf /usr/src/app/status.json && touch /usr/src/app/status.json

# Install cron
RUN apt-get update && apt-get install -y --no-install-recommends cron \
    && rm -rf /var/lib/apt/lists/*

# Copy the cron job setup script
COPY add_cronjob.sh /usr/src/app/add_cronjob.sh
RUN chmod +x /usr/src/app/add_cronjob.sh

# Copy the start services script
COPY start_services.sh /usr/src/app/start_services.sh
RUN chmod +x /usr/src/app/start_services.sh

# Final stage
FROM base

# Copy only necessary files from the build stage
COPY --from=build /usr/src/app /usr/src/app
COPY --from=build /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libbluetooth3 \
    && rm -rf /var/lib/apt/lists/*

# Expose the port the API will run on
EXPOSE 5000

# Run the start_services script
CMD ["/usr/src/app/start_services.sh"]
