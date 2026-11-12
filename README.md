# RIFF: a knowledge graph of music genres and influence

RIFF stands for Roots, Influence, Forms, Fusion. It is a project for the course
Knowledge Representation and Extraction at the University of Bologna.

## The question

Everyone knows the family tree of popular music: blues leads to rock and roll, rock and roll
leads to rock, and so on. But do the influences between artists really follow that tree?

RIFF puts two things in one graph, so we can compare them with SPARQL:

- **Genres and where they come from.** These come from DBpedia.
- **Artists and who influenced them.** These come from Wikidata, Wikipedia text and MusicBrainz.

When we add up artist influence by genre, each genre-to-genre route gets one of these labels:

| Label | Meaning |
|---|---|
| direct | The tree has this link |
| two-step | The tree has this link through one genre in between |
| reversed | The tree has the link, but in the other direction |
| hidden | The tree has no link between these genres |

A separate query lists the opposite case: links in the tree with no artists behind them.

## A second question: instruments

Do genres and influences shape which instruments artists play? The graph also says which
instruments each artist plays (from Wikidata and MusicBrainz). Queries 15 to 17 add these up by
genre. They ask which instruments a genre adds to the ones its roots use, and whether artists play
the same instruments as the artists who influenced them.

## What is in this folder

| Folder | Contents |
|---|---|
| `ontology/` | The ontology (`riff.ttl`) and its diagram (`riff_diagram.svg`) |
| `data/raw/` | Data as downloaded |
| `data/extracted/` | Candidate sentences found in Wikipedia |
| `data/curated/` | Cleaned tables. The graph is built from these |
| `graph/` | The knowledge graph (`graph.ttl`) and the genre routes (`routes.ttl`) |
| `queries/` | The SPARQL queries |
| `results/` | Answers to the queries |
| `scripts/` | The Python scripts |
| `docs/` | The web pages |

## How to run it

You need Python and two packages:

```
pip install -r requirements.txt
```

Everything needed is saved in the project, so these three steps work without internet.
Run them from the project folder:

```
python scripts/build_graph.py
python scripts/run_queries.py
python scripts/build_site.py
```

The first one builds the graph from the tables in `data/curated/`. The second one runs all the
queries and saves the answers in `results/`. The third one writes the web pages. To see
them, open `docs/index.html`.

To download the data again (this takes a while):

```
python scripts/fetch_lod.py
python scripts/extract_text.py
python scripts/fetch_samples.py
python scripts/fetch_instruments.py
```

These scripts only write to `data/raw/` and `data/extracted/`. They never change the curated tables.

## The curated tables

| File | Contents |
|---|---|
| `genres.csv` | The genres, with a rough year and place |
| `lineage.csv` | Links between genres. Dropped links stay here with the reason |
| `artists.csv` | The artists, with one primary genre each |
| `genre_phases.csv` | Forms of genres, from Lena and Peterson |
| `influences_wikidata.csv` | Influence pairs from Wikidata |
| `influences_text.csv` | Candidate sentences from Wikipedia, with the decision for each |
| `influences_recordings.csv` | Samples and cover versions |
| `recordings.csv` | The recordings used in samples and covers |
| `instruments.csv` | Our list of instruments, each in one instrument group |
| `artist_instruments.csv` | Which instruments each artist plays, and where this comes from |

Each row has a `status` column. It says `draft` until someone on the team has checked the row, then
`checked`. `run_queries.py` prints how many rows are still drafts.

## Querying the graph

The queries run with rdflib, so no server is needed. To use a SPARQL endpoint, load
`ontology/riff.ttl` and `graph/graph.ttl` into
[Apache Jena Fuseki](https://jena.apache.org/documentation/fuseki2/) on your computer.

## Namespace

The files use `https://w3id.org/riff/`. This address still has to be registered with
[w3id.org](https://w3id.org/), so the links don't work yet.

## Licence

Ontology and data: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), see `LICENSE`.
We use this licence because Music Meta, DBpedia and Wikipedia are also share-alike.

Sources: [DBpedia](https://www.dbpedia.org/), [Wikidata](https://www.wikidata.org/),
[Wikipedia](https://en.wikipedia.org/), [MusicBrainz](https://musicbrainz.org/),
[Music Meta](https://w3id.org/polifonia/ontology/music-meta/).

## Team

Bram, Tarek, Eddy
