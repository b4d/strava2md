"""
Page2HTML

Test/preview HTML renderer for Strava2.md generated files
Forked and adapted from md-to-html, TL;DR to allow usage of Hugo's "rawhtml" tags in Markdowns
Uses Mistune library markdown parser (C) 2014, Hsiaoming Yang)

Strava2.md:
https://github.com/b4d/strava2md

md-to-html:
https://github.com/AumitLeon/markdown_html_converter/blob/master/README.md

mistune:
https://github.com/lepture/mistune/blob/main/LICENSE

Original md-to-html header follows:

---

@author Aumit Leon
Convert Markdown documents to HTML
Uses the mistune library markdown parser: https://github.com/lepture/mistune (Copyright (c) 2014, Hsiaoming Yang)
License information for use of mistune library: https://github.com/lepture/mistune/blob/master/LICENSE
"""

import argparse
import mistune
from bs4 import BeautifulSoup as bs

def main():
    # Collect arguments
    parser = argparse.ArgumentParser(description="Convert Markdown File to HTML file")
    parser.add_argument(
        "--input", "-i", type=str, required=True, help="input markdown file"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="converted.html", help="output HTML file"
    )

    args = parser.parse_args()
    convert(args.output, args.input)

def convert(output, input):
    html_doc = open(output, "w", encoding="utf-8")
    generated_html = (
        "<!DOCTYPE html>"
        + "<!--Converted via md-to-html for-->"
        + "<html><head></head><body>"
    )

    with open(input, encoding="utf-8") as f:
        content = f.readlines()
        noescape = False
        for line in content:
            if line == "{{< rawhtml >}}\n":
                noescape = True
                continue
            if line == "{{< /rawhtml >}}\n":
                noescape = False
                continue

            if noescape:
                generated_html += line
            else:
                generated_html += mistune.markdown(line)

    generated_html += "</body></html>"

    # make BeautifulSoup
    soup = bs(generated_html, "html.parser")
    # prettify the html
    prettyHTML = soup.prettify()
    # write to the html doc
    html_doc.write(prettyHTML)


if __name__ == "__main__":
    main()