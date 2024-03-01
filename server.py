from typing import Optional, List

from flask import Flask, jsonify
from pydantic import BaseModel, ValidationError

from netlist_compiler import JsonNetlist


app = Flask(__name__)

class ErrorCompilerResponse(BaseModel):
  error: str

class NetlistCompilerResponse(BaseModel):
  kicadNetlist: Optional[str]
  errors: List[str]

@app.route("/compile")
def compile():
  try:
    netlist = JsonNetlist.model_validate_json("BasicBlinky.json")
  except ValidationError as e:
    return jsonify(ErrorCompilerResponse(error="invalid input format")), 400

  return jsonify(NetlistCompilerResponse(kicadNetlist="TODO").dict())