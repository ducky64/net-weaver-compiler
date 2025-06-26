# Simple tool that scans for libraries and dumps the whole thing to a proto file
import inspect
from itertools import chain
from typing import Optional, List, Any, Union, Tuple, cast

from pydantic import BaseModel

from PolymorphicBlocks import edg
from PolymorphicBlocks.edg import *
from PolymorphicBlocks.edg import core, edgir
from PolymorphicBlocks.edg.core.Binding import FloatLiteralBinding, IntLiteralBinding, \
  StringLiteralBinding, BoolLiteralBinding, RangeLiteralBinding, ArrayLiteralBinding, ArrayBinding
from PolymorphicBlocks.edg.core.Builder import builder
from PolymorphicBlocks.edg.electronics_model.KiCadSchematicParser import test_cast
from PolymorphicBlocks.edg.hdl_server.__main__ import LibraryElementIndexer


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
  docstring: Optional[str] = ""  # docstring for the port, if any


def port_to_dir(name: str, target: edgir.ref_pb2.LibraryPath) -> Optional[str]:
  simpleTarget = simpleName(target)

  if simpleTarget == 'Passive':
    return None
  elif simpleTarget == 'Ground':
    return 'down'
  elif simpleTarget == 'GroundReference':
    return 'down'

  elif simpleTarget == 'VoltageSource':
    return 'right'
  elif simpleTarget == 'VoltageSink':
    if name == 'gnd':
      return 'down'
    else:
      return 'up'

  elif simpleTarget == 'DigitalSource':
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

  elif simpleTarget == 'UartPort':
    return None

  elif simpleTarget == 'UsbHostPort':
    return 'right'
  elif simpleTarget == 'UsbDevicePort':
    return 'left'
  elif simpleTarget == 'UsbPassivePort':
    return 'left'

  elif simpleTarget == 'UsbCcPort':
    return None

  elif simpleTarget == 'CanDiffPort':
    return None
  elif simpleTarget == 'CanControllerPort':
    return 'right'
  elif simpleTarget == 'CanTransceiverPort':
    return 'left'
  elif simpleTarget == 'CanPassivePort':
    return None

  elif simpleTarget == 'I2sController':
    return 'right'
  elif simpleTarget == 'I2sTargetReceiver':
    return 'left'

  else:
    print(f"unknown direction {simpleTarget}")
    return None


def port_to_signal_dir(pair: edgir.elem_pb2.NamedPortLike) -> Optional[str]:
  if pair.value.HasField('lib_elem'):
    simpleTarget = simpleName(pair.value.lib_elem)
  elif pair.value.HasField('array'):
    simpleTarget = simpleName(pair.value.array.self_class)
  else:
    raise ValueError(f"unknown port type {pair.value}")

  if simpleTarget == 'Passive':
    return 'passive'
  elif simpleTarget == 'Ground':
    return 'bidir'
  elif simpleTarget == 'GroundReference':
    return 'source'

  elif simpleTarget == 'VoltageSource':
    return 'source'
  elif simpleTarget == 'VoltageSink':
    return 'sink'

  elif simpleTarget == 'DigitalSource':
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


def pb_to_port(instance: core.BaseBlock, container: edgir.BlockLikeTypes, pair: edgir.elem_pb2.NamedPortLike):
  constrs = [constraint_pair.value for constraint_pair in container.constraints]
  required = bool([constr for constr in constrs
                  if constr.HasField('ref') and len(constr.ref.steps) == 2 and constr.ref.steps[0].name == pair.name
                   and constr.ref.steps[1].HasField('reserved_param')
                   and constr.ref.steps[1].reserved_param == edgir.IS_CONNECTED])

  doc = None
  if hasattr(instance, pair.name) and getattr(instance, pair.name) in instance._port_docs:
    doc = instance._port_docs[getattr(instance, pair.name)]

  if pair.value.HasField('lib_elem'):
    return PortJsonDict(
      name=pair.name,
      type=simpleName(pair.value.lib_elem),
      is_array=False,
      hint_position=port_to_dir(pair.name, pair.value.lib_elem),
      hint_signal_direction=port_to_signal_dir(pair),
      hint_array_direction=None,
      required=required,
      docstring=doc
    )
  elif pair.value.HasField('array'):
    # TODO: array directionality should be a IR construct exposed through the frontend
    # this is a temporary hack to make things work
    all_superclasses = list(chain(container.superclasses, container.super_superclasses, [container.self_class]))
    # note superclass.target.name contains namespaces so test needs to be generic
    if any([('IoController' in superclass.target.name or 'PassiveConnector' in superclass.target.name)
            for superclass in all_superclasses]):
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
      required=required,
      docstring=doc
    )
  else:
    raise ValueError(f"unknown pair value type ${pair.value}")


ParamValueTypes = Union[int, float, bool, Tuple[float, float], str, List[Any]]
class ParamJsonDict(BaseModel):
  name: str
  type: str  # int | float | bool | range | string | array
  default_value: Optional[ParamValueTypes]  # in Python HDL
  docstring: Optional[str] = ""  # docstring for the port, if any


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


OUTPUT_FILE = "resources/library.json"

