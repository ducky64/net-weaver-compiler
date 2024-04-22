import unittest
import os.path

from netlist_compiler import JsonNetlist
from server import app
app.testing = True


EXPECTED_NETLIST = [
  {'name': '_t42BdSzQ.signal', 'pads': [['_p5zNfcKi', '10'], ['_t42BdSzQ_package', '2']]},
  {'name': '_p5zNfcKi.gnd_out', 'pads': [['_p5zNfcKi', '4'], ['_p5zNfcKi', '17'], ['_t42BdSzQ_res', '2']]},
  {'name': '_p5zNfcKi.pwr_out', 'pads': [['_p5zNfcKi', '29']]},
  {'name': '_p5zNfcKi.vusb_out', 'pads': [['_p5zNfcKi', '19']]},
  {'name': '_t42BdSzQ.res.a', 'pads': [['_t42BdSzQ_res', '1'], ['_t42BdSzQ_package', '1']]}
]

EXPECTED_KICAD_NETLIST = """\
(export (version D)
(components
(comp (ref "_p5zNfcKi")
  (value "NUCLEO-F303K8")
  (footprint "edg:Nucleo32")
  (property (name "Sheetname") (value ""))
  (property (name "Sheetfile") (value ""))
  (property (name "edg_path") (value "_p5zNfcKi"))
  (property (name "edg_short_path") (value "_p5zNfcKi"))
  (property (name "edg_refdes") (value "U1"))
  (property (name "edg_part") (value "NUCLEO-F303K8 (STMicroelectronics)"))
  (sheetpath (names "/") (tstamps "/"))
  (tstamps "1075034a"))
(comp (ref "_t42BdSzQ.package")
  (value "Red 615~630nm 1.9~2.2V 0603 Light Emitting Diodes (LED) RoHS")
  (footprint "LED_SMD:LED_0603_1608Metric")
  (property (name "Sheetname") (value "_t42BdSzQ"))
  (property (name "Sheetfile") (value "electronics_abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "_t42BdSzQ.package"))
  (property (name "edg_short_path") (value "_t42BdSzQ.package"))
  (property (name "edg_refdes") (value "D1"))
  (property (name "edg_part") (value "KT-0603R (Hubei KENTO Elec)"))
  (sheetpath (names "/_t42BdSzQ/") (tstamps "/0eb002fe/"))
  (tstamps "0b4e02cd"))
(comp (ref "_t42BdSzQ.res")
  (value "±1% 1/10W Thick Film Resistors 75V ±100ppm/℃ -55℃~+155℃ 1kΩ 0603 Chip Resistor - Surface Mount ROHS")
  (footprint "Resistor_SMD:R_0603_1608Metric")
  (property (name "Sheetname") (value "_t42BdSzQ"))
  (property (name "Sheetfile") (value "electronics_abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "_t42BdSzQ.res"))
  (property (name "edg_short_path") (value "_t42BdSzQ.res"))
  (property (name "edg_refdes") (value "R1"))
  (property (name "edg_part") (value "0603WAF1001T5E (UNI-ROYAL(Uniroyal Elec))"))
  (sheetpath (names "/_t42BdSzQ/") (tstamps "/0eb002fe/"))
  (tstamps "0296014b")))
(nets
(net (code 1) (name "_t42BdSzQ.signal")
  (node (ref _p5zNfcKi) (pin 10))
  (node (ref _t42BdSzQ.package) (pin 2)))
(net (code 2) (name "_p5zNfcKi.gnd_out")
  (node (ref _p5zNfcKi) (pin 4))
  (node (ref _p5zNfcKi) (pin 17))
  (node (ref _t42BdSzQ.res) (pin 2)))
(net (code 3) (name "_p5zNfcKi.pwr_out")
  (node (ref _p5zNfcKi) (pin 29)))
(net (code 4) (name "_p5zNfcKi.vusb_out")
  (node (ref _p5zNfcKi) (pin 19)))
(net (code 5) (name "_t42BdSzQ.res.a")
  (node (ref _t42BdSzQ.res) (pin 1))
  (node (ref _t42BdSzQ.package) (pin 1))))
)"""

EXPECTED_SVGPCB_INSTANTIATIONS = [
  "const _p5zNfcKi = board.add(Nucleo32, {\ntranslate: pt(0, 0), rotate: 0,\nid: '_p5zNfcKi'\n})",
  "const _t42BdSzQ_package = board.add(LED_0603_1608Metric, {\ntranslate: pt(0, 0), rotate: 0,\nid: '_t42BdSzQ_package'\n})",
  "const _t42BdSzQ_res = board.add(R_0603_1608Metric, {\ntranslate: pt(0, 0), rotate: 0,\nid: '_t42BdSzQ_res'\n})",
]


class BasicBlinkyTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "BasicBlinky.json")) as f:
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
