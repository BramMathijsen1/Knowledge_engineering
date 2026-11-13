"""Build graph/graph.ttl from the curated CSV files.

Run it from the project folder: python scripts/build_graph.py
"""
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, VOID, XSD

from common import (read_csv, RIFF, GENRE, ARTIST, INFLUENCE, CLAIM, RECORDING, PHASE, INSTRUMENT,
                    ORIGIN, MM, WD, DBR, PROV)

EVIDENCE = {"Declared": RIFF.Declared, "Attributed": RIFF.Attributed, "Unsourced": RIFF.Unsourced,
            "Sampling": RIFF.Sampling, "CoverVersion": RIFF.CoverVersion}
FORMS = {"AvantGarde": RIFF.AvantGarde, "SceneBased": RIFF.SceneBased,
         "IndustryBased": RIFF.IndustryBased, "Traditionalist": RIFF.Traditionalist}
# The page or item an origin claim comes from, made from the genre's row in genres.csv.
SOURCES = {"wikipedia": lambda g: URIRef("https://en.wikipedia.org/wiki/" + g["wikipedia"].replace(" ", "_")),
           "wikidata": lambda g: WD[g["wikidata"]]}

SHORTCUT_QUERY = """
PREFIX riff: <https://w3id.org/riff/ontology#>
PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
CONSTRUCT { ?artist mm:isInfluencedBy ?other }
WHERE { ?influence riff:influenced ?artist ; riff:influencer ?other . }
"""

used_names = {}


def add_genres(graph):
    for row in read_csv("data/curated/genres.csv"):
        genre = GENRE[row["id"]]
        graph.add((genre, RDF.type, MM.MusicGenre))
        graph.add((genre, RDFS.label, Literal(row["label"], lang="en")))
        graph.add((genre, OWL.sameAs, WD[row["wikidata"]]))
        graph.add((genre, OWL.sameAs, DBR[row["dbpedia"]]))


def add_origin_claims(graph):
    """One claim per genre and source. The preferred claim also gives the genre its
    riff:emergedIn (earliest year) and riff:originPlace, which the queries use."""
    genres = {row["id"]: row for row in read_csv("data/curated/genres.csv")}
    preferred = {}
    for row in read_csv("data/curated/origin_claims.csv"):
        genre_id = row["genre"]
        if genre_id not in genres:
            raise ValueError("origin_claims.csv: unknown genre " + genre_id)
        claim = ORIGIN[genre_id + "--" + row["source"]]
        graph.add((claim, RDF.type, RIFF.OriginClaim))
        graph.add((claim, RIFF.originOf, GENRE[genre_id]))
        if row["earliest"]:
            graph.add((claim, RIFF.earliestYear, Literal(int(row["earliest"]))))
        if row["latest"]:
            graph.add((claim, RIFF.latestYear, Literal(int(row["latest"]))))
        if row["place"]:
            graph.add((claim, RIFF.claimedPlace, Literal(row["place"])))
        graph.add((claim, RIFF.sourceWording, Literal(row["wording"])))
        graph.add((claim, RIFF.isPreferred, Literal(row["preferred"] == "yes")))
        if row["note"]:
            graph.add((claim, RIFF.originNote, Literal(row["note"], lang="en")))
        graph.add((claim, PROV.wasDerivedFrom, SOURCES[row["source"]](genres[genre_id])))

        if row["preferred"] == "yes":
            if genre_id in preferred:
                raise ValueError("origin_claims.csv: more than one preferred claim for " + genre_id)
            preferred[genre_id] = row
            if row["earliest"]:
                graph.add((GENRE[genre_id], RIFF.emergedIn, Literal(int(row["earliest"]))))
            if row["place"]:
                graph.add((GENRE[genre_id], RIFF.originPlace, Literal(row["place"])))

    missing = sorted(set(genres) - set(preferred))
    if missing:
        raise ValueError("origin_claims.csv: no preferred claim for " + ", ".join(missing))


def add_lineage(graph):
    for row in read_csv("data/curated/lineage.csv"):
        if row["keep"] != "yes":
            continue
        child = GENRE[row["child"]]
        parent = GENRE[row["parent"]]
        graph.add((child, RIFF.hasStylisticOrigin, parent))
        if row["relation"] == "fusion":
            graph.add((child, RIFF.isFusionOf, parent))
        if row["relation"] == "subgenre":
            graph.add((child, SKOS.broader, parent))


def add_artists(graph):
    for row in read_csv("data/curated/artists.csv"):
        artist = ARTIST[row["id"]]
        graph.add((artist, RDF.type, MM.MusicArtist))
        graph.add((artist, RDF.type, MM.Musician if row["kind"] == "person" else MM.MusicEnsenble))
        graph.add((artist, RDFS.label, Literal(row["name"], lang="en")))
        graph.add((artist, OWL.sameAs, WD[row["wikidata"]]))
        graph.add((artist, RIFF.hasPrimaryGenre, GENRE[row["primary_genre"]]))
        graph.add((artist, MM.hasGenre, GENRE[row["primary_genre"]]))
        for other in row["other_genres"].split():
            graph.add((artist, MM.hasGenre, GENRE[other]))
        if row["active_from"]:
            graph.add((artist, RIFF.activeFrom, Literal(int(row["active_from"]))))
        if row["active_to"]:
            graph.add((artist, RIFF.activeTo, Literal(int(row["active_to"]))))


