import unittest
import os.path

from server import app
app.testing = True


EXPECTED_NETLIST = """\
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
  (tstamps "0296014b"))
(comp (ref "jlc_th.th1")
  (value "")
  (footprint "edg:JlcToolingHole_1.152mm")
  (property (name "Sheetname") (value "jlc_th"))
  (property (name "Sheetfile") (value "edg.BoardTop.JlcToolingHoles"))
  (property (name "edg_path") (value "jlc_th.th1"))
  (property (name "edg_short_path") (value "jlc_th.th1"))
  (property (name "edg_refdes") (value "H1"))
  (property (name "edg_part") (value ""))
  (sheetpath (names "/jlc_th/") (tstamps "/08970275/"))
  (tstamps "0260010e"))
(comp (ref "jlc_th.th2")
  (value "")
  (footprint "edg:JlcToolingHole_1.152mm")
  (property (name "Sheetname") (value "jlc_th"))
  (property (name "Sheetfile") (value "edg.BoardTop.JlcToolingHoles"))
  (property (name "edg_path") (value "jlc_th.th2"))
  (property (name "edg_short_path") (value "jlc_th.th2"))
  (property (name "edg_refdes") (value "H2"))
  (property (name "edg_part") (value ""))
  (sheetpath (names "/jlc_th/") (tstamps "/08970275/"))
  (tstamps "0261010f"))
(comp (ref "jlc_th.th3")
  (value "")
  (footprint "edg:JlcToolingHole_1.152mm")
  (property (name "Sheetname") (value "jlc_th"))
  (property (name "Sheetfile") (value "edg.BoardTop.JlcToolingHoles"))
  (property (name "edg_path") (value "jlc_th.th3"))
  (property (name "edg_short_path") (value "jlc_th.th3"))
  (property (name "edg_refdes") (value "H3"))
  (property (name "edg_part") (value ""))
  (sheetpath (names "/jlc_th/") (tstamps "/08970275/"))
  (tstamps "02620110")))
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

class BasicBlinkyTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "BasicBlinky.json")) as f:
      netlist_data = f.read()

    with app.test_client() as client:
      response = client.post('/compile', data=netlist_data)

      self.assertEqual(response.json, {
        'kicadNetlist': EXPECTED_NETLIST,
        'errors': []
      })
      self.assertEqual(response.status_code, 200)
