import csv
import os
import time

import requests
from rdflib import Namespace

RIFF = Namespace("https://w3id.org/riff/ontology#")
GENRE = Namespace("https://w3id.org/riff/genre/")
ARTIST = Namespace("https://w3id.org/riff/artist/")
INFLUENCE = Namespace("https://w3id.org/riff/influence/")
RECORDING = Namespace("https://w3id.org/riff/recording/")
PHASE = Namespace("https://w3id.org/riff/phase/")
ROUTE = Namespace("https://w3id.org/riff/route/")
INSTRUMENT = Namespace("https://w3id.org/riff/instrument/")
MM =Namespace("https://w3id.org/polifonia/ontology/music-meta/")
WD = Namespace("http://www.wikidata.org/entity/")
DBR = Namespace("http://dbpedia.org/resource/")
PROV = Namespace("http://www.w3.org/ns/prov#")

HEADERS = {"User-Agent": "riff-music-kg/1.0 (university course project)"}
CACHE_FOLDER = "data/raw/wikipedia_cache"

# The official Wikidata endpoint is sometimes limited, so QLever is the second choice.
WIKIDATA_ENDPOINTS = ["https://query.wikidata.org/sparql", "https://qlever.dev/api/wikidata"]
WD_PREFIXES = """
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run_sparql(endpoint, query):
    headers = dict(HEADERS)
    headers["Accept"] = "application/sparql-results+json"
    response = requests.post(endpoint, data={"query": query}, headers=headers, timeout=180)
    response.raise_for_status()
    return response.json()["results"]["bindings"]


def query_wikidata(query):
    for endpoint in WIKIDATA_ENDPOINTS:
        try:
            return run_sparql(endpoint, WD_PREFIXES + query)
        except Exception as error:
            print("Problem with", endpoint, ":", error)
    raise RuntimeError("No Wikidata endpoint worked")


def last_part(uri):
    return uri.rsplit("/", 1)[-1]


def ask_musicbrainz(path, params):
    """Ask the MusicBrainz API. It allows about one request per second."""
    params["fmt"] = "json"
    headers = dict(HEADERS)
    headers["Accept"] = "application/json"
    while True:
        response = requests.get("https://musicbrainz.org/ws/2/" + path, params=params,
                                headers=headers, timeout=60)
        if response.status_code == 503:
            print("MusicBrainz asked us to slow down, waiting 15 seconds", flush=True)
            time.sleep(15)
            continue
        response.raise_for_status()
        time.sleep(1.2)
        return response.json()


def musicbrainz_ids():
    """MusicBrainz artist id -> our artist id, from the Wikidata facts."""
    ids = {}
    for fact in read_csv("data/raw/wikidata_artist_facts.csv"):
        if fact["fact"] == "musicbrainz":
            ids[fact["value"]] = fact["artist"]
    return ids


def wikipedia_text(title):
    """Return the wikitext of a Wikipedia page. Pages are saved so we only download them once."""
    os.makedirs(CACHE_FOLDER, exist_ok=True)
    file_name = "".join(c if c.isalnum() else "_" for c in title) + ".txt"
    path = os.path.join(CACHE_FOLDER, file_name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    params = {"action": "parse", "page": title, "prop": "wikitext", "format": "json",
              "formatversion": 2, "redirects": 1}
    while True:
        response = requests.get("https://en.wikipedia.org/w/api.php", params=params,
                                headers=HEADERS, timeout=60)
        if response.status_code == 429:
            print("Wikipedia asked us to slow down, waiting 60 seconds")
            time.sleep(60)
            continue
        response.raise_for_status()
        break

    text = response.json()["parse"]["wikitext"]
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    time.sleep(2)
    return text
