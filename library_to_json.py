# Simple tool that scans for libraries and dumps the whole thing to a proto file
from itertools import chain
from typing import Optional, List, Any, Union, Tuple
import inspect
from pydantic import BaseModel, RootModel

# needed to enable EDG as a submodule instead of requiring it to be installed as a system package
import sys
import os.path
sys.path.append(os.path.join(os.path.dirname(__file__), 'PolymorphicBlocks'))

from edg_hdl_server.__main__ import LibraryElementIndexer
import edg_core
import edgir
import edg
from edg_core.Builder import builder


def simpleName(target: edgir.ref_pb2.LibraryPath) -> str:
  return target.target.name.split('.')[-1]


class PortJsonDict(BaseModel):
  name: str  # name in parent
  type: str  # type of self; if array refers to the array element type
  is_array: bool
  hint_position: Optional[str]  # left | right | up | down | '' (empty)
  hint_signal_direction: Optional[str]  # source | sink | bidir | passive | None
  hint_array_direction: Optional[str]  # source | sink | bidir | None (if not is_array)
  required: bool


def port_to_dir(name: str, target: edgir.ref_pb2.LibraryPath) -> Optional[str]:
  simpleTarget = simpleName(target)

  if simpleTarget == 'Passive':
    return None

  elif simpleTarget == 'VoltageSource':
    return 'right'
  elif simpleTarget == 'VoltageSink':
    if name == 'gnd':
      return 'down'
    else:
      return 'up'

  elif simpleTarget == 'DigitalSource':
    return 'right'
  elif simpleTarget == 'DigitalSingleSource':
    return 'right'
  elif simpleTarget == 'DigitalSink':
    return 'left'
  elif simpleTarget == 'DigitalBidir':
    return None

  elif simpleTarget == 'AnalogSource':
    return 'right'
  elif simpleTarget == 'AnalogSink':
    return 'left'
  elif simpleTarget == 'AnalogBidir':
    return None

  elif simpleTarget == 'I2cController':
    return 'right'
  elif simpleTarget == 'I2cPullupPort':
    return 'down'
  elif simpleTarget == 'I2cTarget':
    return 'left'

  elif simpleTarget == 'SpiController':
    return 'right'
  elif simpleTarget == 'SpiPeripheral':
    return 'left'

  elif simpleTarget == 'UsbHostPort':
    return 'right'
  elif simpleTarget == 'UsbDevicePort':
    return 'left'
  elif simpleTarget == 'UsbPassivePort':
    return 'left'

  else:
    print(f"unknown direction {simpleTarget}")
    return None


def port_to_signal_dir(pair: edgir.elem_pb2.NamedPortLike) -> Optional[str]:
  if pair.value.HasField('lib_elem'):
    simpleTarget = simpleName(pair.value.lib_elem)
  elif pair.value.HasField('array'):
    simpleTarget = simpleName(pair.value.array.self_class)

  if simpleTarget == 'Passive':
    return 'passive'

  elif simpleTarget == 'VoltageSource':
    return 'source'
  elif simpleTarget == 'VoltageSink':
    return 'sink'

  elif simpleTarget == 'DigitalSource':
    return 'source'
  elif simpleTarget == 'DigitalSingleSource':
    return 'source'
  elif simpleTarget == 'DigitalSink':
    return 'sink'
  elif simpleTarget == 'DigitalBidir':
    return 'bidir'

  elif simpleTarget == 'AnalogSource':
    return 'source'
  elif simpleTarget == 'AnalogSink':
    return 'sink'
  elif simpleTarget == 'AnalogBidir':
    return 'bidir'

  elif simpleTarget == 'I2cController':
    return 'source'
  elif simpleTarget == 'I2cPullupPort':
    return 'passive'
  elif simpleTarget == 'I2cTarget':
    return 'sink'

  elif simpleTarget == 'SpiController':
    return 'source'
  elif simpleTarget == 'SpiPeripheral':
    return 'sink'

  elif simpleTarget == 'UartPort':
    return 'bidir'

  elif simpleTarget == 'UsbHostPort':
    return 'source'
  elif simpleTarget == 'UsbDevicePort':
    return 'sink'
  elif simpleTarget == 'UsbPassivePort':
    return 'passive'

  elif simpleTarget == 'UsbCcPort':
    return 'bidir'

  elif simpleTarget == 'CanDiffPort':
    return 'bidir'
  elif simpleTarget == 'CanControllerPort':
    return 'source'
  elif simpleTarget == 'CanTransceiverPort':
    return 'sink'
  elif simpleTarget == 'CanPassivePort':
    return 'passive'

  elif simpleTarget == 'SwdHostPort':
    return 'source'
  elif simpleTarget == 'SwdTargetPort':
    return 'sink'
  elif simpleTarget == 'SwdPullPort':
    return 'passive'

  elif simpleTarget == 'I2sController':
    return 'source'
  elif simpleTarget == 'I2sTargetReceiver':
    return 'sink'

  elif simpleTarget == 'TouchDriver':
    return 'sink'
  elif simpleTarget == 'TouchPadPort':
    return 'source'

  elif simpleTarget == 'CrystalDriver':
    return 'source'
  elif simpleTarget == 'CrystalPort':
    return 'sink'

  elif simpleTarget == 'Dvp8Host':
    return 'sink'
  elif simpleTarget == 'Dvp8Camera':
    return 'source'

  elif simpleTarget == 'SpeakerDriverPort':
    return 'source'
  elif simpleTarget == 'SpeakerPort':
    return 'sink'

  elif simpleTarget == 'JacdacDataPort':
    return 'bidir'
  elif simpleTarget == 'JacdacPassivePort':
    return 'passive'

  else:
    raise ValueError(f"unknown direction {simpleTarget} in {pair.name}")


