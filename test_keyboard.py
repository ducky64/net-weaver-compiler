import unittest

from netlist_compiler import tohdl_netlist, JsonNetlist


EXPECTED_HDL = """\
"""

class KeyboardTestCase(unittest.TestCase):
  def test_compile(self):
    with open("Keyboard.json") as f:
      netlist_data = JsonNetlist.model_validate_json(f.read())

    hdl = tohdl_netlist(netlist_data)
    print(hdl)

    #
    # with app.test_client() as client:
    #   response = client.post('/compile', data=netlist_data)
    #
    #   self.assertEqual(response.json, {
    #     'kicadNetlist': EXPECTED_NETLIST,
    #     'errors': []
    #   })
    #   self.assertEqual(response.status_code, 200)
