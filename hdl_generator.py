from typing import Optional, List, Tuple, Type, NamedTuple, Dict
from netweaver_interface import JsonNetlist, JsonLabel, JsonNode, JsonNodePort
from PolymorphicBlocks import edg


class JsonNetlistValidationError(Exception):
  def __init__(self, path: list[str], desc: str):
    super().__init__(f"{'.'.join(path)}: {desc}")
    self.path = path
    self.desc = desc


class Connection(NamedTuple):
  name: str
  ports: list[Tuple[JsonNode, JsonNodePort]]
  labels: list[JsonLabel]

  def is_array(self) -> bool:
    is_array: Optional[bool] = None
    for (containing_node, port) in self.ports:  # sweep through connected to determine if an array
      if port.elementOf is not None:
        continue  # ignored, request does not determine array-ness
      elif port.array:
        if is_array is False:
          raise JsonNetlistValidationError([], f"mixed array and non-array ports in connection {self.name}")
        is_array = True
      else:
        if is_array is True:
          raise JsonNetlistValidationError([], f"mixed array and non-array ports in label {self.name}")
        is_array = False
    return bool(is_array)


# connector port mapping - for each set of incoming port types, the connector port type
kConnectorTypeMap = [
  ({edg.VoltageSink}, edg.VoltageSource),
  ({edg.VoltageSource, edg.VoltageSink}, edg.VoltageSink),
  ({edg.DigitalSource, edg.DigitalSink, edg.DigitalBidir}, edg.DigitalBidir),
  ({edg.AnalogSink}, edg.AnalogSource),
  ({edg.AnalogSource, edg.AnalogSink}, edg.AnalogSink),
  ({edg.Ground, edg.GroundReference}, edg.Ground)
]
def get_connector_type(err_path: list[str], port_types: list[Type[edg.CircuitPort]]) -> Type[edg.CircuitPort]:
  """For a list of port types of incoming connections, return the (likely) port type that is connectable to them all,
  preferring required but not-connected ports, then any free port in the link."""
  # choose from kConnectorTypeMap where the port_types is a subset of the key AND overlap is not zero
  for incoming_ports, connector_type in kConnectorTypeMap:
    if incoming_ports.intersection(port_types) and incoming_ports.issuperset(port_types):
      return connector_type
  raise JsonNetlistValidationError(err_path, f"no connector type for {port_types}")


def tohdl_connector(connector: JsonNode, connector_class_name: str, connector_args: str,
                    port_connections: List[Tuple[int, Connection]]) -> Tuple[str, str]:
  """Compiles a JsonNode representing a connector to HDL, returning the block class name and block definition."""
  assert connector.data.type.isidentifier() and connector.data.name.isidentifier()
  classname = connector.data.type + "_" + connector.data.name
  port_decls = []

  for portidx, connection in port_connections:
    port_name = connector.data.ports[portidx].name
    if not port_name.isidentifier() or not port_name.startswith('port_'):
      raise JsonNetlistValidationError([connector.data.name, port_name], f"invalid port name")
    port_num = int(port_name[5:]) + 1

    err_path = [connector.data.name, port_name]

    # aggregate incoming connection by types
    connection_ports_str = [port[1].type for port in connection.ports if port[0] is not connector]
    connection_port_types = []
    for connection_port_str in connection_ports_str:
      if not hasattr(edg, connection_port_str):
        raise JsonNetlistValidationError(err_path, f"invalid port type {connection_port_str}")
      port_class = getattr(edg, connection_port_str)
      if connection.is_array():
        raise JsonNetlistValidationError(err_path, f"can't connect array to connectors")
      connection_port_types.append(port_class)

    connector_port_type = get_connector_type(err_path, connection_port_types).__name__
    port_decls.append(f"self.{port_name} = self.Export(self._conn.pins.request('{port_num}').adapt_to({connector_port_type}()), optional=True)")

  # globals['__builtins__'] is added since exec top-level classes appear in __builtin__ scope,
  # and modules and top-level in exec() do not share the same scope
  newline = '\n'  # not allowed in f-strings
  connector_code = f"""\
class {classname}(Block):
  def __init__(self):
    super().__init__()
    self._conn = self.Block({connector_class_name}({connector_args}))
{newline.join(map(lambda c: "    " + c, port_decls))}

globals()['__builtins__']['{classname}'] = {classname}
"""
  return classname, connector_code


