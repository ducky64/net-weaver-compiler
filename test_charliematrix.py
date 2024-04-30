import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self.Xiao_Esp32c3 = self.Block(Xiao_Esp32c3())
    self.CharlieplexedLedMatrix = self.Block(CharlieplexedLedMatrix(nrows=2, ncols=3))

    self.connect(self.CharlieplexedLedMatrix.ios, self.Xiao_Esp32c3.gpio.request_vector('gpio_14'))
"""


class CharlieMatrixTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/CharlieMatrix.json")) as f:
      netlist_data = f.read()
      netlist = JsonNetlist.model_validate_json(netlist_data)

    hdl = tohdl_netlist(netlist)
    self.assertEqual(hdl, EXPECTED_HDL)

    result = compile_netlist(netlist)  # just check it doesn't error out
    self.assertEqual(result.errors, [])
