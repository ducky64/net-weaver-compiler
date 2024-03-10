import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("url")
parser.add_argument("payload")
args = parser.parse_args()

url = 'https://www.w3schools.com/python/demopage.php'
myobj = {'somekey': 'somevalue'}

with open(args.payload) as f:
  payload = f.read()

x = requests.post(args.url, data={'netlist': payload})

print(x.text)
