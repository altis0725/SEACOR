FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (including config, public, seacor package)
COPY core/ ./core/
COPY tools/ ./tools/
COPY utils/ ./utils/
COPY crews/ ./crews/
COPY config/ ./config/
COPY public/ ./public/
COPY logs/ ./logs/
COPY main.py ./

# Expose the application port
EXPOSE 8000

# Launch the app with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
