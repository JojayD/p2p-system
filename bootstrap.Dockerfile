FROM python:3.9

WORKDIR /app

COPY bootstrap.py .

# Install required packages
RUN pip install flask flask-cors

# Expose the default port
EXPOSE 8000

# Run the bootstrap node
CMD ["python", "bootstrap.py", "8000"]