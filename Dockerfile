# Use the official Python image from the Docker Hub
FROM python:3.8-slim
LABEL authors="Thomas White"

# Install dependencies
RUN pip install --no-cache-dir flask sqlalchemy flask-sqlalchemy

# Create and set the working directory
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Create the config directory for the database file
RUN mkdir -p /config

# Run the command to start the Flask application
CMD ["flask", "run"]
