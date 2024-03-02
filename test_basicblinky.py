import unittest

from server import app
app.testing = True


class BasicBlinkyTestCase(unittest.TestCase):
  def test_compile(self):
    with open("BasicBlinky.json") as f:
      netlist_data = f.read()

    with app.test_client() as client:
      response = client.post('/compile', data={'netlist': netlist_data})

      self.assertEqual(response.status_code, 200)
      self.assertEqual(response.json, {
        'kicadNetlist': 'TODO',
        'errors': []
      })
