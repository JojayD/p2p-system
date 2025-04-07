# Use Python 3 as the base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install required dependencies
RUN pip install flask requests

# Copy the application code
COPY p2pnode.py .

# Expose the port that the Flask app runs on
EXPOSE 5000

# Command to run the application
CMD ["python", "p2pnode.py"]