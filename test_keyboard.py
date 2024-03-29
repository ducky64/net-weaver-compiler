import unittest

from server import app
app.testing = True
from netlist_compiler import tohdl_netlist, JsonNetlist


EXPECTED_HDL = """\
class MyModule(JlcBoardTop):
  def __init__(self):
    super().__init__()

    self._QGZd05Ri = self.Block(UsbCReceptacle())
    self._n3w58oKp = self.Block(Ldl1117(output_voltage=(1.0, 3.0)))
    self._xQhDBnLi = self.Block(SwitchMatrix(nrows=3, ncols=2))
    self._UJOuhuHr = self.Block(Rp2040())

    self.connect(self._xQhDBnLi.rows, self._xQhDBnLi.cols, self._UJOuhuHr.gpio.request())
    self.connect(self._n3w58oKp.pwr_in, self._QGZd05Ri.pwr)
    self.connect(self._QGZd05Ri.gnd, self._UJOuhuHr.gnd, self._n3w58oKp.gnd)
    self.connect(self._n3w58oKp.pwr_out, self._UJOuhuHr.pwr)
    self.connect(self._UJOuhuHr.usb, self._QGZd05Ri.usb)
"""

class KeyboardTestCase(unittest.TestCase):
  def test_compile(self):
    with open("Keyboard.json") as f:
      netlist_data = f.read()

    hdl = tohdl_netlist(JsonNetlist.model_validate_json(netlist_data))
    self.assertEqual(hdl, EXPECTED_HDL)

    with app.test_client() as client:  # test it compiles w/o validating the netlist
      response = client.post('/compile', data=netlist_data)

      self.assertEqual(response.status_code, 200)
