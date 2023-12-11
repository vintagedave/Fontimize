import unittest
from fontimize import get_used_characters_in_html, charPair, _get_char_ranges, optimise_fonts
from fontTools.ttLib import TTFont

class TestGetUsedCharactersInHtml(unittest.TestCase):
    def test_empty_html(self):
        self.assertEqual(get_used_characters_in_html(''), set(' '))

    def test_html_with_no_text(self):
        self.assertEqual(get_used_characters_in_html('<html><body></body></html>'), set(' '))

    def test_html_with_text(self):
        self.assertEqual(get_used_characters_in_html('<html><body>Hello, World!</body></html>'), set('Hello, World!'))

    def test_html_with_repeated_text(self):
        self.assertEqual(get_used_characters_in_html('<html><body>Hello, World! Hello, World!</body></html>'), set('Hello, World!'))

    def test_html_with_multiple_spans(self):
        self.assertEqual(get_used_characters_in_html('<html><body><span>Hello</span><span>, </span><span>World!</span></body></html>'), set('Hello, World!'))

    def test_html_with_multiple_divs(self):
        self.assertEqual(get_used_characters_in_html('<html><body><div>Hello</div><div>, </div><div>World!</div></body></html>'), set('Hello, World!'))

    def test_html_with_links(self):
        self.assertEqual(get_used_characters_in_html('<html><body><a href="https://example.com">Hello, World!</a></body></html>'), set('Hello, World!'))

    def test_html_with_nested_tags(self):
        self.assertEqual(get_used_characters_in_html('<html><body><div><span>Hello, </span><a href="https://example.com">World!</a></span></div></body></html>'), set('Hello, World!'))


class TestCharPairs(unittest.TestCase):
    def test_get_range_with_single_char(self):
        self.assertEqual(charPair('a', 'a').get_range(), 'U+0061')

    # Note that the second of the pair does not have the "U+" -- this caught me out
    # with parse errors inside TTF2Web()
    def test_get_range_with_two_chars(self):
        self.assertEqual(charPair('a', 'b').get_range(), 'U+0061-0062')

    def test_get_range_with_multiple_chars(self):
        self.assertEqual(charPair('a', 'd').get_range(), 'U+0061-0064')


class TestCharRanges(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_get_char_ranges([]), [])

    def test_single_char(self):
        self.assertEqual(_get_char_ranges(['a']), [charPair('a', 'a')])

    def test_two_sequential_chars(self):
        self.assertEqual(_get_char_ranges(['a', 'b']), [charPair('a', 'b')])

    def test_two_nonsequential_chars(self):
        self.assertEqual(_get_char_ranges(['a', 'c']), [charPair('a', 'a'), charPair('c', 'c')])

    def test_multiple_ranges(self):
        self.assertEqual(_get_char_ranges(['a', 'b', 'd', 'e', 'f', 'h']), [charPair('a', 'b'), charPair('d', 'f'), charPair('h', 'h')])


class TestOptimiseFonts(unittest.TestCase):
    # Contains unique characters, none repeated, a couple of capitals, some symbols, and 26 lowercase
    test_string = " ,.@QT_abcdefghijklmnopqrstuvwxyz"

    # Used to verify the number of glyphs in a font matches the number of (unique!) characters in the test string
    def _count_glyphs_in_font(self, fontpath):
        font = TTFont(fontpath)
        cmap = font['cmap']
        return len(cmap.getBestCmap())

    def test_optimise_fonts_with_single_font(self):
        result = optimise_fonts(self.test_string, ['tests/Spirax-Regular.ttf'], fontpath='tests/output')
        # Basics
        self.assertIsInstance(result, dict)
        self.assertIn('tests/Spirax-Regular.ttf', result)
        # Generated with the right name
        self.assertEqual(result['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number
        self.assertEqual(len(self.test_string), self._count_glyphs_in_font(result['tests/Spirax-Regular.ttf']))

    def test_optimise_fonts_with_multiple_fonts(self):
        result = optimise_fonts(self.test_string,
            ['tests/Spirax-Regular.ttf', 'tests/EBGaramond-VariableFont_wght.ttf', 'tests/EBGaramond-Italic-VariableFont_wght.ttf'],
            fontpath='tests/output')
        self.assertIsInstance(result, dict)
        self.assertIn('tests/Spirax-Regular.ttf', result)
        self.assertEqual(result['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        self.assertIn('tests/EBGaramond-VariableFont_wght.ttf', result)
        self.assertEqual(result['tests/EBGaramond-VariableFont_wght.ttf'], 'tests/output/EBGaramond-VariableFont_wght.FontimizeSubset.woff2')
        self.assertIn('tests/EBGaramond-Italic-VariableFont_wght.ttf', result)
        self.assertEqual(result['tests/EBGaramond-Italic-VariableFont_wght.ttf'], 'tests/output/EBGaramond-Italic-VariableFont_wght.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number
        self.assertEqual(len(self.test_string), self._count_glyphs_in_font(result['tests/Spirax-Regular.ttf']))
        self.assertEqual(len(self.test_string), self._count_glyphs_in_font(result['tests/EBGaramond-VariableFont_wght.ttf']))
        self.assertEqual(len(self.test_string), self._count_glyphs_in_font(result['tests/EBGaramond-Italic-VariableFont_wght.ttf']))

    def test_optimise_fonts_with_empty_text(self):
        result = optimise_fonts("",
            ['tests/Spirax-Regular.ttf'],
            fontpath='tests/output')
        self.assertIsInstance(result, dict)
        self.assertIn('tests/Spirax-Regular.ttf', result)
        self.assertEqual(result['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number: one, because an empty string is reported as containing space, see get_used_characters_in_str
        self.assertEqual(1, self._count_glyphs_in_font(result['tests/Spirax-Regular.ttf']))
        

if __name__ == '__main__':
    unittest.main()