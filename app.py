from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
from pydantic import ValidationError

from netlist_compiler import JsonNetlist, compile_netlist, CompilerResult, CompilerError
from hdl_generator import JsonNetlistValidationError


app = Flask(__name__)
CORS(app)


@app.route("/version", methods=['GET'])
def version():
  return "0.12"

@app.route("/compile", methods=['POST', 'OPTIONS'])
@cross_origin(origins=['*'])
def compile():
  try:
    json_netlist = JsonNetlist.model_validate_json(request.get_data())
    result = compile_netlist(json_netlist)
  except JsonNetlistValidationError as e:
    return jsonify(CompilerResult(
      edgHdl="",
      errors=[
        CompilerError(path=[e.path], kind="invalid input", details=e.desc)
      ]
    ).model_dump()), 400
  except ValidationError as e:
    return jsonify(CompilerResult(
      edgHdl="",
      errors=[
        CompilerError(path=[], kind="invalid input", details="format error")
      ]
    ).model_dump()), 400
  except Exception as e:
    return jsonify(CompilerResult(
      edgHdl="",
      errors=[
        CompilerError(path=[], kind=f"internal error", details=repr(e))
      ]
    ).model_dump()), 400

  return jsonify(result.model_dump())

@app.route("/library", methods=['GET'])
@cross_origin(origins=['*'])
def library():
  with open("resources/library.json") as f:
    return f.read()