if __name__ == '__main__':
  library = LibraryElementIndexer()

  pb = edgir.Library()

  all_blocks = []
  all_links = []

  subclasses: dict[str, list[str]] = {}  # superclass -> [subclasses]
  excluded_classes: list[Block] = []  # list of excluded classes

  def is_excluded_class(block: Block) -> bool:
    if isinstance(block, BlockInterfaceMixin) and block._is_mixin():
      return True
    if isinstance(block, InternalBlock) and not isinstance(block, PassiveConnector):
      return True
    if block.__class__ is BaseIoController:  # manual exclusions
      return True
    return False

  count = 0
  for cls in library.index_module(edg):
    instance = cls()
    name = cls.__name__
    if isinstance(instance, Block):
      if is_excluded_class(instance):
        excluded_classes.append(instance)
        continue  # skip

      print(f"Elaborating block {name}")
      block_proto = builder.elaborate_toplevel(instance)

      # get arg-params from _init_params_value
      argParams = []
      for param_name, (param, param_value) in instance._init_params_value.items():
        default_value: Optional[ParamValueTypes] = None
        if isinstance(param, FloatExpr):
          param_type = 'float'
          if param_value is not None:
            default_value = test_cast(cast(ConstraintExpr, param_value).binding, FloatLiteralBinding).value
        elif isinstance(param, IntExpr):
          param_type = 'int'
          if param_value is not None:
            default_value = test_cast(cast(ConstraintExpr, param_value).binding, IntLiteralBinding).value
        elif isinstance(param, BoolExpr):
          param_type = 'bool'
          if param_value is not None:
            default_value = test_cast(cast(ConstraintExpr, param_value).binding, BoolLiteralBinding).value
        elif isinstance(param, StringExpr):
          param_type = 'str'
          if param_value is not None:
            default_value = test_cast(cast(ConstraintExpr, param_value).binding, StringLiteralBinding).value
        elif isinstance(param, RangeExpr):
          param_type = 'range'
          if param_value is not None:
            value_range = test_cast(cast(ConstraintExpr, param_value).binding, RangeLiteralBinding).value
            default_value = (value_range.lower, value_range.upper)
        elif isinstance(param, (ArrayIntExpr, ArrayBoolExpr, ArrayFloatExpr, ArrayStringExpr)):
          param_type = 'array'
          if param_value is not None:
            binding = cast(ConstraintExpr, param_value).binding
            if isinstance(binding, ArrayBinding):
              assert binding.values == []  # TODO support array literals with values
            elif isinstance(binding, ArrayLiteralBinding):
              assert binding.values == []
            else:
              raise TypeError()
            default_value = []
        else:
          raise ValueError(f"{name}.{param_name} unknown param type {type(param)}")

        doc = None
        if hasattr(instance, param_name) and getattr(instance, param_name) in instance._param_docs:
          doc = instance._param_docs[getattr(instance, param_name)]

        argParams.append(ParamJsonDict(
          name=param_name,
          type=param_type,
          default_value=default_value,
          docstring=doc
        ))

      block_docstring = None
      if cls.__doc__ is not None:
        block_docstring = inspect.cleandoc(cls.__doc__)

      block_dict = BlockJsonDict(
        name="",  # empty for libraries
        type=simpleName(block_proto.self_class),
        superClasses=[simpleName(superclass) for superclass in block_proto.superclasses]
                     + [simpleName(superclass) for superclass in block_proto.super_superclasses],
        ports=[pb_to_port(instance, block_proto, pair) for pair in block_proto.ports],
        argParams=argParams,
        is_abstract=block_proto.is_abstract,
        docstring=block_docstring
      )
      all_blocks.append(block_dict)

      for superclass in block_proto.superclasses:
        subclasses.setdefault(simpleName(superclass), []).append(simpleName(block_proto.self_class))
      if not block_proto.superclasses:  # no superclasses, add to root
        subclasses.setdefault('', []).append(simpleName(block_proto.self_class))
    elif isinstance(instance, Link):
      link_proto = builder.elaborate_toplevel(instance)
      pb.root.members[name].link.CopyFrom(link_proto)

      link_dict = BlockJsonDict(
        name="",  # empty for libraries
        type=simpleName(link_proto.self_class),
        ports=[pb_to_port(instance, link_proto, pair) for pair in link_proto.ports],
        docstring=inspect.getdoc(cls)
      )
      all_links.append(link_dict)

    elif isinstance(instance, Bundle):  # TODO: note Bundle extends Port, so this must come first
      # pb.root.members[name].bundle.CopyFrom(obj._def_to_proto())
      pass
    elif isinstance(instance, Port):
      # pb.root.members[name].port.CopyFrom(obj._def_to_proto())
      pass

    count += 1

  excluded_class_simplenames = [simpleName(edgir.libpath(block._get_def_name())) for block in excluded_classes]
  for block in all_blocks:
    block.superClasses = [superclass for superclass in block.superClasses
                          if superclass not in excluded_class_simplenames]

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

  subclasses = {name: subclasses_list for name, subclasses_list in subclasses.items()
                if name not in excluded_class_simplenames}
  root_hierarchy_elts = sort_hierarchy_list(
    [generate_hierarchy_node(child) for child in subclasses.get('', [])]
  )
  unseen = subclasses.keys() - hierarchy_seen - {'', 'Block'}
  print(f"Missing from type hierarchy: {unseen}")

  library_json = LibraryJson(
    blocks=sorted(all_blocks, key=lambda block: block.type),
    links=sorted(all_links, key=lambda link: link.type),
    typeHierarchyTree=TypeHierarchyNode(name='', children=root_hierarchy_elts)
  )

  print(f"Writing {count} classes to {OUTPUT_FILE}")

  with open(OUTPUT_FILE, 'w') as file:
    file.write(library_json.model_dump_json(indent=2))
