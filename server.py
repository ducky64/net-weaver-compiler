from typing import Optional, List

from flask import Flask, jsonify, request
from pydantic import BaseModel, ValidationError

from netlist_compiler import JsonNetlist


class NetlistCompilerResponse(BaseModel):
  kicadNetlist: Optional[str]
  errors: List[str]


app = Flask(__name__)


@app.route("/compile", methods=['POST'])
def compile():
  try:
    netlist = JsonNetlist.model_validate_json(request.form['netlist'])
  except ValidationError as e:
    return jsonify(NetlistCompilerResponse(kicadNetlist=None, errors=["invalid input format"]).model_dump()), 400

  return jsonify(NetlistCompilerResponse(kicadNetlist="TODO", errors=[]).model_dump())
