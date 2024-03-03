FROM python:3.9-alpine

RUN apk update
RUN pip install --no-cache-dir pipenv

WORKDIR /usr/app

COPY PolymorphicBlocks ./
RUN pip install -r PolymorphicBlocks/requirements.txt

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY server.py netlist_compiler.py PolymorphicBlocks ./
ENV FLASK_APP=server.py

EXPOSE 7761
CMD ["flask", "run", "--port", "7761"]
