import ttf2web
from bs4 import BeautifulSoup
from ttf2web import TTF2Web

    
def _get_unicode_string(char : chr, withU : bool = True) -> str:
    return ('U+' if withU else '') + hex(ord(char))[2:].upper().zfill(4) # eg U+1234

def get_used_characters_in_str(s : str) -> set[chr]:
    res : set[chr] = { " " } # Error when trying to add to an empty set! Space seems a fine initial value
    for c in s:
        res.add(c)
    return res

def get_used_characters_in_html(html : str) -> set[chr]:
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()
    return get_used_characters_in_str(text)

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


# Takes the input text, and the fonts, and generates new font files
# Other methods (eg taking HTML files, or multiple pieces of text) all end up here
def optimise_fonts(text : str, fonts : list[str], fontpath : str = "", verbose : bool = False) -> dict[str, str]:
    verbosity = 2 if verbose else 1 # Matching ttf2web

    characters = get_used_characters_in_str(text)

    char_list = list(characters)
    char_list.sort()
    if verbosity >= 2:
        print("Characters:")
        print(char_list)

    char_ranges = _get_char_ranges(char_list)
    if verbosity >= 2:
        print("Character ranges:")
        print(char_ranges)
    
    uranges = [['subset', ', '.join(r.get_range() for r in char_ranges)]] # name here, "subset", will be in the generated font
    if verbosity >= 2:
        print("Unicode ranges:")
        print(uranges)    

    res : dict[str, str] = {}
    # For each font, generate a new font file using only the used characters
    # By default, place it in the same folder as the respective font, unless fontpath is specified
    for font in fonts:
        assertdir = fontpath if fontpath else os.path.dirname(font)
        t2w = TTF2Web(font, uranges, assetdir='output_temp')
        woff2_list = t2w.generateWoff2(verbosity=verbosity)
        # print(woff2_list)
        assert len(woff2_list) == 1 # We only expect one font file to be generated
        res[font] = woff2_list[0][0]

    # Return a dict of input font file -> output font file, eg for CSS to be updated
    return res


def optimise_fonts_for_multiple_text(texts : list[str], fonts : list[str], fontpath : str = "", verbose : bool = False) -> dict[str, str]:
    text = ""
    for t in texts:
        text = text + t
    return optimise_fonts(text, fonts, fontpath, verbose)

def optimise_fonts_for_html(html_contents : list[str], fonts : list[str], fontpath : str = "", verbose : bool = False) -> dict[str, str]:
    text = ""
    for html in html_contents:
        soup = BeautifulSoup(html, 'html.parser')
        text = text + soup.get_text()
    return optimise_fonts(text, fonts, fontpath, verbose)


if __name__ == '__main__':
    generated = optimise_fonts("Hello world",
                               ['fonts/text/EB_Garamond/EBGaramond-VariableFont_wght.ttf', 'fonts/text/EB_Garamond/EBGaramond-Italic-VariableFont_wght.ttf'],
                               fontpath='output_temp',
                               verbose=True)
    print("Generated:")
    print(generated)

    
    # unittest.main()

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





