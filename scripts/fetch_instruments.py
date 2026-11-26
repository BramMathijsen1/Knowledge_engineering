"""Download which instruments our artists play.

Run it from the project folder: python scripts/fetch_instruments.py
Output: data/raw/instruments_raw.csv and data/raw/wikidata_instrument_codes.csv

Solo artists: Wikidata, property P1303 "instrument".
Bands: MusicBrainz. Its "member of band" links say which instruments each member played
in that band. Touring and session members ("additional") are left out.
Wikidata only has the instruments a member played in their whole career, which is less
exact. We use it for bands where MusicBrainz gives no instruments, and for the members
that MusicBrainz lists with no instruments. MusicBrainz often gives instruments only for
some members of a band (for The Clash only a late guitarist), so without this the main
members would be missing.
"""
from common import read_csv, write_csv, query_wikidata, last_part, ask_musicbrainz, musicbrainz_ids

# MusicBrainz puts these words next to the instruments. They are not instruments.
NOT_INSTRUMENTS = {"original", "founder", "additional", "minor", "guest", "emeritus"}


def same_name(name):
    # MusicBrainz and Wikidata write some names with different hyphens or capitals.
    return name.replace("‐", "-").lower()


def solo_artist_instruments(artists):
    ids = {a["wikidata"]: a["id"] for a in artists if a["kind"] == "person"}
    values = " ".join("wd:" + qid for qid in ids)
    query = f"""
    SELECT DISTINCT ?artist ?instrument ?instrumentLabel WHERE {{
      VALUES ?artist {{ {values} }}
      ?artist wdt:P1303 ?instrument .
      OPTIONAL {{ ?instrument rdfs:label ?instrumentLabel . FILTER(LANG(?instrumentLabel) = "en") }}
    }}"""
    rows = []
    for result in query_wikidata(query):
        label = result["instrumentLabel"]["value"] if "instrumentLabel" in result else ""
        rows.append({"artist": ids[last_part(result["artist"]["value"])], "source": "wikidata", "member": "",
                     "instrument": label.lower(), "wikidata_item": last_part(result["instrument"]["value"])})
    return rows


def band_instruments(artists):
    bands = {a["id"] for a in artists if a["kind"] == "group"}
    rows = []
    for musicbrainz_id, artist in musicbrainz_ids().items():
        if artist not in bands:
            continue
        data = ask_musicbrainz("artist/" + musicbrainz_id, {"inc": "artist-rels"})
        for relation in data.get("relations", []):
            if relation["type"] != "member of band" or relation["direction"] != "backward":
                continue
            attributes = relation.get("attributes", [])
            if "additional" in attributes:
                continue
            for attribute in attributes:
                if attribute not in NOT_INSTRUMENTS:
                    rows.append({"artist": artist, "source": "musicbrainz", "member": relation["artist"]["name"],
                                 "instrument": attribute.lower(), "wikidata_item": ""})
        print(artist, "- rows so far:", len(rows), flush=True)
    return rows


def member_instruments(artists, bands):
    ids = {a["wikidata"]: a["id"] for a in artists if a["id"] in bands}
    values = " ".join("wd:" + qid for qid in ids)
    query = f"""
    SELECT DISTINCT ?artist ?member ?memberLabel ?instrument ?instrumentLabel WHERE {{
      VALUES ?artist {{ {values} }}
      {{ ?artist wdt:P527 ?member }} UNION {{ ?member wdt:P463 ?artist }}
      ?member wdt:P1303 ?instrument .
      OPTIONAL {{ ?member rdfs:label ?memberLabel . FILTER(LANG(?memberLabel) = "en") }}
      OPTIONAL {{ ?instrument rdfs:label ?instrumentLabel . FILTER(LANG(?instrumentLabel) = "en") }}
    }}"""
    rows = []
    for result in query_wikidata(query):
        member = result["memberLabel"]["value"] if "memberLabel" in result else ""
        label = result["instrumentLabel"]["value"] if "instrumentLabel" in result else ""
        rows.append({"artist": ids[last_part(result["artist"]["value"])], "source": "wikidata members",
                     "member": member, "instrument": label.lower(),
                     "wikidata_item": last_part(result["instrument"]["value"])})
    return rows


def instrument_codes(rows):
    # Wikidata gives many instruments a Hornbostel-Sachs code (P1762). We keep it to check our groups.
    items = " ".join("wd:" + qid for qid in sorted({r["wikidata_item"] for r in rows if r["wikidata_item"]}))
    query = f"""
    SELECT DISTINCT ?instrument ?code WHERE {{
      VALUES ?instrument {{ {items} }}
      ?instrument wdt:P1762 ?code .
    }}"""
    codes = [{"wikidata_item": last_part(r["instrument"]["value"]), "hornbostel_sachs": r["code"]["value"]}
             for r in query_wikidata(query)]
    codes.sort(key=lambda r: (r["wikidata_item"], r["hornbostel_sachs"]))
    return codes


def main():
    artists = read_csv("data/curated/artists.csv")
    rows = solo_artist_instruments(artists) + band_instruments(artists)
    bands = {a["id"] for a in artists if a["kind"] == "group"}
    missing = bands - {r["artist"] for r in rows if r["instrument"] not in ("lead vocals", "background vocals", "vocals")}
    print("Bands with no instruments in MusicBrainz:", len(missing))
    # Members that MusicBrainz already gives instruments for, in each band.
    covered = {(r["artist"], same_name(r["member"])) for r in rows if r["source"] == "musicbrainz"}
    added = 0
    for row in member_instruments(artists, bands):
        if row["artist"] in missing or (row["artist"], same_name(row["member"])) not in covered:
            rows.append(row)
            added += 1
    print("Rows from Wikidata for members MusicBrainz leaves out:", added)
    rows.sort(key=lambda r: (r["artist"], r["instrument"], r["member"]))
    write_csv("data/raw/instruments_raw.csv", rows, ["artist", "source", "member", "instrument", "wikidata_item"])
    print("Instrument rows:", len(rows))
    codes = instrument_codes(rows)
    write_csv("data/raw/wikidata_instrument_codes.csv", codes, ["wikidata_item", "hornbostel_sachs"])
    print("Instrument code rows:", len(codes))


main()
