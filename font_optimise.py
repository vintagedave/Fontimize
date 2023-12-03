import ttf2web
import FileToArticle
from bs4 import BeautifulSoup
import unittest
from ttf2web import TTF2Web

    
def _get_unicode_string(char : chr, withU : bool = True) -> str:
    return ('U+' if withU else '') + hex(ord(char))[2:].upper().zfill(4) # eg U+1234

def get_used_characters_in_html(html : str):
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return get_used_characters_in_str(text)

def get_used_characters_in_str(s : str):
    res : set[chr] = { " " } # Error when trying to add to an empty set! Space seems a fine initial value
    for c in s:
        res.add(c)
    return res

def _get_used_characters(article : FileToArticle.FileToArticle):
    return get_used_characters_in_html(article.output_html)

def optimise_fonts(articles : list[FileToArticle.FileToArticle]):
    characters : set[chr] = { " " }
    for a in articles:
        characters = characters.union(_get_used_characters(a))

    print("Characters!")
    print(characters)

class charPair:
    def __init__(self, first : chr, second : chr):
        self.first = first
        self.second = second

    def __str__(self):
        return "[" + self.first + "-" + self.second + "]" # Pairs are inclusive
    
    # For print()-ing
    def __repr__(self):
        return self.__str__()
    
    def __eq__(self, other):
        if isinstance(other, charPair):
            return self.first == other.first and self.second == other.second
        return False
    
    def get_range(self):
        if self.first == self.second:
            return _get_unicode_string(self.first)
        else:
            return _get_unicode_string(self.first) + '-' + _get_unicode_string(self.second, False)


# Taking a sorted list of characters, find the sequential subsets and return pairs of the start and end
# of each sequential subset
def _get_char_ranges(chars : list[chr]):
    if not chars:
        return []
    res : list[charPair] = []
    first : chr = chars[0]
    prev_seen : chr = first
    for c in chars[1:]:
        expected_next_char = chr(ord(prev_seen) + 1)
        if c != expected_next_char:
            # non-sequential, so time to start a new set
            pair = charPair(first, prev_seen)
            res.append(pair)
            first = c
        prev_seen = c
    # add final set if it hasn't been added yet
    if (not res) or (res[-1].second != prev_seen):
        pair = charPair(first, prev_seen)
        res.append(pair)

    return res


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

class TestCharPairs(unittest.TestCase):
    def test_get_range_with_single_char(self):
        self.assertEqual(charPair('a', 'a').get_range(), 'U+0061')

    # Note that the second of the pair does not have the "U+" -- this caught me out
    # with parse errors inside TTF2Web()
    def test_get_range_with_two_chars(self):
        self.assertEqual(charPair('a', 'b').get_range(), 'U+0061-0062')

    def test_get_range_with_multiple_chars(self):
        self.assertEqual(charPair('a', 'd').get_range(), 'U+0061-0064')


if __name__ == '__main__':
    unittest.main()

    # print("Example usage:")

    # characters : set[chr] = get_used_characters_in_str("Helloworld")
    # characters = characters.union(get_used_characters_in_str("abcdefABCDEF.Z?<>,...+="))

    # char_list = list(characters)
    # char_list.sort()

    # char_ranges = _get_char_ranges(char_list)

    # print("Characters!")
    # print(char_list)

    # print("")
    # print("Ranges!")
    # print(char_ranges)

    # for r in char_ranges:
    #     print(r.get_range())

    # print("uranges")
    # uranges = [['subset', ', '.join(r.get_range() for r in char_ranges)]] # name here, "subset", will be in the generated font
    # print(uranges)

    # verbose = 2
    # fonts : list[str] = ['fonts/text/EB_Garamond/EBGaramond-VariableFont_wght.ttf', 'fonts/text/EB_Garamond/EBGaramond-Italic-VariableFont_wght.ttf']
    # for fontfile in fonts:
    #     verbosity = 2 if verbose else 1

    #     t2w = TTF2Web(fontfile, uranges, assetdir='output_temp')
    #     woff2_list = t2w.generateWoff2(verbosity=verbosity)
    #     #t2w.generateCss(woff2_list, verbosity=verbosity)