def pb_to_port(container: edgir.BlockLikeTypes, pair: edgir.elem_pb2.NamedPortLike):
  constrs = [constraint_pair.value for constraint_pair in container.constraints]
  required = bool([constr for constr in constrs
                  if constr.HasField('ref') and len(constr.ref.steps) == 2 and constr.ref.steps[0].name == pair.name
                   and constr.ref.steps[1].HasField('reserved_param')
                   and constr.ref.steps[1].reserved_param == edgir.IS_CONNECTED])

  if pair.value.HasField('lib_elem'):
    return PortJsonDict(
      name=pair.name,
      type=simpleName(pair.value.lib_elem),
      is_array=False,
      hint_position=port_to_dir(pair.name, pair.value.lib_elem),
      hint_signal_direction=port_to_signal_dir(pair),
      hint_array_direction=None,
      required=required
    )
  elif pair.value.HasField('array'):
    # TODO: array directionality should be a IR construct exposed through the frontend
    # this is a temporary hack to make things work
    all_superclasses = list(chain(container.superclasses, container.super_superclasses, [container.self_class]))
    if any(['IoController' in superclass.target.name for superclass in all_superclasses]):
      hint_array_direction = 'sink'
    else:
      hint_array_direction = 'source'

    return PortJsonDict(
      name=pair.name,
      type=simpleName(pair.value.array.self_class),
      is_array=True,
      hint_position=port_to_dir(pair.name, pair.value.array.self_class),
      hint_signal_direction=port_to_signal_dir(pair),
      hint_array_direction=hint_array_direction,
      required=required
    )
  else:
    raise ValueError(f"unknown pair value type ${pair.value}")


ParamValueTypes = Union[int, float, bool, Tuple[float, float], str, List[Any]]
class ParamJsonDict(BaseModel):
  name: str
  type: str  # int | float | bool | range | string | array
  default_value: Optional[ParamValueTypes]  # in Python HDL


class BlockJsonDict(BaseModel):
  name: str  # name in superblock - empty for libraries
  type: str  # type of self
  superClasses: list[str] = []  # superclasses of self
  ports: list[PortJsonDict]
  argParams: list[ParamJsonDict] = []
  is_abstract: bool = False
  docstring: Optional[str] = ""  # docstring for the block, if any


class TypeHierarchyNode(BaseModel):
  name: str
  children: list['TypeHierarchyNode']


class LibraryJson(BaseModel):
  blocks: list[BlockJsonDict]
  links: list[BlockJsonDict]
  typeHierarchyTree: TypeHierarchyNode


OUTPUT_FILE = "library.json"

