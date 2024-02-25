from typing import Any
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

    code = f"""
import sys
import os.path
sys.path.append(edg_dir)

from edg import *
          
class MyModule(BoardTop):
  def __init__(self):
    super().__init__()
"""

    code += "\n"

    for node_name, node in netlist.graph.nodes.items():
      assert node_name.isidentifier(), f"non-identifier block name {node_name}"
      block_class = node.data.type
      assert block_class.isidentifier(), f"non-identifier block class {block_class}"
      code += f"    self.{node_name} = self.Block({block_class}())\n"

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
        if not node_port.array:
          net_ports.append(f"self.{port.name}.{port.portName}")
        else:
          net_ports.append(f"self.{port.name}.{port.portName}.request()")
      code += f"    self.connect({', '.join(net_ports)})\n"

    code += "\n"

    code += """compiled = ScalaCompiler.compile(MyModule, ignore_errors=True)
compiled.append_values(RefdesRefinementPass().run(compiled))
netlist_all = NetlistBackend().run(compiled)
netlist = netlist_all[0][1]
"""

    print(code)
    exec_env = {
      'edg_dir': os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks')
    }
    exec(code, exec_env)
    print(exec_env['netlist'])
