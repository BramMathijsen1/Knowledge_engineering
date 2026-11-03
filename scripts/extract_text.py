"""Find sentences about influence in the Wikipedia pages of our artists.

Run it from the project folder: python scripts/extract_text.py
Output: data/extracted/candidates.csv

A sentence is a candidate if it has an influence word and a link to another artist
in our list. The Wikipedia links tell us which artist is meant, so we don't need a
separate entity linking tool. Candidates are not facts yet: each one has to be
checked and the result goes into data/curated/influences_text.csv.
"""
import re

from common import read_csv, write_csv, wikipedia_text

INFLUENCE_WORDS = r"\b(influenc\w*|inspir\w*|idoli[sz]\w*|emulat\w*)\b"
LINK = r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]"
SENTENCE_END = r"(?<!Dr\.)(?<!Jr\.)(?<!Sr\.)(?<!St\.)(?<!Mr\.)(?<![A-Z]\.)(?<=[.!?])\s+(?=[A-Z\"\[])(?![^\[\]]*\]\])"
LAST_SECTIONS = ("== Discography", "== Filmography", "== Awards", "== See also", "== Notes",
                 "== References", "== Bibliography", "== External links", "== Further reading")

# Other names that Wikipedia links use for artists in our list.
OTHER_LINK_NAMES = {
    "Parliament (band)": "Parliament-Funkadelic",
    "Funkadelic": "Parliament-Funkadelic",
    "George Clinton (funk musician)": "Parliament-Funkadelic",
    "The Pixies": "Pixies (band)",
    "Ramones (band)": "Ramones",
    "2Pac": "Tupac Shakur",
    "Riley B. King": "B. B. King",
    "B.B. King": "B. B. King",
    "Chic (group)": "Chic (band)",
}


def clean_page(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<ref[^>]*/>", "", text)
    text = re.sub(r"<ref.*?</ref>", "", text, flags=re.S)
    for i in range(6):
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    text = text.replace("'''", "").replace("''", "")
    for section in LAST_SECTIONS:
        position = text.find(section)
        if position != -1:
            text = text[:position]
    return text


def page_sentences(text):
    sentences = []
    for line in clean_page(text).split("\n"):
        line = line.strip()
        if len(line) < 40 or line[0] in "=|!*#{:<":
            continue
        sentences.extend(re.split(SENTENCE_END, line))
    return sentences


def link_title(raw_title):
    title = raw_title.strip().replace("_", " ")
    title = title[0].upper() + title[1:]
    return OTHER_LINK_NAMES.get(title, title)


def plain_text(sentence):
    text = re.sub(LINK, lambda m: m.group(2) or m.group(1), sentence)
    return text.replace("&nbsp;", " ")


def main():
    artists = read_csv("data/curated/artists.csv")
    id_by_title = {a["wikipedia"]: a["id"] for a in artists}
    rows = []
    for artist in artists:
        text = wikipedia_text(artist["wikipedia"])
        url = "https://en.wikipedia.org/wiki/" + artist["wikipedia"].replace(" ", "_")
        for sentence in page_sentences(text):
            match = re.search(INFLUENCE_WORDS, plain_text(sentence), re.I)
            if not match or len(sentence) > 700:
                continue
            found = []
            for link in re.finditer(LINK, sentence):
                other = id_by_title.get(link_title(link.group(1)))
                if other and other != artist["id"] and other not in found:
                    found.append(other)
            for other in found:
                rows.append({"page_artist": artist["id"], "linked_artist": other,
                             "word": match.group(1).lower(), "sentence": plain_text(sentence),
                             "url": url})
        print(artist["name"], "- candidates so far:", len(rows), flush=True)
    write_csv("data/extracted/candidates.csv", rows,
              ["page_artist", "linked_artist", "word", "sentence", "url"])


main()
