from typing import Any, cast, Tuple, List, Optional
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

class JsonGraph(BaseModel):
  nodes: dict[str, JsonNode]
  edges: dict[str, JsonEdge]

class JsonNetlist(BaseModel):
  nets: list[list[JsonNetPort]]
  graph: JsonGraph
  graphUIData: Any  # ignored


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

    args_str = ""
    for arg_param in node.data.argParams:
      if arg_param.default_value != arg_param.value and arg_param.value:
        args_str += f", {arg_param.name}={arg_param.value}"
    code += f"    self.{node_name} = self.Block({block_class}(){args_str})\n"
  code += "\n"

  for net in netlist.nets:
    net_ports = []
    for port in net:
      assert port.name.isidentifier(), f"non-identifier block reference {port.name}"
      assert port.portName.isidentifier(), f"non-identifier port reference {port.portName}"

      node = netlist.graph.nodes[port.name]
      node_ports = [node_port for node_port in node.data.ports if node_port.name == port.portName]
      assert len(node_ports) == 1
      node_port = node_ports[0]

      edge_dsts = [edge for (name, edge) in netlist.graph.edges.items()
                   if edge.dst.node_id == port.name and edge.dst.portName == port.portName]

      if node_port.array and edge_dsts:  # if array and a edge target, considered a request
        net_ports.append(f"self.{port.name}.{port.portName}.request()")
      else:
        net_ports.append(f"self.{port.name}.{port.portName}")
    code += f"    self.connect({', '.join(net_ports)})\n"
  code += "\n"

  return code

def compile_netlist(netlist: JsonNetlist) -> Tuple[str, List[str]]:
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
