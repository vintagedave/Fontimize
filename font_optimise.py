import ttf2web
import FileToArticle
from bs4 import BeautifulSoup
import unittest

def get_used_characters_in_str(s : str):
    res : set[chr] = { " " }
    for c in s:
        res.add(c)
    return res

def get_used_characters(article : FileToArticle.FileToArticle):
    soup = BeautifulSoup(article.output_html, 'html.parser')
    text = soup.get_text()
    return get_used_characters_in_str(text)
    
def optimise_fonts(articles : list[FileToArticle.FileToArticle]):
    characters : set[chr] = { " " }
    for a in articles:
        characters = characters.union(get_used_characters(a))

    print("Characters!")
    print(characters)


def _get_unicode_string(char : chr) -> str:
    return 'U+' + hex(ord(char))[2:].upper().zfill(4) # eg U+1234


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
            return _get_unicode_string(self.first) + '-' + _get_unicode_string(self.second)


# Taking a sorted list of characters, find the sequential subsets and return pairs of the start and end
# of each sequential subset
def get_char_ranges(chars : list[chr]):
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
        self.assertEqual(get_char_ranges([]), [])

    def test_single_char(self):
        self.assertEqual(get_char_ranges(['a']), [charPair('a', 'a')])

    def test_two_sequential_chars(self):
        self.assertEqual(get_char_ranges(['a', 'b']), [charPair('a', 'b')])

    def test_two_nonsequential_chars(self):
        self.assertEqual(get_char_ranges(['a', 'c']), [charPair('a', 'a'), charPair('c', 'c')])

    def test_multiple_ranges(self):
        self.assertEqual(get_char_ranges(['a', 'b', 'd', 'e', 'f', 'h']), [charPair('a', 'b'), charPair('d', 'f'), charPair('h', 'h')])


    def test_get_range_with_single_char(self):
        self.assertEqual(charPair('a', 'a').get_range(), 'U+0061')

    def test_get_range_with_two_chars(self):
        self.assertEqual(charPair('a', 'b').get_range(), 'U+0061-U+0062')

    def test_get_range_with_multiple_chars(self):
        self.assertEqual(charPair('a', 'd').get_range(), 'U+0061-U+0064')




if __name__ == '__main__':
    unittest.main()

    print("Example usage:")

    characters : set[chr] = get_used_characters_in_str("Helloworld")
    characters = characters.union(get_used_characters_in_str("abcdefABCDEF"))

    char_list = list(characters)
    char_list.sort()

    char_ranges = get_char_ranges(char_list)

    print("Characters!")
    print(char_list)

    print("")
    print("Ranges!")
    print(char_ranges)

    for r in char_ranges:
        print(r.get_range())




