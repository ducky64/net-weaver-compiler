from typing import Optional, List

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS, cross_origin
from pydantic import BaseModel, ValidationError

from netlist_compiler import JsonNetlist, compile_netlist, CompilerResult


app = Flask(__name__)
CORS(app)


@app.route("/version", methods=['GET'])
def version():
  return "0.4"

@app.route("/compile", methods=['POST', 'OPTIONS'])
@cross_origin(origins=['*'])
def compile():
  try:
    json_netlist = JsonNetlist.model_validate_json(request.get_data())
  except ValidationError as e:
    return jsonify(CompilerResult(errors=["invalid input format"]).model_dump()), 400

  try:
    result = compile_netlist(json_netlist)
  except Exception as e:
    return jsonify(CompilerResult(errors=[str(e)]).model_dump()), 400

  return jsonify(result.model_dump())
