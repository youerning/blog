FROM python:3.7-alpine3.13

RUN pip install --no-cache-dir -i http://pypi.douban.com/simple/ --trusted-host=pypi.douban.com/simple fastapi pyyaml motor aiofiles uvicorn 

COPY ./app /app

WORKDIR /app

ENTRYPOINT ["uvicorn", "app:app", "--port", "80", "--host", "0.0.0.0"]
EXPOSE 80