def add_phases(graph):
    for row in read_csv("data/curated/genre_phases.csv"):
        phase = PHASE[row["genre"] + "_" + row["order"]]
        graph.add((phase, RDF.type, RIFF.GenrePhase))
        graph.add((phase, RIFF.phaseOf, GENRE[row["genre"]]))
        graph.add((phase, RIFF.hasForm, FORMS[row["form"]]))
        graph.add((phase, RIFF.phaseOrder, Literal(int(row["order"]))))
        graph.add((phase, PROV.wasDerivedFrom, URIRef(row["source"])))


def add_recordings(graph):
    for row in read_csv("data/curated/recordings.csv"):
        recording = RECORDING[row["id"]]
        graph.add((recording, RDF.type, MM.Recording))
        graph.add((recording, RDFS.label, Literal(row["title"], lang="en")))
        graph.add((recording, DCTERMS.creator, ARTIST[row["artist"]]))
        graph.add((recording, RDFS.seeAlso, URIRef(row["url"])))


def add_instruments(graph):
    for row in read_csv("data/curated/instruments.csv"):
        instrument = INSTRUMENT[row["id"]]
        graph.add((instrument, RDF.type, RIFF.Instrument))
        graph.add((instrument, RDFS.label, Literal(row["label"], lang="en")))
        graph.add((instrument, RIFF.inInstrumentGroup, RIFF[row["group"]]))
        if row["wikidata"]:
            graph.add((instrument, OWL.sameAs, WD[row["wikidata"]]))
    for row in read_csv("data/curated/artist_instruments.csv"):
        if row["keep"] == "yes":
            graph.add((ARTIST[row["artist"]], RIFF.playsInstrument, INSTRUMENT[row["instrument"]]))


def add_influence(graph, row, evidence, source):
    pair = row["influenced"] + "--" + row["influencer"]
    influence = INFLUENCE[pair]
    graph.add((influence, RDF.type, RIFF.Influence))
    graph.add((influence, RIFF.influenced, ARTIST[row["influenced"]]))
    graph.add((influence, RIFF.influencer, ARTIST[row["influencer"]]))
    if row.get("date_note"):
        graph.add((influence, RIFF.dateNote, Literal(row["date_note"], lang="en")))

    name = pair + "--" + evidence.lower()
    used_names[name] = used_names.get(name, 0) + 1
    if used_names[name] > 1:
        name += "--" + str(used_names[name])
    claim = CLAIM[name]
    graph.add((claim, RDF.type, RIFF.InfluenceClaim))
    graph.add((claim, RIFF.describes, influence))
    graph.add((claim, RIFF.hasEvidenceKind, EVIDENCE[evidence]))
    graph.add((claim, PROV.wasDerivedFrom, source))
    if row.get("sentence"):
        graph.add((claim, RIFF.evidenceQuote, Literal(row["sentence"], lang="en")))
    if row.get("via_recording"):
        graph.add((claim, RIFF.viaRecording, RECORDING[row["via_recording"]]))
    if row.get("in_recording"):
        graph.add((claim, RIFF.inRecording, RECORDING[row["in_recording"]]))


def add_influences(graph):
    wikidata_ids = {row["id"]: row["wikidata"] for row in read_csv("data/curated/artists.csv")}
    for row in read_csv("data/curated/influences_wikidata.csv"):
        if row["keep"] == "yes":
            add_influence(graph, row, "Unsourced", WD[wikidata_ids[row["influenced"]]])
    for row in read_csv("data/curated/influences_text.csv"):
        if row["keep"] == "yes":
            add_influence(graph, row, row["evidence"], URIRef(row["url"]))
    for row in read_csv("data/curated/influences_recordings.csv"):
        add_influence(graph, row, row["evidence"], URIRef(row["url"]))


def add_dataset_info(graph):
    dataset = URIRef("https://w3id.org/riff/graph")
    graph.add((dataset, RDF.type, VOID.Dataset))
    graph.add((dataset, DCTERMS.title, Literal("RIFF knowledge graph", lang="en")))
    graph.add((dataset, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by-sa/4.0/")))
    for source in ["https://www.wikidata.org/", "https://www.dbpedia.org/",
                   "https://en.wikipedia.org/", "https://musicbrainz.org/"]:
        graph.add((dataset, DCTERMS.source, URIRef(source)))


def main():
    graph = Graph()
    graph.bind("riff", RIFF)
    graph.bind("genre", GENRE)
    graph.bind("artist", ARTIST)
    graph.bind("influence", INFLUENCE)
    graph.bind("claim", CLAIM)
    graph.bind("recording", RECORDING)
    graph.bind("phase", PHASE)
    graph.bind("instrument", INSTRUMENT)
    graph.bind("origin", ORIGIN)
    graph.bind("mm", MM)
    graph.bind("wd", WD)
    graph.bind("dbr", DBR)
    graph.bind("prov", PROV)

    add_genres(graph)
    add_origin_claims(graph)
    add_lineage(graph)
    add_artists(graph)
    add_phases(graph)
    add_recordings(graph)
    add_instruments(graph)
    add_influences(graph)
    add_dataset_info(graph)

    for triple in graph.query(SHORTCUT_QUERY):
        graph.add(triple)

    graph.serialize("graph/graph.ttl", format="turtle")
    print("graph/graph.ttl written with", len(graph), "triples")


main()
