from typing import TypedDict, Tuple, Optional, Any
import json
import inspect
from pydantic import BaseModel

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks'))


class JsonNetPort(BaseModel):
  nodeId: str  # unused, internal node ID
  portIdx: int  # unused
  name: str  # name of node, may be same as node ID
  portName: str  # name of port (consistent w/ HDL)

class JsonNodePort(BaseModel):
  name: str  # name of port (consistent w/ HDL)
  leftRightUpDown: str  # ignored
  type: str  # type of port
  array: bool  # whether port is an array
  _idx: int

class JsonNodeArgParam(BaseModel):
  name: str  # name of parameter (consistent w/ HDL)
  type: str  # type of parameter, ...
  defaultValue: Any  # value of parameter

class JsonNodeData(BaseModel):
  name: str  # ???
  type: str  # node class
  superClasses: list[str]  # superclasses, excluding self type
  ports: list[JsonNodePort]
  argParams: list[JsonNodeArgParam]

class JsonNode(BaseModel):
  data: JsonNodeData
  ports: list[list[str]]  # port names
  id: str  # node ID

class JsonGraph(BaseModel):
  nodes: dict[str, JsonNode]
  edges: dict[str, Any]  # ignored

class JsonNetlist(BaseModel):
  nets: list[list[JsonNetPort]]
  graph: JsonGraph
  graphUIData: Any  # ignored


if __name__ == '__main__':
  with open("BasicBlinky.json") as f:
    netlist = JsonNetlist.model_validate_json(f.read())

    print(netlist)
    print(netlist.graph.nodes)
