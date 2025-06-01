# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
# Ensure your .env.encrypted.bak (or similar) is copied if needed by encrypted_env_loader.py
COPY . .
COPY secrets/.env.encrypted.bak /app/secrets/.env.encrypted.bak
# Or if it's in a 'secrets' folder:
# COPY secrets/ /app/secrets/


# Command to run the application using Gunicorn (will use gunicorn_config.py)
CMD ["gunicorn", "--config", "./gunicorn_config.py", "app:app"]