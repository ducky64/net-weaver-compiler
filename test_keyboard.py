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

EXPECTED_SVGPCB_FUNCTIONS = ["""\
function SwitchMatrix__xQhDBnLi_2_3(xy, colSpacing=1, rowSpacing=1, diodeOffset=[0.25, 0]) {
  // Circuit generator params
  const ncols = 2
  const nrows = 3

  // Global params
  const traceSize = 0.015
  const viaTemplate = via(0.02, 0.035)

  // Return object
  const obj = {
    footprints: {},
    pts: {}
  }

  // Actual generator code
  allColWirePoints = []
  for (let yIndex=0; yIndex < nrows; yIndex++) {
    colWirePoints = []
    rowDiodeVias = []

    for (let xIndex=0; xIndex < ncols; xIndex++) {
      index = yIndex * ncols + xIndex + 1

      buttonPos = [colSpacing * xIndex, rowSpacing * yIndex]
      obj.footprints[`sw[${xIndex}][${yIndex}]`] = button = board.add(
        SW_SPST_SKQG_WithoutStem,
        {
          translate: buttonPos, rotate: 0,
          id: `_xQhDBnLi_sw[${xIndex}][${yIndex}]`
        })

      diodePos = [buttonPos[0] + diodeOffset[0], buttonPos[1] + diodeOffset[1]]
      obj[`d[${xIndex}][${yIndex}]`] = diode = board.add(
        D_SMA,
        {
          translate: diodePos, rotate: 90,
          id: `_xQhDBnLi_d[${xIndex}][${yIndex}]`
        })

      // create stub wire for button -> column common line
      colWirePoint = [buttonPos[0], button.padY("2")]
      board.wire([colWirePoint, button.pad("2")], traceSize, "F.Cu")
      colWirePoints.push(colWirePoint)

      // create wire for button -> diode
      board.wire([button.pad("1"), diode.pad("1")], traceSize, "F.Cu")
      diodeViaPos = [diode.padX("2"), diode.padY("2") + 0.5]
      diodeVia = board.add(viaTemplate, {translate: diodeViaPos})
      board.wire([diode.pad("2"), diodeVia.pos], traceSize)

      if (rowDiodeVias.length > 0) {
        board.wire([rowDiodeVias[rowDiodeVias.length - 1].pos, diodeVia.pos], traceSize, "B.Cu")
      }
      rowDiodeVias.push(diodeVia)
    }
    allColWirePoints.push(colWirePoints)
  }

  // Inter-row wiring
  for (let xIndex=0; xIndex < allColWirePoints[0].length; xIndex++) {
    board.wire([
      allColWirePoints[0][xIndex],
      allColWirePoints[allColWirePoints.length - 1][xIndex]
    ], traceSize, "F.Cu")
  }

  return obj
}
"""]


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

    self.assertEqual(result.svgpcbFunctions, EXPECTED_SVGPCB_FUNCTIONS)
    # don't check instantiations, it's just going to be a mess from the discrete RP2040
