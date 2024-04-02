import unittest

import sys
sys.path.append('../')
import life

class TestCell(unittest.TestCase):
    def test_create_cell(self):
        x, y = 1, 1
        new_cell = life.Cell(x,y)
        self.assertEqual(str(new_cell), f'({x},{y})')

if __name__ == '__main__':
    unittest.main()