import unittest
import os.path

from netlist_compiler import JsonNetlist
from server import app
app.testing = True


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self.Xiao_Esp32c3 = self.Block(Xiao_Esp32c3())
    self.IndicatorLed = self.Block(IndicatorLed())

    self.connect(self.IndicatorLed.signal, self.Xiao_Esp32c3.gpio.request('gpio_14'))
    self.connect(self.IndicatorLed.gnd, self.Xiao_Esp32c3.gnd_out)
"""

EXPECTED_NETLIST = [
  {'name': 'IndicatorLed.signal', 'pads': [['Xiao_Esp32c3', '2'], ['IndicatorLed_package', '2']]},
  {'name': 'IndicatorLed.gnd', 'pads': [['Xiao_Esp32c3', '13'], ['IndicatorLed_res', '2']]},
  {'name': 'Xiao_Esp32c3.pwr_out', 'pads': [['Xiao_Esp32c3', '12']]},
  {'name': 'Xiao_Esp32c3.vusb_out', 'pads': [['Xiao_Esp32c3', '14']]},
  {'name': 'IndicatorLed.res.a', 'pads': [['IndicatorLed_res', '1'], ['IndicatorLed_package', '1']]}
]

EXPECTED_KICAD_NETLIST = """\
(export (version D)
(components
(comp (ref "Xiao_Esp32c3")
  (value "XIAO ESP32C3")
  (footprint "Seeed Studio XIAO Series Library:XIAO-Generic-Hybrid-14P-2.54-21X17.8MM")
  (property (name "Sheetname") (value ""))
  (property (name "Sheetfile") (value ""))
  (property (name "edg_path") (value "Xiao_Esp32c3"))
  (property (name "edg_short_path") (value "Xiao_Esp32c3"))
  (property (name "edg_refdes") (value "U1"))
  (property (name "edg_part") (value "XIAO ESP32C3"))
  (sheetpath (names "/") (tstamps "/"))
  (tstamps "1c780414"))
(comp (ref "IndicatorLed.package")
  (value "Red 615~630nm 1.9~2.2V 0603 Light Emitting Diodes (LED) RoHS")
  (footprint "LED_SMD:LED_0603_1608Metric")
  (property (name "Sheetname") (value "IndicatorLed"))
  (property (name "Sheetfile") (value "PolymorphicBlocks.edg.abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "IndicatorLed.package"))
  (property (name "edg_short_path") (value "IndicatorLed.package"))
  (property (name "edg_refdes") (value "D1"))
  (property (name "edg_part") (value "KT-0603R (Hubei KENTO Elec)"))
  (sheetpath (names "/IndicatorLed/") (tstamps "/1e4704b3/"))
  (tstamps "0b4e02cd"))
(comp (ref "IndicatorLed.res")
  (value "±1% 1/10W Thick Film Resistors 75V ±100ppm/℃ -55℃~+155℃ 1kΩ 0603 Chip Resistor - Surface Mount ROHS")
  (footprint "Resistor_SMD:R_0603_1608Metric")
  (property (name "Sheetname") (value "IndicatorLed"))
  (property (name "Sheetfile") (value "PolymorphicBlocks.edg.abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "IndicatorLed.res"))
  (property (name "edg_short_path") (value "IndicatorLed.res"))
  (property (name "edg_refdes") (value "R1"))
  (property (name "edg_part") (value "0603WAF1001T5E (UNI-ROYAL(Uniroyal Elec))"))
  (sheetpath (names "/IndicatorLed/") (tstamps "/1e4704b3/"))
  (tstamps "0296014b")))
(nets
(net (code 1) (name "IndicatorLed.signal")
  (node (ref Xiao_Esp32c3) (pin 2))
  (node (ref IndicatorLed.package) (pin 2)))
(net (code 2) (name "IndicatorLed.gnd")
  (node (ref Xiao_Esp32c3) (pin 13))
  (node (ref IndicatorLed.res) (pin 2)))
(net (code 3) (name "Xiao_Esp32c3.pwr_out")
  (node (ref Xiao_Esp32c3) (pin 12)))
(net (code 4) (name "Xiao_Esp32c3.vusb_out")
  (node (ref Xiao_Esp32c3) (pin 14)))
(net (code 5) (name "IndicatorLed.res.a")
  (node (ref IndicatorLed.res) (pin 1))
  (node (ref IndicatorLed.package) (pin 1))))
)"""

EXPECTED_SVGPCB_INSTANTIATIONS = [
  "const Xiao_Esp32c3 = board.add(XIAO_Generic_Hybrid_14P_2_54_21X17_8MM, {\n  translate: pt(0, 0), rotate: 0,\n  id: 'Xiao_Esp32c3'\n})",
  "const IndicatorLed_package = board.add(LED_0603_1608Metric, {\n  translate: pt(0, 0), rotate: 0,\n  id: 'IndicatorLed_package'\n})",
  "const IndicatorLed_res = board.add(R_0603_1608Metric, {\n  translate: pt(0, 0), rotate: 0,\n  id: 'IndicatorLed_res'\n})"
]




class BasicBlinkyTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/BasicBlinky.json")) as f:
      netlist_data = f.read()
      JsonNetlist.model_validate_json(netlist_data)

    with app.test_client() as client:
      response = client.post('/compile', data=netlist_data)

      self.assertEqual(response.status_code, 200)
      self.assertEqual(response.json['edgHdl'], EXPECTED_HDL)
      self.assertEqual(response.json['errors'], [])
      self.assertEqual(response.json['netlist'], EXPECTED_NETLIST)

      self.assertEqual(response.json['kicadNetlist'], EXPECTED_KICAD_NETLIST)

      self.assertEqual(response.json['svgpcbFunctions'], [])
      self.assertEqual(response.json['svgpcbInstantiations'], EXPECTED_SVGPCB_INSTANTIATIONS)
