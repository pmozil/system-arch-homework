# Use Python 3.9 as the base image
FROM python:latest

# Set the working directory in the container
WORKDIR /app

# Install the necessary dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . /app/

# Expose the necessary port
EXPOSE 8000

# Command to run the FastAPI app
CMD ["python3", "consumer.py"]
