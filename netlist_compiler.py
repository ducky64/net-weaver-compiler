from typing import Any, cast, Tuple, Optional
from pydantic import BaseModel

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks'))
import edg_core


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
  idx: int

class JsonNodeArgParam(BaseModel):
  name: str  # name of parameter (consistent w/ HDL)
  type: str  # type of parameter, ...
  default_value: Optional[Any]  # default value of parameter in library, if any
  value: Optional[Any]  # value as specified by the user

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

class JsonEdgeTarget(BaseModel):
  node_id: str  # node ID
  idx: int  # port index, unused
  portName: str  # name of port (consistent w/ HDL)

class JsonEdge(BaseModel):
  data: Any  # ignored
  src: JsonEdgeTarget
  dst: JsonEdgeTarget
  id: str  # ignored

class JsonLabel(BaseModel):
  labelName: str
  nodeId: str
  portIdx: int

class JsonGraph(BaseModel):
  nodes: dict[str, JsonNode]
  edges: dict[str, JsonEdge]

class JsonNetlist(BaseModel):
  nets: list[list[JsonNetPort]]
  graph: JsonGraph
  graphUIData: Any  # ignored
  labels: dict[str, JsonLabel] = {}  # labels, if any - new feature


def tohdl_netlist(netlist: JsonNetlist) -> str:
  """Compiles the JsonNetlist to HDL, returning the HDL code."""
  code = f"""\
class MyModule(JlcBoardTop):
  def __init__(self):
    super().__init__()
"""

  code += "\n"

  for node_name, node in netlist.graph.nodes.items():
    assert node_name.isidentifier(), f"non-identifier block name {node_name}"
    block_class = node.data.type
    assert block_class.isidentifier(), f"non-identifier block class {block_class}"

    args_elts = []
    for arg_param in node.data.argParams:
      if arg_param.default_value != arg_param.value and arg_param.value:
        # parse and sanitize the value
        if arg_param.type == 'int':
          arg_value = str(int(arg_param.value))
        elif arg_param.type == 'float':
          arg_value = str(float(arg_param.value))
        elif arg_param.type == 'range':
          assert isinstance(arg_param.value, list) and len(arg_param.value) == 2
          arg_value = f"({float(arg_param.value[0])}, {float(arg_param.value[1])})"
        elif arg_param.type == 'string':
          raise ValueError(f"TODO")
        else:
          raise ValueError(f"unknown arg param type {arg_param.type}")

        args_elts.append(f"{arg_param.name}={arg_value}")
    code += f"    self.{node_name} = self.Block({block_class}({', '.join(args_elts)}))\n"
  code += "\n"

  labels_by_name: dict[str, list[JsonLabel]] = { }
  if netlist.labels:
    for id, label in netlist.labels.items():
      labels_by_name.setdefault(label.labelName, []).append(label)

  # generate labels first
  for name, labels in labels_by_name.items():
    port_hdls = []
    for label in labels:
      port_node = netlist.graph.nodes[label.nodeId]
      port_port = port_node.data.ports[label.portIdx].name
      port_hdls.append(f"self.{label.nodeId}.{port_port}")

    code += f"    self.connect({', '.join(port_hdls)})\n"

  # then directed edges
  for name, edge in netlist.graph.edges.items():
    src_node = netlist.graph.nodes[edge.src.node_id]
    src_port = src_node.data.ports[edge.src.idx]
    dst_node = netlist.graph.nodes[edge.dst.node_id]
    dst_port = dst_node.data.ports[edge.dst.idx]

    src_hdl = f"self.{edge.src.node_id}.{src_port.name}"
    if src_port.array and dst_port.array:
      dst_hdl = f"self.{edge.dst.node_id}.{dst_port.name}.request_vector()"
    elif not src_port.array and dst_port.array:
      dst_hdl = f"self.{edge.dst.node_id}.{dst_port.name}.request()"
    else:
      dst_hdl = f"self.{edge.dst.node_id}.{dst_port.name}"
    code += f"    self.connect({src_hdl}, {dst_hdl})\n"

  return code

def compile_netlist(netlist: JsonNetlist) -> Tuple[str, list[str]]:
  """Compiles the JsonNetlist to a KiCad netlist, returning the KiCad netlist along with a list of model
  validation errors (if any)."""
  code = f"""\
import os
os.chdir(edg_dir)

from edg import *

"""
        
  code += tohdl_netlist(netlist)

  code += """

compiled = ScalaCompiler.compile(MyModule, ignore_errors=True)
compiled.append_values(RefdesRefinementPass().run(compiled))
netlist_all = NetlistBackend().run(compiled)
netlist = netlist_all[0][1]"""

  exec_env = {
    'edg_dir': os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks')
  }
  exec(code, exec_env)

  compiled_netlist = cast(str, exec_env['netlist'])
  compiled = cast(edg_core.ScalaCompilerInterface.CompiledDesign, exec_env['compiled'])

  if compiled.error:
    return compiled_netlist, [compiled.error]
  else:
    return compiled_netlist, []
