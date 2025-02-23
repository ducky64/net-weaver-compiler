import unittest
import os.path

from netlist_compiler import tohdl_netlist, compile_netlist, JsonNetlist


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self.Esp32_Wroom_32 = self.Block(Esp32_Wroom_32())
    self.UsbCReceptacle = self.Block(UsbCReceptacle())
    self.Ldl1117 = self.Block(Ldl1117(output_voltage=(3.135, 3.465)))
    self.Hdc1080 = self.Block(Hdc1080())
    self.Bme680 = self.Block(Bme680())
    self.Bh1750 = self.Block(Bh1750())
    self._implicit_i2c_pullup_i2c = self.Block(I2cPullup())

    self.connect(self.UsbCReceptacle.pwr, self.Ldl1117.pwr_in)
    self.connect(self.Ldl1117.gnd, self.Esp32_Wroom_32.gnd, self.Hdc1080.gnd, self.Bme680.gnd, self.Bh1750.gnd, self.UsbCReceptacle.gnd)
    self.connect(self.Bme680.i2c, self.Bh1750.i2c, self.Hdc1080.i2c, self.Esp32_Wroom_32.i2c.request('i2c_16'), self._implicit_i2c_pullup_i2c.i2c)
    self.connect(self.Esp32_Wroom_32.pwr, self.Hdc1080.pwr, self.Bme680.pwr, self.Bh1750.pwr, self.Ldl1117.pwr_out, self._implicit_i2c_pullup_i2c.pwr)
"""


class ImplicitI2cTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/IotSensorImplicitI2c.json")) as f:
      netlist_data = f.read()
      netlist = JsonNetlist.model_validate_json(netlist_data)

    hdl = tohdl_netlist(netlist)
    self.assertEqual(hdl, EXPECTED_HDL)

    result = compile_netlist(netlist)  # just check it doesn't error out
    self.assertEqual(result.errors, [])