if __name__ == '__main__':
  library = LibraryElementIndexer()

  pb = edgir.Library()

  all_blocks = []
  all_links = []

  subclasses: dict[str, list[str]] = {}  # superclass -> [subclasses]

  count = 0
  for cls in library.index_module(edg):
    # from edg import IndicatorLed
    # cls = IndicatorLed

    obj = cls()
    name = cls.__name__
    if isinstance(obj, edg_core.Block):
      print(f"Elaborating block {name}")
      block_proto = builder.elaborate_toplevel(obj)

      # inspect into the args to get ArgParams
      argParams = []
      sig = inspect.signature(cls.__init__)
      for param_name, param in list(sig.parameters.items())[1:]:  # drop 'self'
        # TODO NEED TO RECURSE FOR *ARGS / **KWARGS
        if param.kind in [inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD,
                          inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.POSITIONAL_ONLY,
                          inspect.Parameter.KEYWORD_ONLY]:
          param_pb = edgir.pair_get_opt(block_proto.params, param_name)
          default_value: Optional[ParamValueTypes] = None
          if param_pb is not None:
            if param.default is inspect.Parameter.empty:
              default_value = None
            elif isinstance(param.default, (int, float, str, bool)):
              default_value = param.default
            elif isinstance(param.default, tuple) and len(param.default) == 2 and \
                isinstance(param.default[0], (int, float)) and isinstance(param.default[1], (int, float)):
              default_value = str(param.default)
            elif isinstance(param.default, edg_core.Range):
              range = param.default
              default_value = (range.lower, range.upper)
            elif isinstance(param.default, edg_core.RangeExpr):
              if isinstance(param.default.binding, edg_core.ConstraintExpr.RangeLiteralBinding):
                range = param.default.binding.value
                default_value = (range.lower, range.upper)
              else:
                print(f"{name}.{param_name}: bad binding {param.default.binding}")
            elif isinstance(param.default, edg_core.FloatExpr):
              if isinstance(param.default.binding, edg_core.ConstraintExpr.FloatLiteralBinding):
                default_value = param.default.binding.value
              else:
                print(f"{name}.{param_name}: bad binding {param.default.binding}")
            elif isinstance(param.default, edg_core.BoolExpr):
              if isinstance(param.default.binding, edg_core.ConstraintExpr.BoolLiteralBinding):
                default_value = param.default.binding.value
              else:
                print(f"{name}.{param_name}: bad binding {param.default.binding}")
            elif isinstance(param.default, edg_core.StringExpr):
              if isinstance(param.default.binding, edg_core.ConstraintExpr.StringLiteralBinding):
                default_value = param.default.binding.value
              else:
                print(f"{name}.{param_name}: bad binding {param.default.binding}")
            else:
              print(f"{name}.{param_name}: failed to parse default {param.default}")

            if param_pb.HasField('floating'):
              param_type = 'float'
            elif param_pb.HasField('integer'):
              param_type = 'int'
            elif param_pb.HasField('boolean'):
              param_type = 'bool'
            elif param_pb.HasField('text'):
              param_type = 'str'
            elif param_pb.HasField('range'):
              param_type = 'range'
            elif param_pb.HasField('array'):
              param_type = 'array'
            else:
              raise ValueError(f"{name}.{param_name} unknown param type {param_pb}")

            argParams.append(ParamJsonDict(
              name=param_name,
              type=param_type,
              default_value=default_value
            ))
          else:
            print(f"missing param {param_name} in {name}")

      block_dict = BlockJsonDict(
        name="",  # empty for libraries
        type=simpleName(block_proto.self_class),
        superClasses=[simpleName(superclass) for superclass in block_proto.superclasses],
        ports=[pb_to_port(block_proto, pair) for pair in block_proto.ports],
        argParams=argParams,
        is_abstract=block_proto.is_abstract,
        docstring=inspect.getdoc(cls)
      )
      all_blocks.append(block_dict)

      for superclass in block_proto.superclasses:
        subclasses.setdefault(simpleName(superclass), []).append(simpleName(block_proto.self_class))
      if not block_proto.superclasses:  # no superclasses, add to root
        subclasses.setdefault('', []).append(simpleName(block_proto.self_class))
    elif isinstance(obj, edg_core.Link):
      link_proto = builder.elaborate_toplevel(obj)
      pb.root.members[name].link.CopyFrom(link_proto)

      link_dict = BlockJsonDict(
        name="",  # empty for libraries
        type=simpleName(link_proto.self_class),
        ports=[pb_to_port(link_proto, pair) for pair in link_proto.ports],
        docstring=inspect.getdoc(cls)
      )
      all_links.append(link_dict)

    elif isinstance(obj, edg_core.Bundle):  # TODO: note Bundle extends Port, so this must come first
      # pb.root.members[name].bundle.CopyFrom(obj._def_to_proto())
      pass
    elif isinstance(obj, edg_core.Port):
      # pb.root.members[name].port.CopyFrom(obj._def_to_proto())
      pass

    count += 1

  hierarchy_seen: set[str] = set()

  def sort_hierarchy_list(in_list: list[TypeHierarchyNode]) -> list[TypeHierarchyNode]:
    return list(sorted(in_list, key=lambda elt: elt.name))

  def generate_hierarchy_node(node_name: str) -> TypeHierarchyNode:
    hierarchy_seen.add(node_name)
    return TypeHierarchyNode(
      name=node_name,
      children=sort_hierarchy_list(
        [generate_hierarchy_node(child) for child in subclasses.get(node_name, [])]
      )
    )

  root_hierarchy_elts = sort_hierarchy_list(
    [generate_hierarchy_node(child) for child in subclasses.get('', [])]
  )
  unseen = subclasses.keys() - hierarchy_seen - {'', 'Block'}
  print(f"Missing from type hierarchy: {unseen}")

  library_json = LibraryJson(
    blocks=all_blocks,
    links=all_links,
    typeHierarchyTree=TypeHierarchyNode(name='', children=root_hierarchy_elts)
  )

  print(f"Writing {count} classes to {OUTPUT_FILE}")

  with open(OUTPUT_FILE, 'w') as file:
    file.write(library_json.model_dump_json(indent=2))
