import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("payload")
args = parser.parse_args()

with open(args.payload) as f:
  payload = f.read()

x = requests.post(args.url, data=payload)

print(x.text)
