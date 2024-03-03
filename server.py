from typing import Optional, List

from flask import Flask, jsonify, request
from pydantic import BaseModel, ValidationError

from netlist_compiler import JsonNetlist, compile_netlist


class NetlistCompilerResponse(BaseModel):
  kicadNetlist: Optional[str]
  errors: List[str]


app = Flask(__name__)


@app.route("/compile", methods=['POST'])
def compile():
  try:
    json_netlist = JsonNetlist.model_validate_json(request.form['netlist'])
  except ValidationError as e:
    return jsonify(NetlistCompilerResponse(kicadNetlist=None, errors=["invalid input format"]).model_dump()), 400

  try:
    kicad_netlist, model_errors = compile_netlist(json_netlist)
  except Exception as e:
    return jsonify(NetlistCompilerResponse(kicadNetlist=None, errors=[str(e)]).model_dump()), 400

  return jsonify(NetlistCompilerResponse(
    kicadNetlist=kicad_netlist,
    errors=model_errors
  ).model_dump())
