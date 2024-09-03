from typing import Any, cast, Optional
from pydantic import BaseModel


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
  srcSinkBi: Optional[str]  # ignored
  idx: int
  elementOf: Optional[int] = None  # refers to idx of parent if array, otherwise None

class JsonNodeArgParam(BaseModel):
  name: str  # name of parameter (consistent w/ HDL)
  type: str  # type of parameter, ...
  default_value: Optional[Any]  # default value of parameter in library, if any
  value: Optional[Any]  # value as specified by the user

class JsonNodeData(BaseModel):
  name: str  # user-facing name
  type: str  # node class
  superClasses: list[str]  # superclasses, excluding self type
  ports: list[JsonNodePort]
  argParams: list[JsonNodeArgParam]

class JsonNode(BaseModel):
  data: JsonNodeData
  ports: list[list[str]]  # port names
  id: str  # node ID

# currently unused
# class JsonEdgeTarget(BaseModel):
#   node_id: str  # node ID
#   idx: int  # port index, unused
#   portName: str  # name of port (consistent w/ HDL)
#
# class JsonEdge(BaseModel):
#   data: Any  # ignored
#   src: JsonEdgeTarget
#   dst: JsonEdgeTarget
#   id: str  # ignored

class JsonLabel(BaseModel):
  labelName: str
  nodeId: str
  portIdx: int

class JsonGraph(BaseModel):
  nodes: dict[str, JsonNode]
  # edges: dict[str, JsonEdge]  # currently unused

class JsonNetlist(BaseModel):
  nets: list[list[JsonNetPort]]
  graph: JsonGraph
  graphUIData: Any  # ignored
  labels: dict[str, JsonLabel] = {}  # labels, if any - new feature
