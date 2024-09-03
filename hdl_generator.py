from typing import Optional, List
from netweaver_interface import JsonNetlist, JsonLabel, JsonNode, JsonNodePort


class JsonNetlistValidationError(Exception):
  def __init__(self, path: list[str], desc: str):
    super().__init__(f"{'.'.join(path)}: {desc}")
    self.path = path
    self.desc = desc


def tohdl_connector(connector: JsonNode, connections: List[JsonNodePort]) -> str:
  pass


def tohdl_netlist(netlist: JsonNetlist) -> str:
  """Compiles the JsonNetlist to HDL, returning the HDL code."""
  connectors_code = f""""""

  # declare blocks
  block_code = ""
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
    block_code += f"    self.{node.data.name} = self.Block({block_class}({', '.join(args_elts)}))\n"

  labels_by_name: dict[str, list[JsonLabel]] = { }
  if netlist.labels:
    for id, label in netlist.labels.items():
      labels_by_name.setdefault(label.labelName, []).append(label)

  # generate labels first
  connections_code = ""
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
      if not port_port.name.isidentifier():
        raise JsonNetlistValidationError([], f"invalid port label {port_node.data.name}.{port_port.name}")
      if port_port.elementOf is not None:  # array request
        port_parent_port = port_node.data.ports[port_port.elementOf].name
        if not port_parent_port.isidentifier():
          raise JsonNetlistValidationError([], f"invalid port label {port_node.data.name}.{port_parent_port}")
        if is_array:
          port_hdls.append(f"self.{port_node.data.name}.{port_parent_port}.request_vector('{port_port.name}')")
        else:
          port_hdls.append(f"self.{port_node.data.name}.{port_parent_port}.request('{port_port.name}')")
      else:  # single port
        port_hdls.append(f"self.{port_node.data.name}.{port_port.name}")

    connections_code += f"    self.connect({', '.join(port_hdls)})\n"

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

  return f"""\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

{block_code}
{connections_code}"""
