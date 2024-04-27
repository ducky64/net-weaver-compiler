import unittest
import os.path

from netlist_compiler import JsonNetlist
from server import app
app.testing = True


EXPECTED_NETLIST = [
  {'name': '_6u3c3kJZ.signal', 'pads': [['_L45VcfTC', '2'], ['_6u3c3kJZ_package', '2']]},
  {'name': '_6u3c3kJZ.gnd', 'pads': [['_L45VcfTC', '13'], ['_6u3c3kJZ_res', '2']]},
  {'name': '_L45VcfTC.pwr_out', 'pads': [['_L45VcfTC', '12']]},
  {'name': '_L45VcfTC.vusb_out', 'pads': [['_L45VcfTC', '14']]},
  {'name': '_6u3c3kJZ.res.a', 'pads': [['_6u3c3kJZ_res', '1'], ['_6u3c3kJZ_package', '1']]}
]

EXPECTED_KICAD_NETLIST = """\
(export (version D)
(components
(comp (ref "_L45VcfTC")
  (value "XIAO ESP32C3")
  (footprint "Seeed Studio XIAO Series Library:XIAO-Generic-Hybrid-14P-2.54-21X17.8MM")
  (property (name "Sheetname") (value ""))
  (property (name "Sheetfile") (value ""))
  (property (name "edg_path") (value "_L45VcfTC"))
  (property (name "edg_short_path") (value "_L45VcfTC"))
  (property (name "edg_refdes") (value "U1"))
  (property (name "edg_part") (value "XIAO ESP32C3"))
  (sheetpath (names "/") (tstamps "/"))
  (tstamps "0dc102cb"))
(comp (ref "_6u3c3kJZ.package")
  (value "Red 615~630nm 1.9~2.2V 0603 Light Emitting Diodes (LED) RoHS")
  (footprint "LED_SMD:LED_0603_1608Metric")
  (property (name "Sheetname") (value "_6u3c3kJZ"))
  (property (name "Sheetfile") (value "electronics_abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "_6u3c3kJZ.package"))
  (property (name "edg_short_path") (value "_6u3c3kJZ.package"))
  (property (name "edg_refdes") (value "D1"))
  (property (name "edg_part") (value "KT-0603R (Hubei KENTO Elec)"))
  (sheetpath (names "/_6u3c3kJZ/") (tstamps "/0e5f02e3/"))
  (tstamps "0b4e02cd"))
(comp (ref "_6u3c3kJZ.res")
  (value "±1% 1/10W Thick Film Resistors 75V ±100ppm/℃ -55℃~+155℃ 1kΩ 0603 Chip Resistor - Surface Mount ROHS")
  (footprint "Resistor_SMD:R_0603_1608Metric")
  (property (name "Sheetname") (value "_6u3c3kJZ"))
  (property (name "Sheetfile") (value "electronics_abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "_6u3c3kJZ.res"))
  (property (name "edg_short_path") (value "_6u3c3kJZ.res"))
  (property (name "edg_refdes") (value "R1"))
  (property (name "edg_part") (value "0603WAF1001T5E (UNI-ROYAL(Uniroyal Elec))"))
  (sheetpath (names "/_6u3c3kJZ/") (tstamps "/0e5f02e3/"))
  (tstamps "0296014b")))
(nets
(net (code 1) (name "_6u3c3kJZ.signal")
  (node (ref _L45VcfTC) (pin 2))
  (node (ref _6u3c3kJZ.package) (pin 2)))
(net (code 2) (name "_6u3c3kJZ.gnd")
  (node (ref _L45VcfTC) (pin 13))
  (node (ref _6u3c3kJZ.res) (pin 2)))
(net (code 3) (name "_L45VcfTC.pwr_out")
  (node (ref _L45VcfTC) (pin 12)))
(net (code 4) (name "_L45VcfTC.vusb_out")
  (node (ref _L45VcfTC) (pin 14)))
(net (code 5) (name "_6u3c3kJZ.res.a")
  (node (ref _6u3c3kJZ.res) (pin 1))
  (node (ref _6u3c3kJZ.package) (pin 1))))
)"""

EXPECTED_SVGPCB_INSTANTIATIONS = [
  "const _L45VcfTC = board.add(XIAO_Generic_Hybrid_14P_2_54_21X17_8MM, {\ntranslate: pt(0, 0), rotate: 0,\nid: '_L45VcfTC'\n})",
  "const _6u3c3kJZ_package = board.add(LED_0603_1608Metric, {\ntranslate: pt(0, 0), rotate: 0,\nid: '_6u3c3kJZ_package'\n})",
  "const _6u3c3kJZ_res = board.add(R_0603_1608Metric, {\ntranslate: pt(0, 0), rotate: 0,\nid: '_6u3c3kJZ_res'\n})"
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
      self.assertEqual(response.json['errors'], [])
      self.assertEqual(response.json['netlist'], EXPECTED_NETLIST)

      self.assertEqual(response.json['kicadNetlist'], EXPECTED_KICAD_NETLIST)

      self.assertEqual(response.json['svgpcbFunctions'], [])
      self.assertEqual(response.json['svgpcbInstantiations'], EXPECTED_SVGPCB_INSTANTIATIONS)
