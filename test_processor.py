import unittest
import fitz
from processor import convert_pdf, _rewrite

class ProcessorTests(unittest.TestCase):
    def test_ignores_text_and_comments(self):
        raw = b'0.03 w\n(This is 4 w) Tj\n% 9 w\n0.2 w\n'
        new, n = _rewrite(raw, 0.85, 'fixed')
        self.assertEqual(n, 2)
        self.assertIn(b'(This is 4 w)', new)
        self.assertIn(b'% 9 w', new)
        self.assertIn(b'0.850000 w', new)
    def test_geometry_preserved(self):
        d = fitz.open(); p = d.new_page(width=1000, height=2000)
        p.draw_line((100,100), (300,300), width=0.03)
        before = d.tobytes(); after, info = convert_pdf(before, .3)
        a, b = fitz.open(stream=before, filetype='pdf'), fitz.open(stream=after, filetype='pdf')
        self.assertEqual(a[0].rect, b[0].rect)
        self.assertAlmostEqual(b[0].get_drawings()[0]['width'], 0.3*72/25.4, places=3)

if __name__ == '__main__': unittest.main()
