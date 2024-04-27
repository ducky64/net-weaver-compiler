from typing import Any, cast, Optional
from pydantic import BaseModel

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks'))
import edg_core
import edgir

import svgpcb_compiler


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
  name: str  # ???
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


class KicadFootprint(BaseModel):
  library: str  # full library name, including the library and the footprint
  name: str  # JS name, containing only the second part of the library name and with character replacements (eg . -> _)
  data: str  # raw Kicad .kicad_mod data


class ResultNet(BaseModel):
  name: str
  pads: list[list[str]]  # nested list is [block name, pin name]


class CompilerError(BaseModel):
  path: list[str]  # path to link / block / port, not including the constraint (if any)
  kind: str  # kind of error, eg "uncompiled block", "failed assertion"
  name: str = ""  # failing constraint name, if any
  details: str = ""  # longer description, optional (may be empty)


class CompilerResult(BaseModel):
  netlist: list[ResultNet] = []
  kicadNetlist: Optional[str] = None
  kicadFootprints: Optional[list[KicadFootprint]] = None
  svgpcbFunctions: Optional[list[str]] = None
  svgpcbInstantiations: Optional[list[str]] = None
  errors: list[CompilerError] = []


class JsonNetlistValidationError(Exception):
  def __init__(self, path: list[str], desc: str):
    super().__init__(f"{'.'.join(path)}: {desc}")
    self.path = path
    self.desc = desc


def tohdl_netlist(netlist: JsonNetlist) -> str:
  """Compiles the JsonNetlist to HDL, returning the HDL code."""
  code = f"""\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()
"""

  code += "\n"

  for node_name, node in netlist.graph.nodes.items():
    if not node_name.isidentifier():
      raise JsonNetlistValidationError([node_name], f"invalid block name")
    block_class = node.data.type
    if not node_name.isidentifier():
      raise JsonNetlistValidationError([node_name], f"invalid block class {block_class}")

    args_elts = []
    for arg_param in node.data.argParams:
      if arg_param.default_value != arg_param.value and arg_param.value:
        # parse and sanitize the value
        if arg_param.type == 'int':
          try:
            arg_value = str(int(arg_param.value))
          except ValueError:
            raise JsonNetlistValidationError([node_name, arg_param], f"invalid non-int value {arg_param.value}")
        elif arg_param.type == 'float':
          try:
            arg_value = str(float(arg_param.value))
          except ValueError:
            raise JsonNetlistValidationError([node_name, arg_param], f"invalid non-float value {arg_param.value}")
        elif arg_param.type == 'range':
          if not isinstance(arg_param.value, list) and len(arg_param.value) == 2:
            raise JsonNetlistValidationError([node_name, arg_param], f"invalid value {arg_param.value}")
          try:
            arg_value = f"({float(arg_param.value[0])}, {float(arg_param.value[1])})"
          except ValueError:
            raise JsonNetlistValidationError([node_name, arg_param], f"invalid range-int value {arg_param.value}")
        elif arg_param.type == 'string':
          raise JsonNetlistValidationError([node_name, arg_param.name], f"TODO: strings unsupported")
        else:
          raise JsonNetlistValidationError([node_name, arg_param.name], f"unknown arg-param type {arg_param.type}")

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

    is_array: Optional[bool] = None
    for label in labels:
      port_node = netlist.graph.nodes[label.nodeId]
      if port_node.data.ports[label.portIdx].elementOf is not None:
        continue  # ignored, request does not determine array-ness
      elif port_node.data.ports[label.portIdx].array:
        if is_array == False:
          raise JsonNetlistValidationError([], f"mixed array and non-array ports in label {name}")
        is_array = True
      else:
        if is_array == True:
          raise JsonNetlistValidationError([], f"mixed array and non-array ports in label {name}")
        is_array = False

    for label in labels:
      port_node = netlist.graph.nodes[label.nodeId]
      port_port = port_node.data.ports[label.portIdx]
      if not label.nodeId.isidentifier() and port_port.name.isidentifier():
        raise JsonNetlistValidationError([], f"invalid port label {label.nodeId}.{port_port.name}")
      if port_port.elementOf is not None:  # array request
        port_parent_port = port_node.data.ports[port_port.elementOf].name
        if not label.nodeId.isidentifier() and port_parent_port.isidentifier():
          raise JsonNetlistValidationError([], f"invalid port label {label.nodeId}.{port_parent_port}")
        if is_array:
          port_hdls.append(f"self.{label.nodeId}.{port_parent_port}.request_vector('{port_port.name}')")
        else:
          port_hdls.append(f"self.{label.nodeId}.{port_parent_port}.request('{port_port.name}')")
      else:  # single port
        port_hdls.append(f"self.{label.nodeId}.{port_port.name}")

    code += f"    self.connect({', '.join(port_hdls)})\n"

  # then directed edges
  # TODO currently not supported in frontend
  # for name, edge in netlist.graph.edges.items():
  #   src_node = netlist.graph.nodes[edge.src.node_id]
  #   src_port = src_node.data.ports[edge.src.idx]
  #   dst_node = netlist.graph.nodes[edge.dst.node_id]
  #   dst_port = dst_node.data.ports[edge.dst.idx]
  #
  #   if not edge.src.node_id.isidentifier() and src_port.name.isidentifier():
  #     raise JsonNetlistValidationError([], f"invalid connect to {edge.src.node_id}.{src_port.name}")
  #   if not edge.dst.node_id.isidentifier() and dst_port.name.isidentifier():
  #     raise JsonNetlistValidationError([], f"invalid connect to {edge.dst.node_id}.{dst_port.name}")
  #   src_hdl = f"self.{edge.src.node_id}.{src_port.name}"
  #   if src_port.array and dst_port.array:
  #     dst_hdl = f"self.{edge.dst.node_id}.{dst_port.name}.request_vector()"
  #   elif not src_port.array and dst_port.array:
  #     dst_hdl = f"self.{edge.dst.node_id}.{dst_port.name}.request()"
  #   else:
  #     dst_hdl = f"self.{edge.dst.node_id}.{dst_port.name}"
  #   code += f"    self.connect({src_hdl}, {dst_hdl})\n"

  return code


