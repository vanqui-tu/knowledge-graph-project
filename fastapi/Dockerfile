FROM tiangolo/uvicorn-gunicorn:python3.10-slim

RUN mkdir /fastapi

RUN mkdir /fastapi/uploaded-content

COPY requirements.txt /fastapi

WORKDIR /fastapi

RUN pip install -r requirements.txt

COPY . /fastapi

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]