def tohdl_netlist(netlist: JsonNetlist) -> str:
  """Compiles the JsonNetlist to HDL, returning the HDL code."""
  # aggregate connections
  labels_by_name: dict[str, list[JsonLabel]] = {}
  for id, label in netlist.labels.items():
    labels_by_name.setdefault(label.labelName, []).append(label)

  connections_by_name: dict[str, Connection] = {}
  connections_by_node_port: dict[Tuple[str, int], Connection] = {}
  for name, labels in labels_by_name.items():
    ports = []
    for label in labels:
      containing_node = netlist.graph.nodes[label.nodeId]
      port = containing_node.data.ports[label.portIdx]
      ports.append((containing_node, port))

    connection = Connection(name, ports, labels)
    connections_by_name[name] = connection
    for label in labels:
      assert (label.nodeId, label.portIdx) not in connections_by_node_port, "duplicate label"
      connections_by_node_port[(label.nodeId, label.portIdx)] = connection

  additional_connections: Dict[str, List[str]] = {}  # connection name, [hdl]
  additional_blocks: List[Tuple[str, str]] = []  # block name, block HDL

  # infer needed parts, just I2C pullup for now
  for name, connection in connections_by_name.items():
    # i2c pull power is connected to the first connected power port of the controller
    I2C_IMPLICIT_CONTROLLER_POWER_PORTS = ['pwr_out', 'pwr']

    connection_is_i2c = False
    i2c_has_pullup = False
    controller_node = None
    for node, port in connection.ports:
      if port.type.endswith('I2cController') or port.type.endswith('I2cTarget'):
        connection_is_i2c = True
      if port.type.endswith('I2cController') and controller_node is None:  # take the first controller
        controller_node = node
      if node.data.type.endswith('I2cPullup'):
        i2c_has_pullup = True
    if connection_is_i2c and not i2c_has_pullup and controller_node is not None:
      # determine power node, from controller
      controller_power_net = None
      controller_port_name_to_idx = {port.name: port.idx for port in controller_node.data.ports}
      for candidate_port_name in I2C_IMPLICIT_CONTROLLER_POWER_PORTS:
        controller_port_idx = controller_port_name_to_idx.get(candidate_port_name, None)
        if (controller_node.id, controller_port_idx) in connections_by_node_port:
          controller_power_net = connections_by_node_port[(controller_node.id, controller_port_idx)].name
      if controller_power_net is not None:
        pullup_name = f'_implicit_i2c_pullup_{name}'
        additional_blocks.append((pullup_name, 'I2cPullup()'))
        additional_connections.setdefault(controller_power_net, []).append(f'{pullup_name}.pwr')
        additional_connections.setdefault(name, []).append(f'{pullup_name}.i2c')

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

  # declare blocks
  blocks_code = []
  connectors_code = []
  for node_id, node in netlist.graph.nodes.items():
    if not node.data.name.isidentifier():
      raise JsonNetlistValidationError([node.data.name], f"invalid block name")
    block_class = node.data.type
    if not block_class.isidentifier():
      raise JsonNetlistValidationError([node.data.name], f"invalid block class {block_class}")

    # fill in block args
    args_elts = []
    for arg_param in node.data.argParams:
      if arg_param.default_value != arg_param.value and arg_param.value:
        # parse and sanitize the value
        if arg_param.type == 'int':
          try:
            arg_value = str(int(arg_param.value))
          except ValueError:
            raise JsonNetlistValidationError([node.data.name, arg_param], f"invalid non-int value {arg_param.value}")
        elif arg_param.type == 'float':
          try:
            arg_value = str(float(arg_param.value))
          except ValueError:
            raise JsonNetlistValidationError([node.data.name, arg_param], f"invalid non-float value {arg_param.value}")
        elif arg_param.type == 'range':
          if not isinstance(arg_param.value, list) and len(arg_param.value) == 2:
            raise JsonNetlistValidationError([node.data.name, arg_param], f"invalid value {arg_param.value}")
          try:
            arg_value = f"({float(arg_param.value[0])}, {float(arg_param.value[1])})"
          except ValueError:
            raise JsonNetlistValidationError([node.data.name, arg_param], f"invalid range-int value {arg_param.value}")
        elif arg_param.type == 'string':
          raise JsonNetlistValidationError([node.data.name, arg_param.name], f"TODO: strings unsupported")
        else:
          raise JsonNetlistValidationError([node.data.name, arg_param.name], f"unknown arg-param type {arg_param.type}")

        args_elts.append(f"{arg_param.name}={arg_value}")
    block_args_code = ', '.join(args_elts)

    if 'PassiveConnector' in node.data.superClasses:  # PassiveConnector args are handled in the connector block
      connector_connections = [(port.idx, connections_by_node_port[(node_id, port.idx)]) for port in node.data.ports
                               if (node_id, port.idx) in connections_by_node_port]
      block_class, block_def = tohdl_connector(node, block_class, block_args_code, connector_connections)
      connectors_code.append(block_def)
      block_code = f"self.{node.data.name} = self.Block({block_class}())"
    else:
      block_code = f"self.{node.data.name} = self.Block({block_class}({block_args_code}))"

    blocks_code.append(block_code)

  # generate additional blocks
  for name, block_hdl in additional_blocks:
    blocks_code.append(f"self.{name} = self.Block({block_hdl})")

  # generate connect statements
  connections_code = []
  for name, connection in connections_by_name.items():
    port_hdls = []

    for (containing_node, port) in connection.ports:
      if not port.name.isidentifier():
        raise JsonNetlistValidationError([], f"invalid port label {containing_node.data.name}.{port.name}")
      if port.elementOf is not None:  # array request
        port_parent_port = containing_node.data.ports[port.elementOf].name
        if not port_parent_port.isidentifier():
          raise JsonNetlistValidationError([], f"invalid port label {containing_node.data.name}.{port_parent_port}")
        if connection.is_array():
          port_hdls.append(f"self.{containing_node.data.name}.{port_parent_port}.request_vector('{port.name}')")
        else:
          port_hdls.append(f"self.{containing_node.data.name}.{port_parent_port}.request('{port.name}')")
      else:  # single port
        port_hdls.append(f"self.{containing_node.data.name}.{port.name}")

    for connect_hdl in additional_connections.get(name, []):
      port_hdls.append(f"self.{connect_hdl}")

    connections_code.append(f"self.connect({', '.join(port_hdls)})")

  # compose into top-level code
  newline = '\n'  # not allowed in f-strings
  return f"""\
{''.join(map(lambda c: c + newline + newline, connectors_code))}\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

{newline.join(map(lambda c: "    " + c, blocks_code))}

{newline.join(map(lambda c: "    " + c, connections_code))}
"""
