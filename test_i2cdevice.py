import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self.Xiao_Rp2040 = self.Block(Xiao_Rp2040())
    self.Hdc1080 = self.Block(Hdc1080())
    self.I2cPullup = self.Block(I2cPullup())

    self.connect(self.I2cPullup.i2c, self.Hdc1080.i2c, self.Xiao_Rp2040.i2c.request('i2c_12'))
    self.connect(self.Hdc1080.gnd, self.Xiao_Rp2040.gnd)
    self.connect(self.Hdc1080.pwr, self.Xiao_Rp2040.pwr_out, self.I2cPullup.pwr)
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
