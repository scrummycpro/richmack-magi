# Use the official lightweight Python image
FROM python:3.9-slim

# Set environment variables to ensure that Python outputs everything that's printed
# to the console
ENV PYTHONUNBUFFERED=1

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

# Create a directory for file uploads
RUN mkdir -p /app/uploads

# Make port 5005 available to the world outside this container
EXPOSE 5005

# Define environment variable
ENV FLASK_APP app.py

# Run app.py when the container launches
CMD ["flask", "run", "--host=0.0.0.0", "--port=5005"]