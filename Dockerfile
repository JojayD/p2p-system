# Use Python 3.9 slim as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app
RUN mkdir -p /app/storage

# Install dependencies
RUN pip install --no-cache-dir flask requests flask-cors

# Copy the app code
COPY p2pnode.py .

# Expose the range of ports used by the nodes
EXPOSE 8000-8050

# Default command (can be overridden in docker-compose)
CMD ["python", "p2pnode.py", "--bootstrap", "8000"]
