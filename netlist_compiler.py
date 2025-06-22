from typing import cast, Optional
from pydantic import BaseModel

import os.path
from PolymorphicBlocks.edg import core, edgir
from netweaver_interface import JsonNetlist
from hdl_generator import tohdl_netlist


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
  edgHdl: str
  netlist: list[ResultNet] = []
  kicadNetlist: Optional[str] = None
  kicadFootprints: Optional[list[KicadFootprint]] = None
  svgpcbFunctions: Optional[list[str]] = None
  svgpcbInstantiations: Optional[list[str]] = None
  bom: Optional[str] = None  # CSV string of the BOM
  errors: list[CompilerError] = []


FOOTPRINT_LIBRARY_RELPATHS = [
  'footprints/kicad-footprints',
  'footprints/kiswitch/library/footprints',
  'footprints/OPL_Kicad_Library',
  'PolymorphicBlocks/examples',
]


def compile_netlist(netweaver_netlist: JsonNetlist) -> CompilerResult:
  """Compiles the JsonNetlist to a KiCad netlist, returning the KiCad netlist along with a list of model
  validation errors (if any)."""
  code = f"""\
from PolymorphicBlocks.edg import *

"""

  hdl = tohdl_netlist(netweaver_netlist)
  code += hdl

  code += """

compiled = ScalaCompiler.compile(MyModule, ignore_errors=True)
compiled.append_values(RefdesRefinementPass().run(compiled))
"""

  exec_env = {}
  exec(code, exec_env)

  compiled = cast(core.ScalaCompilerInterface.CompiledDesign, exec_env['compiled'])

  from PolymorphicBlocks.edg.electronics_model.NetlistGenerator import NetlistTransform
  from PolymorphicBlocks.edg.electronics_model.footprint import generate_netlist
  from PolymorphicBlocks.edg.electronics_model.BomBackend import GenerateBom
  from PolymorphicBlocks.edg import SvgPcbTemplateBlock, SvgPcbBackend

  netlist = NetlistTransform(compiled).run()
  kicad_netlist = generate_netlist(netlist, True)
  bom = GenerateBom().run(compiled)[0][1]

  # generate structured netlist
  nets_obj = [ResultNet(
    name=net.name,
    pads=[[SvgPcbTemplateBlock._svgpcb_pathname_to_svgpcb(pin.block_path), pin.pin_name]
          for pin in net.pins])
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
  svgpcb_result = SvgPcbBackend()._generate(compiled, netlist)

  errors = []
  for error in compiled.errors:
    # suppress some manufacturability warnings
    if error.name == 'required basic part':
      continue

    errors.append(CompilerError(
      path=edgir.local_path_to_str_list(error.path),
      kind=error.kind,
      name=error.name,
      details=error.details
    ))

  return CompilerResult(
    edgHdl=hdl,
    netlist=nets_obj,
    kicadNetlist=cast(str, kicad_netlist),
    kicadFootprints=all_footprints,
    svgpcbFunctions=svgpcb_result.functions,
    svgpcbInstantiations=svgpcb_result.instantiations,
    bom=bom,
    errors=errors
  )
