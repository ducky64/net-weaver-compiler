import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


class DiscreteRp2040TestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/DiscreteRp2040.json")) as f:
      netlist_data = f.read()
      netlist = JsonNetlist.model_validate_json(netlist_data)

    hdl = tohdl_netlist(netlist)
    result = compile_netlist(netlist)  # just check it doesn't error out
    print(result.kicadNetlist)
    self.assertEqual(result.errors, [])
