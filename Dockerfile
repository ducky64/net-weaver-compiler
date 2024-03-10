# based on example from https://docs.docker.com/compose/gettingstarted/
FROM python:3.9-alpine
RUN apt-get install -y openjdk11-jre

WORKDIR /usr/app

COPY PolymorphicBlocks/ ./PolymorphicBlocks/
RUN pip install -r PolymorphicBlocks/requirements.txt

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY server.py netlist_compiler.py PolymorphicBlocks ./
ENV FLASK_APP=server.py
ENV FLASK_RUN_HOST=0.0.0.0

EXPOSE 80
CMD ["flask", "run", "--port", "80"]
