from typing import Any, cast, Optional
from pydantic import BaseModel

import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks'))
import edg_core

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


class KicadFootprint(BaseModel):
  library: str  # library name, first part of a KiCad footprint full name
  name: str  # name (within a library), second part of a KiCad footprint full name
  data: str  # raw Kicad .kicad_mod data


class ResultNet(BaseModel):
  name: str
  pads: list[list[str]]  # nested list is [block name, pin name]


class CompilerResult(BaseModel):
  netlist: list[ResultNet] = []
  kicadNetlist: Optional[str] = None
  kicadFootprints: Optional[list[KicadFootprint]] = None
  svgpcbFunctions: Optional[list[str]] = None
  svgpcbInstantiations: Optional[list[str]] = None
  errors: list[str] = []


def tohdl_netlist(netlist: JsonNetlist) -> str:
  """Compiles the JsonNetlist to HDL, returning the HDL code."""
  code = f"""\
class MyModule(SimpleBoardTop):
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


EXAMPLE_KICAD_FOOTPRINTS = [
  KicadFootprint(
    library="Diode_SMD",
    name="D_SMA",
    data="""\
(footprint D_SMA (version 20210108) (generator KicadMod) (layer F.Cu) (tedit 63CB70A4)
  (descr "Diode SMA (DO-214AC)")
  (tags "Diode SMA (DO-214AC)")
  (attr smd)
  (fp_text reference REF** (at 0 -2.5) (layer F.SilkS)
    (effects (font (size 1 1) (thickness 0.15)))
  )
  (fp_text value D_SMA (at 0 2.6) (layer F.Fab)
    (effects (font (size 1 1) (thickness 0.15)))
  )
  (fp_text user ${REFERENCE} (at 0 -2.5) (layer F.Fab)
    (effects (font (size 1 1) (thickness 0.15)))
  )
  (fp_line (start -3.51 1.65) (end 2 1.65) (layer F.SilkS) (width 0.12))
  (fp_line (start -3.51 -1.65) (end -3.51 1.65) (layer F.SilkS) (width 0.12))
  (fp_line (start -3.51 -1.65) (end 2 -1.65) (layer F.SilkS) (width 0.12))
  (fp_line (start 3.5 -1.75) (end 3.5 1.75) (layer F.CrtYd) (width 0.05))
  (fp_line (start -3.5 1.75) (end -3.5 -1.75) (layer F.CrtYd) (width 0.05))
  (fp_line (start -3.5 -1.75) (end 3.5 -1.75) (layer F.CrtYd) (width 0.05))
  (fp_line (start 3.5 1.75) (end -3.5 1.75) (layer F.CrtYd) (width 0.05))
  (fp_line (start 2.3 1.5) (end -2.3 1.5) (layer F.Fab) (width 0.1))
  (fp_line (start 0.50118 0.75032) (end 0.50118 -0.79908) (layer F.Fab) (width 0.1))
  (fp_line (start 2.3 -1.5) (end 2.3 1.5) (layer F.Fab) (width 0.1))
  (fp_line (start -0.64944 0.00102) (end 0.50118 0.75032) (layer F.Fab) (width 0.1))
  (fp_line (start 2.3 -1.5) (end -2.3 -1.5) (layer F.Fab) (width 0.1))
  (fp_line (start 0.50118 0.00102) (end 1.4994 0.00102) (layer F.Fab) (width 0.1))
  (fp_line (start -0.64944 0.00102) (end -1.55114 0.00102) (layer F.Fab) (width 0.1))
  (fp_line (start -0.64944 -0.79908) (end -0.64944 0.80112) (layer F.Fab) (width 0.1))
  (fp_line (start -0.64944 0.00102) (end 0.50118 -0.79908) (layer F.Fab) (width 0.1))
  (fp_line (start -2.3 1.5) (end -2.3 -1.5) (layer F.Fab) (width 0.1))
  (pad 1 smd roundrect (at -2 0) (size 2.5 1.8) (layers F.Cu F.Paste F.Mask) (roundrect_rratio 0.1388888889))
  (pad 2 smd roundrect (at 2 0) (size 2.5 1.8) (layers F.Cu F.Paste F.Mask) (roundrect_rratio 0.1388888889))
  (model ${KICAD6_3DMODEL_DIR}/Diode_SMD.3dshapes/D_SMA.wrl
    (at (xyz 0 0 0))
    (scale (xyz 1 1 1))
    (rotate (xyz 0 0 0))
  )
)
"""
  )
]


def compile_netlist(netlist: JsonNetlist) -> CompilerResult:
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
# netlist_all = NetlistBackend().run(compiled)
# netlist = netlist_all[0][1]
# svgpcb_all = SvgPcbBackend().run(compiled)
# svgpcb_functions = svgpcb_all[0][1]
# svgpcb_instantiations = svgpcb_all[1][1]
# svgpcb_netlist = svgpcb_all[2][1]
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
  # TODO IMPLEMENT ME

  # generate SVGPCB data
  svgpcb_result = svgpcb_compiler.run(compiled)

  if compiled.error:  # TODO plumb through structured errors instead of relying on strings
    errors = [compiled.error]
  else:
    errors = []
  return CompilerResult(
    netlist=nets_obj,
    kicadNetlist=cast(str, kicad_netlist),
    kicadFootprints=EXAMPLE_KICAD_FOOTPRINTS,
    svgpcbFunctions=svgpcb_result.functions,
    svgpcbInstantiations=svgpcb_result.instantiations,
    errors=errors
  )
