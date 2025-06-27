import unittest
import os.path

from netlist_compiler import JsonNetlist
from app import app
app.testing = True


EXPECTED_HDL = """\
class MyModule(SimpleBoardTop):
  def __init__(self):
    super().__init__()

    self.Xiao_Esp32c3 = self.Block(Xiao_Esp32c3())
    self.IndicatorLed = self.Block(IndicatorLed())

    self.connect(self.IndicatorLed.signal, self.Xiao_Esp32c3.gpio.request('gpio_14'))
    self.connect(self.IndicatorLed.gnd, self.Xiao_Esp32c3.gnd)
"""

EXPECTED_KICAD_NETLIST = """\
(export (version D)
(components
(comp (ref "U1")
  (value "Xiao_Esp32c3")
  (footprint "Seeed Studio XIAO Series Library:XIAO-ESP32C3-SMD")
  (property (name "Sheetname") (value ""))
  (property (name "Sheetfile") (value ""))
  (property (name "edg_path") (value "Xiao_Esp32c3"))
  (property (name "edg_short_path") (value "Xiao_Esp32c3"))
  (property (name "edg_refdes") (value "U1"))
  (property (name "edg_part") (value "XIAO ESP32C3"))
  (property (name "edg_value") (value "XIAO ESP32C3"))
  (sheetpath (names "/") (tstamps "/"))
  (tstamps "1c780414"))
(comp (ref "D1")
  (value "IndicatorLed.package")
  (footprint "LED_SMD:LED_0603_1608Metric")
  (property (name "Sheetname") (value "IndicatorLed"))
  (property (name "Sheetfile") (value "PolymorphicBlocks.edg.abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "IndicatorLed.package"))
  (property (name "edg_short_path") (value "IndicatorLed.package"))
  (property (name "edg_refdes") (value "D1"))
  (property (name "edg_part") (value "KT-0603R (Hubei KENTO Elec)"))
  (property (name "edg_value") (value "Red 615~630nm 1.9~2.2V 0603 Light Emitting Diodes (LED) RoHS"))
  (sheetpath (names "/IndicatorLed/") (tstamps "/1e4704b3/"))
  (tstamps "0b4e02cd"))
(comp (ref "R1")
  (value "IndicatorLed.res")
  (footprint "Resistor_SMD:R_0603_1608Metric")
  (property (name "Sheetname") (value "IndicatorLed"))
  (property (name "Sheetfile") (value "PolymorphicBlocks.edg.abstract_parts.AbstractLed.IndicatorLed"))
  (property (name "edg_path") (value "IndicatorLed.res"))
  (property (name "edg_short_path") (value "IndicatorLed.res"))
  (property (name "edg_refdes") (value "R1"))
  (property (name "edg_part") (value "0603WAF1001T5E (UNI-ROYAL(Uniroyal Elec))"))
  (property (name "edg_value") (value "±1% 1/10W Thick Film Resistors 75V ±100ppm/℃ -55℃~+155℃ 1kΩ 0603 Chip Resistor - Surface Mount ROHS"))
  (sheetpath (names "/IndicatorLed/") (tstamps "/1e4704b3/"))
  (tstamps "0296014b")))
(nets
(net (code 1) (name "IndicatorLed.signal")
  (node (ref U1) (pin 2))
  (node (ref D1) (pin 2)))
(net (code 2) (name "IndicatorLed.gnd")
  (node (ref U1) (pin 13))
  (node (ref R1) (pin 2)))
(net (code 3) (name "Xiao_Esp32c3.pwr_out")
  (node (ref U1) (pin 12)))
(net (code 4) (name "Xiao_Esp32c3.vusb_out")
  (node (ref U1) (pin 14)))
(net (code 5) (name "IndicatorLed.res.a")
  (node (ref R1) (pin 1))
  (node (ref D1) (pin 1))))
)"""

EXPECTED_SVGPCB = """\
const board = new PCB();

// Xiao_Esp32c3
const U1 = board.add(XIAO_ESP32C3_SMD, {
  translate: pt(0.348, 0.412), rotate: 0,
  id: 'U1'
})
// IndicatorLed.package
const D1 = board.add(LED_0603_1608Metric, {
  translate: pt(0.798, 0.029), rotate: 0,
  id: 'D1'
})
// IndicatorLed.res
const R1 = board.add(R_0603_1608Metric, {
  translate: pt(0.798, 0.126), rotate: 0,
  id: 'R1'
})

board.setNetlist([
  {name: "IndicatorLed.signal", pads: [["U1", "2"], ["D1", "2"]]},
  {name: "IndicatorLed.gnd", pads: [["U1", "13"], ["R1", "2"]]},
  {name: "Xiao_Esp32c3.pwr_out", pads: [["U1", "12"]]},
  {name: "Xiao_Esp32c3.vusb_out", pads: [["U1", "14"]]},
  {name: "IndicatorLed.res.a", pads: [["R1", "1"], ["D1", "1"]]}
])

const limit0 = pt(-0.07874015748031496, -0.07874015748031496);
const limit1 = pt(0.9742125984251969, 0.9238188976377953);
const xMin = Math.min(limit0[0], limit1[0]);
const xMax = Math.max(limit0[0], limit1[0]);
const yMin = Math.min(limit0[1], limit1[1]);
const yMax = Math.max(limit0[1], limit1[1]);

const filletRadius = 0.1;
const outline = path(
  [(xMin+xMax/2), yMax],
  ["fillet", filletRadius, [xMax, yMax]],
  ["fillet", filletRadius, [xMax, yMin]],
  ["fillet", filletRadius, [xMin, yMin]],
  ["fillet", filletRadius, [xMin, yMax]],
  [(xMin+xMax/2), yMax],
);
board.addShape("outline", outline);

renderPCB({
  pcb: board,
  layerColors: {
    "F.Paste": "#000000ff",
    "F.Mask": "#000000ff",
    "B.Mask": "#000000ff",
    "componentLabels": "#00e5e5e5",
    "outline": "#002d00ff",
    "padLabels": "#ffff99e5",
    "B.Cu": "#ef4e4eff",
    "F.Cu": "#ff8c00cc",
  },
  limits: {
    x: [xMin, xMax],
    y: [yMin, yMax]
  },
  background: "#00000000",
  mmPerUnit: 25.4
})


"""

EXPECTED_BOM = """\
Id,Designator,Footprint,Quantity,Designation,Supplier and Ref,JLCPCB Part #,Manufacturer,Part
1,U1,Seeed Studio XIAO Series Library:XIAO-ESP32C3-SMD,1,,,,,XIAO ESP32C3
2,D1,LED_SMD:LED_0603_1608Metric,1,Red 615~630nm 1.9~2.2V 0603 Light Emitting Diodes (LED) RoHS,,C2286,Hubei KENTO Elec,KT-0603R
3,R1,Resistor_SMD:R_0603_1608Metric,1,±1% 1/10W Thick Film Resistors 75V ±100ppm/℃ -55℃~+155℃ 1kΩ 0603 Chip Resistor - Surface Mount ROHS,,C21190,UNI-ROYAL(Uniroyal Elec),0603WAF1001T5E
"""


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
      self.assertEqual(response.json['kicadNetlist'], EXPECTED_KICAD_NETLIST)
      self.assertEqual(response.json['svgpcb'], EXPECTED_SVGPCB)
      self.assertEqual(response.json['bom'], EXPECTED_BOM)
