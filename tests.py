import os
import unittest
from unittest.mock import patch
import sys
from fontimize import get_used_characters_in_html, charPair, _get_char_ranges, optimise_fonts, optimise_fonts_for_files
from fontTools.ttLib import woff2, TTFont

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


# Used to verify the number of glyphs in a font matches the number of (unique!) characters in the test string
def _count_glyphs_in_font(fontpath):
    # with open(fontpath, 'rb') as f:
    # wfr = woff2.WOFF2Reader(f)
    # cmap = font['cmap']
    # return len(cmap.getBestCmap())
    # font.flavor = None  # Decompress the font data
    font = TTFont(fontpath)#flavor='woff2')#, sfntReader=wfr)
    font.flavor = None  # Decompress the font data
    num_glyphs = font['maxp'].numGlyphs # Use font.getGlyphOrder() and https://fontdrop.info to examine, if weird
    return num_glyphs

# Does a named glyph exist in the font?
def _font_contains(fontpath, charname : str) -> bool:
    font = TTFont(fontpath)
    font.flavor = None  # Decompress the font data
    return charname in font.getGlyphOrder()

class TestOptimiseFonts(unittest.TestCase):
    # Contains unique characters, none repeated, a couple of capitals, some symbols, and 26 lowercase
    test_string = " ,.@QT_abcdefghijklmnopqrstuvwxyz"

    def test_optimise_fonts_with_single_font(self):
        result = optimise_fonts(self.test_string, ['tests/Spirax-Regular.ttf'], fontpath='tests/output', verbose=False, print_stats=False)
        # Basics
        self.assertIsInstance(result, dict)
        self.assertIn('tests/Spirax-Regular.ttf', result)
        # Generated with the right name
        self.assertEqual(result['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number
        # For +1, see test_optimise_fonts_with_empty_text
        self.assertEqual(len(self.test_string) + 1, _count_glyphs_in_font(result['tests/Spirax-Regular.ttf']))

    def test_optimise_fonts_with_multiple_fonts(self):
        result = optimise_fonts(self.test_string,
            ['tests/Spirax-Regular.ttf', 'tests/EBGaramond-VariableFont_wght.ttf', 'tests/EBGaramond-Italic-VariableFont_wght.ttf'],
            fontpath='tests/output', verbose=False, print_stats=False)
        self.assertIsInstance(result, dict)
        self.assertIn('tests/Spirax-Regular.ttf', result)
        self.assertEqual(result['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        self.assertIn('tests/EBGaramond-VariableFont_wght.ttf', result)
        self.assertEqual(result['tests/EBGaramond-VariableFont_wght.ttf'], 'tests/output/EBGaramond-VariableFont_wght.FontimizeSubset.woff2')
        self.assertIn('tests/EBGaramond-Italic-VariableFont_wght.ttf', result)
        self.assertEqual(result['tests/EBGaramond-Italic-VariableFont_wght.ttf'], 'tests/output/EBGaramond-Italic-VariableFont_wght.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number
        # + 1 for the tests below -- see test_optimise_fonts_with_empty_text
        self.assertEqual(len(self.test_string) + 1, _count_glyphs_in_font('tests/output/Spirax-Regular.FontimizeSubset.woff2'))
        # + 16, + 12: EB Garamond contains multiple f-ligatures (eg fi), plus other variants, so the number of glyphs is higher. Italic has fewer.
        self.assertEqual(len(self.test_string) + 1 + 16, _count_glyphs_in_font('tests/output/EBGaramond-VariableFont_wght.FontimizeSubset.woff2'))
        self.assertEqual(len(self.test_string) + 1 + 12, _count_glyphs_in_font('tests/output/EBGaramond-Italic-VariableFont_wght.FontimizeSubset.woff2'))

    def test_optimise_fonts_with_empty_text(self):
        result = optimise_fonts("",
            ['tests/Spirax-Regular.ttf'],
            fontpath='tests/output',
            verbose=False, print_stats=False)
        self.assertIsInstance(result, dict)
        self.assertIn('tests/Spirax-Regular.ttf', result)
        self.assertEqual(result['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number: two, because an empty string is reported as containing space, see get_used_characters_in_str
        # and fonts also seem to contain ".notdef":
        #   > font.getGlyphOrder()
        #   > ['.notdef', 'space']
        self.assertEqual(2, _count_glyphs_in_font('tests/output/Spirax-Regular.FontimizeSubset.woff2'))


class TestOptimiseFontsForFiles(unittest.TestCase):

    def setUp(self):
        self.files = ['tests/test1-index-css.html', 'tests/test.txt', 'tests/test2.html']
        self.font_output_dir = 'tests/output'
        self.subsetname = 'TestFilesSubset'
        self.verbose = False
        self.print_stats = False
        # Not used by any HTML/CSS, mimics manually adding a font
        self.fonts = ['tests/Whisper-Regular.ttf', 'tests/NotoSans-VariableFont_wdth,wght.ttf', 'tests/NotoSansJP-VariableFont_wght.ttf']

    @patch.object(sys, 'stdout') # provides mock_stdout in order to hide and verify console output
    def test_optimise_fonts_for_files(self, mock_stdout):
        result = optimise_fonts_for_files(files=self.files, font_output_dir=self.font_output_dir, subsetname=self.subsetname, fonts=self.fonts,
            verbose=False, print_stats=False)
        
        # css_test.css has:
        #   src: url('DOESNOTEXIST.ttf') format('truetype');
        # This will emit a warning, check it was written to standard output
        mock_stdout.write.assert_any_call('Warning: Font file not found (may be remote not local?); skipping: DOESNOTEXIST.ttf (resolved to tests/DOESNOTEXIST.ttf)')
        
        self.assertIsInstance(result, dict)
        self.assertIn('css', result)
        self.assertIn('fonts', result)
        
        css = result['css']
        self.assertIn('tests/css_test.css', css)
        self.assertIn('tests/css_test-index.css', css)
        self.assertEqual(len(css), 2)

        fonts = result['fonts']
        font_keys = fonts.keys()
        self.assertEqual(len(fonts), 7)
        # These five found in CSS, via HTML input
        self.assertIn('tests/EBGaramond-VariableFont_wght.ttf', font_keys)
        self.assertIn('tests/Spirax-Regular.ttf', font_keys)
        self.assertIn('tests/SortsMillGoudy-Regular.ttf', font_keys)
        self.assertIn('tests/SortsMillGoudy-Italic.ttf', font_keys)
        # These are manually specified
        self.assertIn('tests/Whisper-Regular.ttf', font_keys) 
        self.assertIn('tests/NotoSans-VariableFont_wdth,wght.ttf', font_keys) 
        self.assertIn('tests/NotoSansJP-VariableFont_wght.ttf', font_keys) 

        self.maxDiff = None # See full results of below comparison
        self.assertDictEqual(fonts, 
                             {
                                 'tests/Spirax-Regular.ttf': 'tests/output/Spirax-Regular.TestFilesSubset.woff2',
                                 'tests/SortsMillGoudy-Italic.ttf': 'tests/output/SortsMillGoudy-Italic.TestFilesSubset.woff2',
                                 'tests/SortsMillGoudy-Regular.ttf': 'tests/output/SortsMillGoudy-Regular.TestFilesSubset.woff2',
                                 'tests/NotoSansJP-VariableFont_wght.ttf': 'tests/output/NotoSansJP-VariableFont_wght.TestFilesSubset.woff2',
                                 'tests/Whisper-Regular.ttf': 'tests/output/Whisper-Regular.TestFilesSubset.woff2',
                                 'tests/NotoSans-VariableFont_wdth,wght.ttf': 'tests/output/NotoSans-VariableFont_wdth,wght.TestFilesSubset.woff2',
                                 'tests/EBGaramond-VariableFont_wght.ttf': 'tests/output/EBGaramond-VariableFont_wght.TestFilesSubset.woff2'
                             }
                            )
        
        # Do the output fonts exist on disk?
        for filepath in fonts.values():
            abspath = os.path.abspath(filepath)
            print(f"Checking {filepath} as {abspath}")
            self.assertTrue(os.path.exists(filepath), f"Output font {filepath} does not exist")
            self.assertTrue(os.path.exists(abspath), f"Output font {abspath} does not exist (absolute path)")
        
        # Check glyph counts (+1 is ".notdef", present in all fonts)
        # space and '(),-.:;? (=10 with space) and 0123479 (=7) and A-Z (minus BFILRYZ, =19) and a-z (minus z, =25) and acircumflex and ecircumflex = 2
        # Becaue of ', the curled left adn right quotes are added; because of -, en- and em-dashes are added, thus +4
        # Note that test.txt contains Kanji, Hindi and Vietnamese. Kanji and Hindi are not in the Spirax input font, but the circumflexes come from Vietnamese support.
        self.assertEqual(10 + 7 + 19 + 25 + 2 + 4 + 1, _count_glyphs_in_font('tests/output/Spirax-Regular.TestFilesSubset.woff2'))
        # EB Garamond contains many more glyphs
        self.assertEqual(115, _count_glyphs_in_font('tests/output/EBGaramond-VariableFont_wght.TestFilesSubset.woff2'))

        # Check specific characters are present
        # U+1EE5 is "u with dot below", ụ, which is in test.txt - Vietnamese
        self.assertTrue(_font_contains('tests/output/EBGaramond-VariableFont_wght.TestFilesSubset.woff2', 'uni1EE5'))
        # Kanji
        self.assertTrue(_font_contains('tests/output/NotoSansJP-VariableFont_wght.TestFilesSubset.woff2', 'uni6F22'))
        self.assertTrue(_font_contains('tests/output/NotoSansJP-VariableFont_wght.TestFilesSubset.woff2', 'uni5B57'))
        # The above is the Japanese version: Noto Sans JP. The other Noto Sans font does not support Kanji
        # so as a sanity check, verify the glyphs are not there
        self.assertFalse(_font_contains('tests/output/NotoSans-VariableFont_wdth,wght.TestFilesSubset.woff2', 'uni6F22'))
        self.assertFalse(_font_contains('tests/output/NotoSans-VariableFont_wdth,wght.TestFilesSubset.woff2', 'uni5B57'))
        # Devangari (Hindi)
        # Supported by Noto Sans
        self.assertTrue(_font_contains('tests/output/NotoSans-VariableFont_wdth,wght.TestFilesSubset.woff2', 'uni0906')) # char 1 in text.txt
        self.assertTrue(_font_contains('tests/output/NotoSans-VariableFont_wdth,wght.TestFilesSubset.woff2', 'uni0927')) # char 2 (part) in text.txt
        self.assertTrue(_font_contains('tests/output/NotoSans-VariableFont_wdth,wght.TestFilesSubset.woff2', 'uni0941')) # char 2 (part) in text.txt
        # Could check that glyphs (in general) are _not_ present, but the count check above does that

if __name__ == '__main__':
    unittest.main()