import unittest
import os.path

from netlist_compiler import JsonNetlist
from server import app
app.testing = True


class BasicBlinkyTestCase(unittest.TestCase):
  def test_compile(self):
    # the server messes with cwd so we need to use the absolute path
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests/BadMicro.json")) as f:
      netlist_data = f.read()
      JsonNetlist.model_validate_json(netlist_data)

    with app.test_client() as client:
      response = client.post('/compile', data=netlist_data)

      self.assertEqual(response.status_code, 200)
      all_error_paths = [error['path'] for error in response.json['errors']]  # order-independent
      self.assertIn(['_uIfOdj51', '_pwr_link'], all_error_paths)
      self.assertIn(['__nKT51Gkb_pwr_link'], all_error_paths)
