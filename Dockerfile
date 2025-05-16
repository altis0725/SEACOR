FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (including config, public, seacor package)
COPY seacor/ ./seacor/

# Expose the application port
EXPOSE 8000

# Launch the app with Uvicorn
CMD ["uvicorn", "seacor.__main__:app", "--host", "0.0.0.0", "--port", "8000"]
