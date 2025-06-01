# Use an official Python base image
FROM python:3.10-slim

# System dependencies for pdfplumber (requires poppler)
RUN apt-get update && \
    apt-get install -y poppler-utils && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Streamlit config: allow secrets, no CORS for local, listen on all interfaces
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_ENABLECORS=false

# You can set your OpenAI API key as an environment variable (for non-secret config)
# ENV OPENAI_API_KEY=sk-...

# Command to run the app
CMD ["streamlit", "run", "app.py"]
