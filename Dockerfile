FROM python:3.10
WORKDIR /app/
RUN pip install -U pip --no-cache-dir
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt --no-cache-dir
RUN python -m spacy download en_core_web_lg
COPY main.py /app/
CMD ["uvicorn","--host","0.0.0.0", "main:app"]
EXPOSE 8000