FOOTPRINT_LIBRARY_RELPATHS = [
  'footprints/kicad-footprints',
  'footprints/kiswitch/library/footprints',
  'footprints/OPL_Kicad_Library',
  'PolymorphicBlocks/examples',
]


def compile_netlist(netweave_netlist: JsonNetlist) -> CompilerResult:
  """Compiles the JsonNetlist to a KiCad netlist, returning the KiCad netlist along with a list of model
  validation errors (if any)."""
  code = f"""\
import os
os.chdir(edg_dir)

from edg import *

"""
        
  code += tohdl_netlist(netweave_netlist)

  code += """

compiled = ScalaCompiler.compile(MyModule, ignore_errors=True)
compiled.append_values(RefdesRefinementPass().run(compiled))
"""

  exec_env = {
    'edg_dir': os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks')
  }
  exec(code, exec_env)

  compiled = cast(edg_core.ScalaCompilerInterface.CompiledDesign, exec_env['compiled'])

  from electronics_model.NetlistGenerator import NetlistTransform
  from electronics_model.footprint import generate_netlist
  from edg import SvgPcbTemplateBlock

  netlist = NetlistTransform(compiled).run()
  kicad_netlist = generate_netlist(netlist, True)

  # generate structured netlist
  netlist_block_dict = {block.full_path: block for block in netlist.blocks}
  nets_obj = [ResultNet(
    name=net.name,
    pads=[['_'.join(netlist_block_dict[pin.block_path].path), pin.pin_name] for pin in net.pins])
    for net in netlist.nets]

  # fetch KiCad data
  all_block_footprints = []  # preserve ordering
  for block in netlist.blocks:
    if block.footprint not in all_block_footprints:
      all_block_footprints.append(block.footprint)

  all_footprints = []
  for footprint in all_block_footprints:
    footprint_split = footprint.split(':')
    if len(footprint_split) != 2:
      continue
    library, name = footprint_split
    footprint_data = None
    for library_container in FOOTPRINT_LIBRARY_RELPATHS:
      container_path = os.path.join(os.path.dirname(__file__), library_container)
      footprint_candidates = [
        os.path.join(container_path, library, name + '.kicad_mod'),
        os.path.join(container_path, library + '.pretty', name + '.kicad_mod')
      ]
      for footprint_candidate in footprint_candidates:
        if os.path.exists(footprint_candidate):
          with open(footprint_candidate) as f:
            footprint_data = f.read()
          break

      if footprint_data is not None:
        break

    if footprint_data is not None:
      all_footprints.append(KicadFootprint(library=footprint,
                                           name=SvgPcbTemplateBlock._svgpcb_footprint_to_svgpcb(footprint),
                                           data=footprint_data))
    else:
      print(f"failed to resolve footprint {footprint}")

  # generate SVGPCB data
  svgpcb_result = svgpcb_compiler.run(compiled, netlist)

  errors = []
  for error in compiled.errors:
    errors.append(CompilerError(
      path=edgir.local_path_to_str_list(error.path),
      kind=error.kind,
      name=error.name,
      details=error.details
    ))

  return CompilerResult(
    netlist=nets_obj,
    kicadNetlist=cast(str, kicad_netlist),
    kicadFootprints=all_footprints,
    svgpcbFunctions=svgpcb_result.functions,
    svgpcbInstantiations=svgpcb_result.instantiations,
    errors=errors
  )
