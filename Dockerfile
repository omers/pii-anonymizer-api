FROM python:3.10

WORKDIR /app/

COPY requirements.txt main.py /app/

RUN pip install -U pip --no-cache-dir && \
    pip install -r /app/requirements.txt --no-cache-dir && \
    python -m spacy download en_core_web_lg

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
