import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self._Uxz6bvy1 = self.Block(Xiao_Rp2040())
    self._wtBTgiHw = self.Block(Hdc1080())
    self._Z6CrKBnO = self.Block(I2cPullup())

    self.connect(self._Z6CrKBnO.i2c, self._wtBTgiHw.i2c, self._Uxz6bvy1.i2c.request('i2c_12'))
    self.connect(self._wtBTgiHw.gnd, self._Uxz6bvy1.gnd_out)
    self.connect(self._wtBTgiHw.vdd, self._Uxz6bvy1.pwr_out, self._Z6CrKBnO.pwr)
"""


class I2cDeviceTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/I2cDevice.json")) as f:
      netlist_data = f.read()
      netlist = JsonNetlist.model_validate_json(netlist_data)

    hdl = tohdl_netlist(netlist)
    self.assertEqual(hdl, EXPECTED_HDL)

    result = compile_netlist(netlist)  # just check it doesn't error out
    self.assertEqual(result.errors, [])
