FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir streamlit==1.41.1
COPY app.py store.py decoder.py ./
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
