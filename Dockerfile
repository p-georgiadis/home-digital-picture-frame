FROM python:3.12-slim

# Install system dependencies: ffmpeg for video thumbnails, etc.
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ app/
COPY templates/ templates/
COPY static/ static/

# Set environment variables
ENV FLASK_APP=app/app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080

# Expose the port
EXPOSE 8080

# Run waitress as the server
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "app.app:app"]
