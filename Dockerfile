FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8-slim

# copy only requirements.txt as it rarely changed. This is done to utilize
# docker layer caching, thus avoid calling 'pip install' during every build
# ref: https://towardsdatascience.com/docker-for-python-development-83ae714468ac#3837
COPY requirements.txt /app/
WORKDIR /app

RUN pip3 install -r requirements.txt

# copy full working dirs
COPY . /app

EXPOSE 80

CMD ./docker-entrypoint.sh
