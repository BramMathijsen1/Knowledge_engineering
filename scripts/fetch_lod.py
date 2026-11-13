"""Download the raw data from DBpedia, Wikidata and Wikipedia into data/raw/.

Run it from the project folder: python scripts/fetch_lod.py
It reads the genre and artist lists from data/curated/.
To fetch only the Wikidata genre dates: python scripts/fetch_lod.py genre-dates
"""
import re
import sys

from common import read_csv, write_csv, run_sparql, query_wikidata, last_part, wikipedia_text

DBPEDIA = "https://dbpedia.org/sparql"

# stylisticOrigin goes child -> parent. The other three go parent -> child.
LINEAGE_PROPERTIES = {
    "stylisticOrigin": "?child dbo:stylisticOrigin ?parent",
    "derivative": "?parent dbo:derivative ?child",
    "musicFusionGenre": "?parent dbo:musicFusionGenre ?child",
    "musicSubgenre": "?parent dbo:musicSubgenre ?child",
}

WIKIDATA_FACTS = {
    "P31": "instance of",
    "P136": "genre",
    "P569": "birth",
    "P570": "death",
    "P571": "inception",
    "P576": "dissolved",
    "P2031": "work start",
    "P2032": "work end",
    "P434": "musicbrainz",
}


def fetch_lineage(genres):
    ids = {"http://dbpedia.org/resource/" + g["dbpedia"]: g["id"] for g in genres}
    values = " ".join("<" + uri + ">" for uri in ids)
    rows = []
    for name, pattern in LINEAGE_PROPERTIES.items():
        query = f"""
        SELECT ?child ?parent WHERE {{
          VALUES ?child {{ {values} }}
          VALUES ?parent {{ {values} }}
          {pattern}
        }}"""
        for result in run_sparql(DBPEDIA, query):
            rows.append({"child": ids[result["child"]["value"]],
                         "parent": ids[result["parent"]["value"]],
                         "property": name})
    rows.sort(key=lambda r: (r["child"], r["parent"], r["property"]))
    write_csv("data/raw/dbpedia_lineage.csv", rows, ["child", "parent", "property"])
    print("DBpedia lineage rows:", len(rows))


def fetch_influences(artists):
    ids = {a["wikidata"]: a["id"] for a in artists}
    values = " ".join("wd:" + qid for qid in ids)
    query = f"""
    SELECT DISTINCT ?influenced ?influencer WHERE {{
      VALUES ?influenced {{ {values} }}
      VALUES ?influencer {{ {values} }}
      ?influenced wdt:P737 ?influencer .
    }}"""
    rows = []
    for result in query_wikidata(query):
        rows.append({"influenced": ids[last_part(result["influenced"]["value"])],
                     "influencer": ids[last_part(result["influencer"]["value"])]})
    rows.sort(key=lambda r: (r["influenced"], r["influencer"]))
    write_csv("data/raw/wikidata_influences.csv", rows, ["influenced", "influencer"])
    print("Wikidata influence rows:", len(rows))


def fetch_artist_facts(artists):
    ids = {a["wikidata"]: a["id"] for a in artists}
    values = " ".join("wd:" + qid for qid in ids)
    rows = []
    for prop, name in WIKIDATA_FACTS.items():
        query = f"""
        SELECT DISTINCT ?artist ?value WHERE {{
          VALUES ?artist {{ {values} }}
          ?artist wdt:{prop} ?value .
        }}"""
        for result in query_wikidata(query):
            rows.append({"artist": ids[last_part(result["artist"]["value"])],
                         "fact": name,
                         "value": last_part(result["value"]["value"])})
    rows.sort(key=lambda r: (r["artist"], r["fact"], r["value"]))
    write_csv("data/raw/wikidata_artist_facts.csv", rows, ["artist", "fact", "value"])
    print("Wikidata fact rows:", len(rows))


def clean_wiki_markup(text):
    text = re.sub(r"<ref.*?(</ref>|/>)", "", text)
    text = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", text)
    # A list template such as {{hlist|Mid-1980s|Oakland}} holds the value itself, so keep its items.
    text = re.sub(r"\{\{\s*(?:hlist|flatlist|ubl|unbulleted list)\s*\|([^{}]*)\}\}",
                  lambda m: ", ".join(item.strip() for item in m.group(1).split("|")), text, flags=re.I)
    text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    return text.replace("'''", "").replace("''", "").strip()


def fetch_genre_origins(genres):
    rows = []
    for genre in genres:
        text = wikipedia_text(genre["wikipedia"])
        match = re.search(r"\|\s*cultural_origins\s*=\s*(.*)", text)
        origins = clean_wiki_markup(match.group(1)) if match else ""
        rows.append({"genre": genre["id"], "cultural_origins": origins})
    write_csv("data/raw/genre_origins.csv", rows, ["genre", "cultural_origins"])
    print("Genre origin rows:", len(rows))


def fetch_genre_dates_wikidata(genres):
    """Inception (P571) and country of origin (P495) of each genre, a second source for origin claims."""
    ids = {g["wikidata"]: g["id"] for g in genres}
    values = " ".join("wd:" + qid for qid in ids)
    query = f"""
    SELECT ?genre (MIN(YEAR(?inception)) AS ?year)
           (GROUP_CONCAT(DISTINCT ?countryLabel; separator="|") AS ?countries) WHERE {{
      VALUES ?genre {{ {values} }}
      OPTIONAL {{ ?genre wdt:P571 ?inception }}
      OPTIONAL {{ ?genre wdt:P495 ?country .
                 ?country rdfs:label ?countryLabel FILTER(lang(?countryLabel) = "en") }}
    }}
    GROUP BY ?genre"""
    rows = []
    for result in query_wikidata(query):
        rows.append({"genre": ids[last_part(result["genre"]["value"])],
                     "inception_year": result.get("year", {}).get("value", ""),
                     "countries": result.get("countries", {}).get("value", "")})
    rows.sort(key=lambda r: r["genre"])
    write_csv("data/raw/wikidata_genre_origins.csv", rows, ["genre", "inception_year", "countries"])
    print("Wikidata genre origin rows:", len(rows))


def main():
    genres = read_csv("data/curated/genres.csv")
    artists = read_csv("data/curated/artists.csv")
    if sys.argv[1:] == ["genre-dates"]:
        # Only the Wikidata genre dates, so the other raw files stay as they are.
        fetch_genre_dates_wikidata(genres)
        return
    fetch_lineage(genres)
    fetch_influences(artists)
    fetch_artist_facts(artists)
    fetch_genre_origins(genres)
    fetch_genre_dates_wikidata(genres)


main()
