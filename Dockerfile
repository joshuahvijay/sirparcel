# Use an official Python runtime as a base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Streamlit apps typically run on port 8501. 
# Azure App Service will need to know which port to map.
EXPOSE 8501

# Command to run the Streamlit app when the container starts
# --server.port=8501: ensures Streamlit uses the exposed port
# --server.address=0.0.0.0: ensures it listens on all interfaces
ENTRYPOINT ["streamlit", "run", "sirparcel.py", "--server.port=8501", "--server.address=0.0.0.0"]