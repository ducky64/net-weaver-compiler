FROM python:3.9-alpine

RUN apk update
RUN pip install --no-cache-dir pipenv

WORKDIR /usr/src/app
COPY requirements.txt server.py netlist_compiler.py PolymorphicBlocks ./

RUN pip install -r requirements.txt

EXPOSE 5000
ENTRYPOINT ["/usr/src/app/bootstrap.sh"]
