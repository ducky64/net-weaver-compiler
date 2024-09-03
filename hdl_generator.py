from typing import Optional, List, Tuple
from netweaver_interface import JsonNetlist, JsonLabel, JsonNode, JsonNodePort


class JsonNetlistValidationError(Exception):
  def __init__(self, path: list[str], desc: str):
    super().__init__(f"{'.'.join(path)}: {desc}")
    self.path = path
    self.desc = desc


class Connection:
  def __init__(self, name: str, ports: list[Tuple[JsonNode, JsonNodePort]], labels: list[JsonLabel]):
    self.name = name
    self.ports = ports
    self.labels = labels

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


def tohdl_connector(connector: JsonNode, port_connections: List[Tuple[int, Connection]]) -> Tuple[str, str]:
  """Compiles a JsonNode representing a connector to HDL, returning the block class name and block definition."""
  assert connector.data.type.isidentifier() and connector.data.name.isidentifier()
  classname = connector.data.type + "_" + connector.data.name

  port_types: dict[str, str] = {}
  for portidx, connection in port_connections:
    port_name = connector.data.ports[portidx].name
    if not port_name.isidentifier():
      raise JsonNetlistValidationError([connector.data.name, port_name], f"invalid port name")
    port_type = [port[1].type for port in connection.ports if port[0] is not connector]
    port_types[port_name] = ', '.join(port_type)

  connector_code = f"""\
class {classname}(Block):
  def __init__(self):
    super().__init__()
    # {port_types}
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
  block_code = []
  connectors_code = []
  for node_id, node in netlist.graph.nodes.items():
    if not node.data.name.isidentifier():
      raise JsonNetlistValidationError([node.data.name], f"invalid block name")
    block_class = node.data.type
    if not block_class.isidentifier():
      raise JsonNetlistValidationError([node.data.name], f"invalid block class {block_class}")

    if 'PassiveConnector' in node.data.superClasses:
      connector_connections = [(port.idx, connections_by_node_port[(node_id, port.idx)]) for port in node.data.ports
                     if (node_id, port.idx) in connections_by_node_port]
      block_class, block_def = tohdl_connector(node, connector_connections)
      connectors_code.append(block_def)

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
    block_code.append(f"self.{node.data.name} = self.Block({block_class}({', '.join(args_elts)}))")

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

    connections_code.append(f"self.connect({', '.join(port_hdls)})")

  # compose into top-level code
  newline = '\n'  # not allowed in f-strings
  return f"""\
{''.join(map(lambda c: c + newline + newline, connectors_code))}\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

{newline.join(map(lambda c: "    " + c, block_code))}

{newline.join(map(lambda c: "    " + c, connections_code))}
"""
