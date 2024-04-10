import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self._QGZd05Ri = self.Block(UsbCReceptacle())
    self._n3w58oKp = self.Block(Ldl1117(output_voltage=(3.0, 3.6)))
    self._xQhDBnLi = self.Block(SwitchMatrix(nrows=3, ncols=2))
    self._UJOuhuHr = self.Block(Rp2040())

    self.connect(self._n3w58oKp.pwr_in, self._QGZd05Ri.pwr)
    self.connect(self._QGZd05Ri.gnd, self._UJOuhuHr.gnd, self._n3w58oKp.gnd)
    self.connect(self._n3w58oKp.pwr_out, self._UJOuhuHr.pwr)
    self.connect(self._xQhDBnLi.cols, self._UJOuhuHr.gpio.request_vector())
    self.connect(self._xQhDBnLi.rows, self._UJOuhuHr.gpio.request_vector())
"""

class KeyboardTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Keyboard.json")) as f:
      netlist_data = f.read()
      netlist = JsonNetlist.model_validate_json(netlist_data)

    hdl = tohdl_netlist(netlist)
    self.assertEqual(hdl, EXPECTED_HDL)

    result = compile_netlist(netlist)  # just check it doesn't error out
    self.assertEqual(result.errors, [])
