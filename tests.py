import os
import tempfile
import unittest
from unittest.mock import patch
import sys
from fontimize import (get_used_characters_in_html, get_used_characters_in_str, charPair, _get_char_ranges,
    optimise_fonts, optimise_fonts_for_files, _find_font_face_urls, _extract_pseudo_elements_content, _get_path,
    _rewrite_css)
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
        foundfonts = result["fonts"]
        self.assertIn('tests/Spirax-Regular.ttf', foundfonts)
        # Generated with the right name
        self.assertEqual(foundfonts['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        # If the number of glyphs in the font matches the expected number
        # For +1, see test_optimise_fonts_with_empty_text
        self.assertEqual(len(self.test_string) + 1, _count_glyphs_in_font(foundfonts['tests/Spirax-Regular.ttf']))

    def test_optimise_fonts_with_multiple_fonts(self):
        result = optimise_fonts(self.test_string,
            ['tests/Spirax-Regular.ttf', 'tests/EBGaramond-VariableFont_wght.ttf', 'tests/EBGaramond-Italic-VariableFont_wght.ttf'],
            fontpath='tests/output', verbose=False, print_stats=False)
        self.assertIsInstance(result, dict)
        foundfonts = result["fonts"]
        self.assertIn('tests/Spirax-Regular.ttf', foundfonts)
        self.assertEqual(foundfonts['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
        self.assertIn('tests/EBGaramond-VariableFont_wght.ttf', foundfonts)
        self.assertEqual(foundfonts['tests/EBGaramond-VariableFont_wght.ttf'], 'tests/output/EBGaramond-VariableFont_wght.FontimizeSubset.woff2')
        self.assertIn('tests/EBGaramond-Italic-VariableFont_wght.ttf', foundfonts)
        self.assertEqual(foundfonts['tests/EBGaramond-Italic-VariableFont_wght.ttf'], 'tests/output/EBGaramond-Italic-VariableFont_wght.FontimizeSubset.woff2')
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
        foundfonts = result["fonts"]
        self.assertIn('tests/Spirax-Regular.ttf', foundfonts)
        self.assertEqual(foundfonts['tests/Spirax-Regular.ttf'], 'tests/output/Spirax-Regular.FontimizeSubset.woff2')
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

class TestFindFontFaceUrls(unittest.TestCase):

    def test_extracts_urls_from_css_test(self) -> None:
        """All three @font-face src URLs in css_test.css should be found."""
        with open('tests/css_test.css', 'r') as f:
            css: str = f.read()
        urls: list[str] = _find_font_face_urls(css)
        self.assertEqual(urls, [
            'EBGaramond-VariableFont_wght.ttf',
            'DOESNOTEXIST.ttf',
            'Spirax-Regular.ttf',
        ])

    def test_extracts_urls_from_css_index(self) -> None:
        """Both @font-face src URLs in css_test-index.css should be found."""
        with open('tests/css_test-index.css', 'r') as f:
            css: str = f.read()
        urls: list[str] = _find_font_face_urls(css)
        self.assertEqual(urls, [
            'SortsMillGoudy-Regular.ttf',
            'SortsMillGoudy-Italic.ttf',
        ])

    def test_unquoted_url_extracted(self) -> None:
        """url(font.ttf) without quotes should work the same as url('font.ttf')."""
        css: str = "@font-face { font-family: 'test'; src: url(font.ttf) format('truetype'); }"
        urls: list[str] = _find_font_face_urls(css)
        self.assertEqual(urls, ['font.ttf'])

    def test_local_source_skipped_url_extracted(self) -> None:
        """local() is a font name, not a file path, so we can't subset it — only url() should be extracted."""
        css: str = "@font-face { font-family: 'test'; src: local('MyFont'), url('font.ttf') format('truetype'); }"
        urls: list[str] = _find_font_face_urls(css)
        self.assertEqual(urls, ['font.ttf'])

    def test_multiple_url_sources_in_one_rule(self) -> None:
        """When src lists multiple url() entries (e.g. woff2 and ttf), all should be extracted."""
        css: str = "@font-face { font-family: 'test'; src: url('font.woff2') format('woff2'), url('font.ttf') format('truetype'); }"
        urls: list[str] = _find_font_face_urls(css)
        self.assertEqual(urls, ['font.woff2', 'font.ttf'])

    def test_no_font_face_rules(self) -> None:
        css: str = "body { font-family: sans-serif; }"
        urls: list[str] = _find_font_face_urls(css)
        self.assertEqual(urls, [])

    def test_empty_css(self) -> None:
        urls: list[str] = _find_font_face_urls("")
        self.assertEqual(urls, [])


class TestExtractPseudoElementsContent(unittest.TestCase):

    def test_extracts_from_css_test(self) -> None:
        """css_test.css has cite:before and ul li:before with special characters."""
        with open('tests/css_test.css', 'r') as f:
            css: str = f.read()
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 2)
        self.assertIn(' \u2E3A ', contents)  # " ⸺ " (two-em-dash with spaces)
        self.assertIn('\u25B8', contents)     # "▸" (right-pointing triangle)

    def test_extracts_from_css_index(self) -> None:
        """css_test-index.css has .sidenote-long:before with a ✻ character."""
        with open('tests/css_test-index.css', 'r') as f:
            css: str = f.read()
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        self.assertIn('\u273B', contents)  # "✻"

    def test_double_colon_before(self) -> None:
        """Both ::before and :before syntax should be recognized."""
        css: str = "p::before { content: 'X'; }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(contents, ['X'])

    def test_counter_decimal_default(self) -> None:
        """counter() with no style defaults to decimal digits."""
        css: str = "ol li::before { content: counter(item); }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        self.assertTrue(all(ch in contents[0] for ch in "0123456789"))

    def test_counter_with_style(self) -> None:
        """counter() with an explicit style includes only that style's characters."""
        css: str = "ol li::before { content: counter(item, upper-roman); }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        self.assertTrue(all(ch in contents[0] for ch in "IVXLCDM"))
        # Should not include decimal digits
        self.assertFalse(any(ch in contents[0] for ch in "0123456789"))

    def test_counter_lower_greek(self) -> None:
        """counter() with lower-greek includes Greek lowercase letters."""
        css: str = "li::before { content: counter(item, lower-greek); }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        self.assertIn('α', contents[0])
        self.assertIn('ω', contents[0])

    def test_counters_with_style(self) -> None:
        """counters() with a separator and style parses the style correctly."""
        css: str = 'li::before { content: counters(item, ".", lower-roman); }'
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        self.assertTrue(all(ch in contents[0] for ch in "ivxlcdm"))

    def test_counter_unknown_style_includes_all(self) -> None:
        """An unrecognised counter style falls back to all numeral characters."""
        css: str = "li::before { content: counter(item, some-future-style); }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        # Fallback should include digits AND roman numerals AND Greek etc
        self.assertIn('0', contents[0])
        self.assertIn('I', contents[0])
        self.assertIn('α', contents[0])

    def test_open_quote_includes_locale_quotes(self) -> None:
        """open-quote adds all locale quote mark characters."""
        css: str = "q::before { content: open-quote; }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        for ch in '\u201c\u201d\u00ab\u00bb\u2018\u2019':  # "", «», ''
            self.assertIn(ch, contents[0])

    def test_close_quote_includes_locale_quotes(self) -> None:
        """close-quote also adds all locale quote mark characters."""
        css: str = "q::after { content: close-quote; }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(len(contents), 1)
        self.assertIn('\u00bb', contents[0])  # »

    def test_attr_emits_warning(self) -> None:
        """attr() cannot be resolved at CSS parse time and should emit a warning."""
        import warnings as w
        css: str = "a::after { content: attr(href); }"
        with w.catch_warnings(record=True) as caught:
            w.simplefilter('always')
            contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(contents, [])
        self.assertEqual(len(caught), 1)
        self.assertIn('attr()', str(caught[0].message))

    def test_none_and_normal_excluded(self) -> None:
        """content: none and content: normal should not produce characters."""
        css: str = "p::before { content: none; } q::after { content: normal; }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(contents, [])

    def test_no_pseudo_elements(self) -> None:
        css: str = "body { color: red; }"
        contents: list[str] = _extract_pseudo_elements_content(css)
        self.assertEqual(contents, [])

    def test_empty_css(self) -> None:
        contents: list[str] = _extract_pseudo_elements_content("")
        self.assertEqual(contents, [])


class TestGetPath(unittest.TestCase):

    def test_simple_relative(self) -> None:
        result: str = _get_path('/a/b/c.html', 'style.css')
        self.assertEqual(result, '/a/b/style.css')

    def test_parent_traversal_normalized(self) -> None:
        """../ in paths should be resolved, e.g. /a/b/../fonts/f.ttf becomes /a/fonts/f.ttf."""
        result: str = _get_path('/a/b/c.html', '../fonts/f.ttf')
        self.assertEqual(result, '/a/fonts/f.ttf')

    def test_empty_dirname(self) -> None:
        """A file with no directory path like 'c.html' has dirname '', so join just returns the relative path."""
        result: str = _get_path('c.html', 'style.css')
        self.assertEqual(result, 'style.css')

    def test_absolute_relative_path(self) -> None:
        """An absolute second argument should be returned as-is (os.path.join behaviour)."""
        result: str = _get_path('/a/b/c.html', '/fonts/f.ttf')
        self.assertEqual(result, '/fonts/f.ttf')


class TestCssDetection(unittest.TestCase):
    """Only actual .css files (or rel=stylesheet links) should be detected as CSS."""

    def _make_temp_html(self, link_href: str) -> str:
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, dir='tests')
        f.write(f'<html><head><link rel="alternate" href="{link_href}"></head><body>text</body></html>')
        f.flush()
        f.close()
        return f.name

    def test_css_href_detected(self) -> None:
        """A .css href should be recognized and parsed."""
        tmpfile: str = self._make_temp_html('css_test.css')
        try:
            result = optimise_fonts_for_files([tmpfile], fonts=['tests/Spirax-Regular.ttf'], print_stats=False)
            expected_css: str = os.path.join(os.path.dirname(tmpfile), 'css_test.css')
            self.assertIn(expected_css, result['css'])
        finally:
            os.unlink(tmpfile)

    def test_non_css_file_not_detected(self) -> None:
        """An HTML file whose name happens to contain 'css' (not_a_css_file.html)
        should not be mistaken for a stylesheet.
        (The file exists on disk so the test fails cleanly on the assertion,
        not on a FileNotFoundError.)"""
        tmpfile: str = self._make_temp_html('not_a_css_file.html')
        try:
            result = optimise_fonts_for_files([tmpfile], fonts=['tests/Spirax-Regular.ttf'], print_stats=False)
            css_basenames: list[str] = [os.path.basename(p) for p in result['css']]
            self.assertNotIn('not_a_css_file.html', css_basenames)
        finally:
            os.unlink(tmpfile)

    def test_css_href_with_query_string(self) -> None:
        """css_test.css?v=123 should be resolved to css_test.css — the query string
        must be stripped before looking up the file."""
        tmpfile: str = self._make_temp_html('css_test.css?v=123')
        try:
            result = optimise_fonts_for_files([tmpfile], fonts=['tests/Spirax-Regular.ttf'], print_stats=False)
            css_paths: set[str] = result['css']
            for p in css_paths:
                self.assertNotIn('?', p, f"Query string not stripped from CSS path: {p}")
            css_basenames: list[str] = [os.path.basename(p) for p in css_paths]
            self.assertIn('css_test.css', css_basenames)
        except FileNotFoundError as e:
            self.fail(f"Query string was not stripped from CSS href before file access: {e}")


class TestRewriteCss(unittest.TestCase):

    def test_rewrites_mapped_font_url(self) -> None:
        """A @font-face src URL that exists in font_mapping should be replaced with the woff2 path."""
        css: str = "@font-face { font-family: 'text'; src: url('EBGaramond.ttf') format('truetype'); }"
        font_mapping: dict[str, str] = {
            '/site/fonts/EBGaramond.ttf': '/output/EBGaramond.FontimizeSubset.woff2',
        }
        output_path, rewritten = _rewrite_css('/site/fonts/style.css', css, font_mapping, '/output')
        self.assertEqual(output_path, '/output/style.css')
        self.assertIn('EBGaramond.FontimizeSubset.woff2', rewritten)
        self.assertIn("format('woff2')", rewritten.replace('"', "'"))
        self.assertNotIn('EBGaramond.ttf', rewritten)

    def test_unmapped_font_url_unchanged(self) -> None:
        """A @font-face src URL not in font_mapping should stay as-is."""
        css: str = "@font-face { font-family: 'text'; src: url('Unknown.ttf') format('truetype'); }"
        _, rewritten = _rewrite_css('/site/style.css', css, {}, '/output')
        self.assertEqual(rewritten, css)

    def test_non_font_face_css_preserved(self) -> None:
        """CSS outside @font-face blocks must not be altered, even if it contains
        invalid values like uppercase RGB() that cssutils would drop on a full round-trip."""
        css: str = (
            "body { background-color: RGB(255, 255, 255); }\n"
            "@font-face { font-family: 'text'; src: url('font.ttf') format('truetype'); }\n"
            "p { color: red; }\n"
        )
        font_mapping: dict[str, str] = {'/a/font.ttf': '/output/font.woff2'}
        _, rewritten = _rewrite_css('/a/style.css', css, font_mapping, '/output')
        # The body and p rules should be byte-for-byte identical
        self.assertIn("body { background-color: RGB(255, 255, 255); }", rewritten)
        self.assertIn("p { color: red; }", rewritten)

    def test_multiple_font_faces_only_mapped_ones_changed(self) -> None:
        """When CSS has several @font-face rules, only the ones with mapped fonts should change."""
        css: str = (
            "@font-face { font-family: 'a'; src: url('mapped.ttf') format('truetype'); }\n"
            "@font-face { font-family: 'b'; src: url('unmapped.ttf') format('truetype'); }\n"
        )
        font_mapping: dict[str, str] = {'/dir/mapped.ttf': '/output/mapped.woff2'}
        _, rewritten = _rewrite_css('/dir/style.css', css, font_mapping, '/output')
        self.assertIn('mapped.woff2', rewritten)
        # The unmapped rule should still reference the original file
        self.assertIn('unmapped.ttf', rewritten)

    def test_mixed_mapped_unmapped_urls_in_one_rule(self) -> None:
        """When a single @font-face src has both a mapped and unmapped URL,
        the unmapped URL and its format() must be preserved."""
        css: str = "@font-face { font-family: 'text'; src: url('mapped.woff2') format('woff2'), url('unmapped.ttf') format('truetype'); }"
        font_mapping: dict[str, str] = {'/dir/mapped.woff2': '/output/mapped.subset.woff2'}
        _, rewritten = _rewrite_css('/dir/style.css', css, font_mapping, '/output')
        self.assertIn('mapped.subset.woff2', rewritten)
        self.assertIn('unmapped.ttf', rewritten)
        # The unmapped URL's format must not be dropped
        self.assertIn("format", rewritten.split('unmapped.ttf')[1])

    def test_rewritten_css_key_in_result(self) -> None:
        """optimise_fonts_for_files should include 'rewritten_css' in the result."""
        result = optimise_fonts(
            "hello", ['tests/Spirax-Regular.ttf'], fontpath='tests/output', print_stats=False
        )
        self.assertIn('rewritten_css', result)
        self.assertIsInstance(result['rewritten_css'], dict)

    def test_css_rewriter_callback_called(self) -> None:
        """When css_rewriter is provided, it should be called instead of writing to disk."""
        captured: list[tuple[str, str]] = []
        def capture(path: str, content: str) -> None:
            captured.append((path, content))

        files: list[str] = ['tests/test2.html']
        result = optimise_fonts_for_files(
            files, font_output_dir='tests/output', fonts=['tests/Spirax-Regular.ttf'],
            print_stats=False, css_rewriter=capture
        )
        # test2.html references css_test.css which has @font-face rules
        if result['css']:
            self.assertGreater(len(captured), 0)
            for path, content in captured:
                self.assertTrue(path.endswith('.css'))
                self.assertIsInstance(content, str)


class TestBeartypeValidation(unittest.TestCase):
    """Test that beartype catches invalid argument types at runtime."""

    def test_get_used_characters_in_str_rejects_non_string(self) -> None:
        from beartype.roar import BeartypeCallHintParamViolation
        with self.assertRaises(BeartypeCallHintParamViolation):
            get_used_characters_in_str(123)  # type: ignore[arg-type]

    def test_get_used_characters_in_html_rejects_non_string(self) -> None:
        from beartype.roar import BeartypeCallHintParamViolation
        with self.assertRaises(BeartypeCallHintParamViolation):
            get_used_characters_in_html(None)  # type: ignore[arg-type]

    def test_optimise_fonts_rejects_non_collection_fonts(self) -> None:
        from beartype.roar import BeartypeCallHintParamViolation
        with self.assertRaises(BeartypeCallHintParamViolation):
            optimise_fonts("hello", 123)  # type: ignore[arg-type]

    def test_optimise_fonts_accepts_single_string_font(self) -> None:
        """A single font path as a string should be treated as one font, not iterated by character."""
        result = optimise_fonts("hello", "tests/Whisper-Regular.ttf", print_stats=False)
        self.assertEqual(len(result["fonts"]), 1)

    def test_optimise_fonts_for_files_rejects_non_list_files(self) -> None:
        from beartype.roar import BeartypeCallHintParamViolation
        with self.assertRaises(BeartypeCallHintParamViolation):
            optimise_fonts_for_files("not a list")  # type: ignore[arg-type]


if __name__ == '__main__':
    unittest.main()