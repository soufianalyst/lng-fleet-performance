FROM python:3.12-slim
WORKDIR /app
COPY synthetic-data-generator/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY synthetic-data-generator/ .
ENTRYPOINT ["python", "run.py"]
