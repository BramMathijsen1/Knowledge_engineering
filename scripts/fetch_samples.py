"""Download "samples material" links from MusicBrainz.

Run it from the project folder: python scripts/fetch_samples.py
Output: data/raw/musicbrainz_samples.csv

We go through the recordings of artists in genres where sampling is common, and keep
a link only if the sampled artist is also in our list. MusicBrainz asks for at most
one request per second, so this takes some minutes.
"""
from common import read_csv, write_csv, ask_musicbrainz, musicbrainz_ids

SAMPLING_GENRES = ["hip_hop", "gangsta_rap", "trap", "jazz_rap", "contemporary_rnb",
                   "jungle", "drum_and_bass", "house", "techno", "electro"]
MAX_PAGES = 8
PAGE_SIZE = 100

# These names have their own MusicBrainz entries but are one artist in our list.
OTHER_NAMES = {"Parliament": "parliament_funkadelic", "Funkadelic": "parliament_funkadelic",
               "George Clinton": "parliament_funkadelic"}


def sampled_artists(relation, known):
    artists = []
    for credit in relation["recording"].get("artist-credit", []):
        artist = known.get(credit["artist"]["id"]) or OTHER_NAMES.get(credit["artist"]["name"])
        if artist:
            artists.append(artist)
    return artists


def main():
    known = musicbrainz_ids()
    chosen = {a["id"] for a in read_csv("data/curated/artists.csv") if a["primary_genre"] in SAMPLING_GENRES}
    rows = []
    seen = set()
    for musicbrainz_id, sampler in known.items():
        if sampler not in chosen:
            continue
        for page in range(MAX_PAGES):
            data = ask_musicbrainz("recording", {"artist": musicbrainz_id, "inc": "recording-rels artist-credits",
                                                 "limit": PAGE_SIZE, "offset": page * PAGE_SIZE})
            for recording in data["recordings"]:
                for relation in recording.get("relations", []):
                    if relation["type"] != "samples material" or relation["direction"] != "forward":
                        continue
                    for sampled in sampled_artists(relation, known):
                        key = (sampled, relation["recording"]["title"].lower(), sampler, recording["title"].lower())
                        if sampled == sampler or key in seen:
                            continue
                        seen.add(key)
                        rows.append({"sampled_artist": sampled, "sampled_title": relation["recording"]["title"],
                                     "sampled_id": relation["recording"]["id"], "sampling_artist": sampler,
                                     "sampling_title": recording["title"], "sampling_id": recording["id"]})
            if (page + 1) * PAGE_SIZE >= data["recording-count"]:
                break
        print(sampler, "- samples so far:", len(rows), flush=True)
    write_csv("data/raw/musicbrainz_samples.csv", rows,
              ["sampled_artist", "sampled_title", "sampled_id", "sampling_artist", "sampling_title", "sampling_id"])


main()
