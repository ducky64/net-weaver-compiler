from typing import TypedDict, Tuple, Optional, Any
import json
import inspect

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks'))


class JsonNet(TypedDict):
  nodeId: str  # unused, internal node ID
  portIdx: str  # unused
  name: str  # name of node, may be same as node ID
  portName: str  # name of port (consistent w/ HDL)

class JsonNodePort(TypedDict):
  name: str  # name of port (consistent w/ HDL)
  leftRightUpDown: str  # ignored
  type: str  # type of port
  array: bool  # whether port is an array
  _idx: int

class JsonNodeArgParam(TypedDict):
  name: str  # name of parameter (consistent w/ HDL)
  type: str  # type of parameter, ...
  defaultValue: Any  # value of parameter

class JsonNodeData(TypedDict):
  name: str  # ???
  type: str  # node class
  superClasses: list[str]  # superclasses, excluding self type
  ports: list[JsonNodePort]
  argParams: list[JsonNodeArgParam]

class JsonNode(TypedDict):
  data: JsonNodeData
  ports: list[list[str]]  # port names
  id: str  # node ID

class JsonGraph(TypedDict):
  nodes: list[Tuple[str, JsonNode]]
  edges: list[Tuple[str, Any]]  # ignored

class JsonNetlist(TypedDict):
  nets: list[JsonNet]
  nodes: JsonGraph
  graphUiData: Any  # ignored


if __name__ == '__main__':
  with open("BasicBlinky.json") as f:
    # netlist: JsonNetlist = json.load(f)
    netlist = JsonNetlist(**json.load(f))
    print(netlist)
    print(netlist.nodes)
