# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the requirements file into the container at /usr/src/app
COPY requirements.txt ./

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY . .

# Inject version
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV FLASK_APP run.py

# Run the command to start the server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]
