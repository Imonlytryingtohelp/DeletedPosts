FROM python:3.14-slim

WORKDIR /app

# Copy application files
COPY Bot ./Bot
COPY populate_config.py .
COPY config ./config

# prepare configuration directory (volume may later overwrite it)
RUN mkdir -p /app/config

# Install dependencies
RUN pip install --no-cache-dir praw PyYAML 

ENV PYTHONUNBUFFERED=1

# Always generate config.py from environment before starting
CMD ["/bin/sh", "-c", "python populate_config.py && python Bot/main.py"]
