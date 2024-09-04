import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


EXPECTED_HDL = """\
class PinHeader254Vertical_PinHeader254Vertical(Block):
  def __init__(self):
    super().__init__()
    self.port_0 = self.Port(DigitalBidir())
    self.port_1 = self.Port(Ground())


class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self.PinHeader254Vertical = self.Block(PinHeader254Vertical_PinHeader254Vertical())
    self.IndicatorLed = self.Block(IndicatorLed())

    self.connect(self.IndicatorLed.signal, self.PinHeader254Vertical.port_0)
    self.connect(self.IndicatorLed.gnd, self.PinHeader254Vertical.port_1)
"""


class ConnectorLedTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/ConnectorLed.json")) as f:
      netlist_data = f.read()
      netlist = JsonNetlist.model_validate_json(netlist_data)

    hdl = tohdl_netlist(netlist)
    self.assertEqual(hdl, EXPECTED_HDL)

    result = compile_netlist(netlist)  # just check it doesn't error out
    self.assertEqual(result.errors, [])
