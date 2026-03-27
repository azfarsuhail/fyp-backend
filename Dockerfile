# Use an official Python runtime as a parent image (Slim version reduces OS bloat)
FROM python:3.10-slim

# Set environment variables
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing pyc files to disc
# PYTHONUNBUFFERED: Prevents Python from buffering stdout and stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /code

# Install system dependencies required for ML libraries and PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
# We do this BEFORE copying the rest of the code to leverage Docker cache
COPY requirements.txt /code/

# Install Python dependencies
# --no-cache-dir keeps the image smaller by not caching the downloaded packages
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
COPY . /code/

# Expose the port that FastAPI runs on
EXPOSE 8000

# Command to run the application using Uvicorn
# We point it to the app folder, main.py file, and the 'app' FastAPI instance
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]