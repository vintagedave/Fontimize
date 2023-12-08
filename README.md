# Fontimize

Easily optimize (subset) fonts to only the specific glyphs needed for your text or HTML!

Are you worried about the initial download size of your website? Requiring megabytes of downloads, and you've optimised and minified your CSS and Javascript and images, but spotted some large fonts? Fontimize is for you! This tool analyses your HTML files and CSS (or any text) and creates *font subsets*, font files that contain only the characters or glyphs that are actually used.

In practice you can shrink your font download size to 10% or less of the original.

Fontimize uses [TTF2Web](https://github.com/johncf/ttf2web), and many thanks and credit to the author of that fantastic library.

## Example Results

This library was originally created for my [personal website](https://daveon.design). It used four TTF fonts totalling just over 1.5MB. (This is not unusual: one for headings, one for the normal text with a variant for italic, plus a fourth for a typographical quirk, dropcaps.)

After running Fontimize, the total size for *all fonts combined* is 76KB.

1.5MB down to 76KB is a saving of 95.2%! This had noticeable impact on the initial time to download a page on the site, plus immense impact on the rendering: before, the site would render with generic serif fonts, and then re-render a few seconds later once the fonts had downloaded, which looked really bad. Now, you will get the new fonts immediately or before you notice and the site will look correct from the start.

# Usage

Fontimize is a Python library, and can be included in your Python software or used stand-alone on the command line. I myself use it as part of a custom static site generator to build my site: it runs as the final step, optimizing fonts based on the generated on-disk HTML files, and I use the return values (what fonts it created, and what CSS files it analysed) to rewrite the CSS to point at the new fonts.

(Rewriting CSS is not currently a feature provided by Fontimizer; please [create an issue](https://github.com/vintagedave/Fontimize/issues) or pull request if you'd like it to be. At the current time, the library will generate new files (new fonts) and return a map (dict or text output) of the old to new fonts, ie what to replace, but will not rewrite existing files.)

## Library

Begin by installing and importing Fontimize:

```
$ python3 -m pip install fontimize
```

In your script:

```
import fontimize
```

To parse a set of HTML files on disk, and the CSS files they use, and export new fonts (by default in the same folder as the original fonts) containing only the glyphs used in the HTML: 

```
all_html_files = [ 'input/one.html', 'input/two.html' ]

font_results = fontimize.optimise_fonts_for_html_files(all_html_files, verbose=False)
css_files = font_results["css"]
replacement_fonts_dict = font_results["fonts"]

print(css_files)
# Prints CSS files found used by any of the HTML input files:
#   input/main.css
#   input/secondary.css

print(replacement_fonts_dict)
# Prints pairs of the old fonts to the new optimised font generated for it. Use this to, eg, rewrite your CSS
#  [ 'input/fonts/Arial.ttf', 'input/fonts/Arial.FontimizeSubset.woff2' ]
#  [ 'input/fonts/EB Garamond.ttf', 'input/fonts/EB Garamond.FontimizeSubset.woff2' ]
```

### Full reference

#### `optimise_fonts_for_html_files()`

This is likely the method you want to use.

Optimises / subsets fonts based on a set of input HTML files on disk, and the external CSS files that those HTML files reference. Returns the list of found CSS files and a map of the old to new optimised font files.

Parameters:

* `html_files : list[str]`: list of paths, each of which is a HTML file. Each one will be analyzed.
* `font_output_dir = ""`: path to where the subsetted fonts should be placed. By default this is empty (`""`), which means to generate the new fonts in the same location as the input fonts. Because the new fonts have a different name (see `subsetname`, the next parameter) you will not overwrite the input fonts. There is no checking if subset fonts already exist before they are written, though.
* `subsetname = "FontimizeSubset"`: The optimised fonts are renamed in the format `OriginalName.FontimizeSubset.woff2`. It's important to differentiate the subsetted fonts from the original fonts with all glyphs. You can change the output subset name to any other string that's valid on your file system.
* `verbose : bool = False`: If `True`, emits diagnostic information about the CSS files, fonts, etc that it's found and is generating. 
* `print_stats : bool = True`: prints information for the total size on disk of the input fonts, and the total size of the optimized fonts, and the savings in percent. Set this to `False` if you want it to run silently.

Returns:
* `dict[str, typing.Any]`
* `return_value["css"]` -> list of unique CSS files that the HTML files use
* `return_value["fonts"]` -> a `dict` where `keys()` are the original font files, and the value for each key is the replacement font file that was generated. You can use this to update references to the original font files. Note that Fontimizer does not rewrite the input CSS.

### `optimise_fonts_for_html_contents()`

Similar to `optimise_fonts_for_html_files`, except the input is HTML as a string (eg `<head>...</head><body>...<body>`). It does not parse to find the CSS files used (and thus fonts used), so you need to also give it a list of font files to optimize.

Parameters:
* `html_contents : list[str]`: list of HTML strings. The text will be extracted and used to generate the list of glyphs for the optimised fonts.
* `fonts : list[str]`: list of paths on your local file system to font files to optimise. These can be relative paths.

Other parameters (`fontpath`, `subsetname`, `verbose`, `print_stats`) are identical to `optimise_fonts_for_html_files`.

Returns:
* a `dict` where `keys()` are the original font files, and the value for each key is the replacement font file that was generated

### `optimise_fonts_for_multiple_text()`

Similar to `optimise_fonts_for_html_contents`, except the input is a list of Python strings. The contents of those strings are used to generate the glyphs for the optimised fonts.

Pass in a list of font files (`fonts` parameter) as the input font files to optimise based on the text.

Parameters:
* `texts : list[str]`: list of Python strings. The generated fonts will contain the glyphs that these strings use.

Other parameters (`fonts`, `fontpath`, `subsetname`, `verbose`, `print_stats`) and the return value are idential to `optimise_fonts_for_html_contents`.

### `optimise_fonts()`

This is the main method; all the methods above end up here. It takes a Python Unicode string of text and a list of paths to font files to optimise, and using the input text it creates font subsets containing only the unique glyphs required for the input text.

Parameters:
* `text: str`: a Python Unicode string. A set of unique Unicode characters is generated from this, and the output font files will contain all glyphs required to render this string correctly (assuming the fonts contained the glyphs to begin with.) 

Other parameters (`fonts`, `fontpath`, `subsetname`, `verbose`, `print_stats`) and the return value are identical to `optimise_fonts_for_html_contents` and `optimise_fonts_for_multiple_text`.

## Command line


## Tests

Unit tests are run via `tests.py` and use the files in `tests\`. Note that this generates new output files within the `tests\output` folder.

The `tests` folder contains several fonts that are licensed under the SIL Open Font License.

# Notes

* By default, the new subset fonts will have a name containing 'FontimizerSubset', eg `Arial.FontimizerSubset.woff2`. You can customise this through the `subsetname` method parameter or `--subsetname=Foo` commandline parameter. You can change it to whatever you want, but it is strongly recommended to use a subset name, in order to not mistake the optimized subsetted font for the original containing all glyphs. The use of `FontimizeSubset` by default is to hopefully point anyone who spots it back to this library, so they can use it too. There is no need to retain it and you can use any phrase you wish.
* CSS pseudo-elements: yes, Fontimize parses CSS not just for the fonts that are used, but for glyphs that are presented onscreen. If you use `:before` or `:after`, the text / characters in those pseudo-elements are added to the characters emitted in the optimised fonts.
* Inline CSS: no, Fontimizer does not currently parse inline CSS in a HTML file. It assumes you're using external CSS and finds those from your `style` links in the `<head>` and parses those for fonts etc. If this would be useful to you please [raise an issue](https://github.com/vintagedave/Fontimize/issues).
* It's really nice (but not required) that if you use Fontimizer, to link to daveondesign/fontimizer.html or this github repo. That's to point other people to the tool. Many thanks :)


