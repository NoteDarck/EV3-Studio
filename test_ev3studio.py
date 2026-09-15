import unittest
from ev3studio_config import distance_to_degrees, turn_to_degrees
from validator import validate_code, validate_project

class EV3StudioTests(unittest.TestCase):
    def test_distance_conversion(self):
        self.assertAlmostEqual(distance_to_degrees(56 * 3.141592653589793, 56), 360)
    def test_turn_conversion(self):
        self.assertGreater(turn_to_degrees(90, 56, 120), 0)
    def test_empty_program(self):
        self.assertTrue(validate_code(""))
    def test_valid_port(self):
        self.assertFalse(validate_code("Motor(Port.A)"))
    def test_invalid_project(self):
        self.assertTrue(validate_project({}))

if __name__ == "__main__":
    unittest.main()
