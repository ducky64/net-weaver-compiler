# based on example from https://docs.docker.com/compose/gettingstarted/
FROM python:3.9-alpine
RUN apk add openjdk11

WORKDIR /usr/app

COPY PolymorphicBlocks/requirements.txt ./PolymorphicBlocks/requirements.txt
RUN pip install -r PolymorphicBlocks/requirements.txt

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY footprints/ ./footprints/

COPY resources/ ./resources/
COPY PolymorphicBlocks/ ./PolymorphicBlocks/

COPY *.py ./
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 80
CMD ["flask", "run", "--port", "80"]
