FROM ubuntu:latest

# Plex Variables
ENV ELEVENLABSAPI ''
ENV ALEXAFOLDER '/app/homeassistant/www/audio'

# Install cron and python
RUN apt-get update
RUN apt-get -y install python3.6
RUN apt-get -y install python3-pip

ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles
RUN apt-get -y install tzdata

# Create a directory for your script
WORKDIR /app

# Copy the script into the container
COPY api.py /app/api.py
COPY voices.json /app/voices.json

# Give execute permission to the script
RUN chmod +x /app/api.py

# Expose volume
RUN ln -s /app/data /data
VOLUME /data
VOLUME /app/homeassistant

# Install required dependencies
RUN pip install Flask
RUN pip install requests
RUN pip install python-dotenv

EXPOSE 5325

# Save env vars and run cron
CMD python3 /app/api.py