"""Build the web pages in docs/ from the ontology, the queries and the results.

Run it from the project folder, after run_queries.py: python scripts/build_site.py
"""
import csv
import glob
import html
import os
import shutil

from rdflib import Graph
from rdflib.namespace import OWL, RDF, RDFS

MENU = [("index.html", "Home"), ("ontology.html", "Ontology"),
        ("queries.html", "Queries"), ("method.html", "Method")]
MAX_ROWS = 15


def make_page(file_name, title, body):
    links = "".join(f'<a href="{link}">{text}</a>' for link, text in MENU)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | RIFF</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header><span class="name">RIFF</span><nav>{links}</nav></header>
<main>
{body}
</main>
<footer>RIFF: Roots, Influence, Forms, Fusion. Data and ontology under
<a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>.</footer>
</body>
</html>
"""
    with open("docs/" + file_name, "w", encoding="utf-8") as f:
        f.write(page)


def result_rows(name):
    path = "results/" + name + ".csv"
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.reader(f))


def html_table(rows, limit=None):
    header, body = rows[0], rows[1:]
    if limit:
        body = body[:limit]
    text = "<table><tr>" + "".join(f"<th>{html.escape(cell)}</th>" for cell in header) + "</tr>"
    for row in body:
        text += "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
    return text + "</table>"


def count_in_graph(graph, query):
    prefixes = """
    PREFIX riff: <https://w3id.org/riff/ontology#>
    PREFIX mm: <https://w3id.org/polifonia/ontology/music-meta/>
    """
    for row in graph.query(prefixes + query):
        return int(row[0])
    return 0


def percent(part, whole):
    return round(100 * part / whole) if whole else 0


def route_numbers():
    numbers = {}
    for status, routes, pairs in result_rows("10_route_summary")[1:]:
        numbers[status] = int(pairs)
    return numbers


def build_home(graph):
    numbers = route_numbers()
    total = sum(numbers.values())
    follow = numbers.get("direct", 0) + numbers.get("two-step", 0)
    against = numbers.get("reversed", 0)
    hidden = numbers.get("hidden", 0)
    routes = result_rows("10b_route_list")
    hidden_routes = [routes[0]] + [row for row in routes[1:] if row[3] == "hidden"]
    no_artists = result_rows("11_links_without_artists")
    genres = count_in_graph(graph, "SELECT (COUNT(DISTINCT ?g) AS ?n) WHERE { ?g a mm:MusicGenre }")
    origin_claims = count_in_graph(graph, "SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?c a riff:OriginClaim }")
    links = count_in_graph(graph, "SELECT (COUNT(*) AS ?n) WHERE { ?a riff:hasStylisticOrigin ?b }")
    artists = count_in_graph(graph, "SELECT (COUNT(DISTINCT ?a) AS ?n) WHERE { ?a a mm:MusicArtist }")
    claims = count_in_graph(graph, "SELECT (COUNT(DISTINCT ?c) AS ?n) WHERE { ?c a riff:InfluenceClaim }")
    pairs = count_in_graph(graph, "SELECT (COUNT(*) AS ?n) WHERE { ?a mm:isInfluencedBy ?b }")
    instruments = count_in_graph(graph, "SELECT (COUNT(DISTINCT ?i) AS ?n) WHERE { ?i a riff:Instrument }")
    plays = count_in_graph(graph, "SELECT (COUNT(*) AS ?n) WHERE { ?a riff:playsInstrument ?i }")
    sources = {row[0]: int(row[1]) for row in result_rows("17_where_instruments_come_from")[1:]}
    uses = sum(sources.values())

    body = f"""
<h1>Do artist influences follow the family tree of genres?</h1>
<p>Everyone knows the family tree of popular music: blues leads to rock and roll, rock and roll leads
to rock, and so on. But musicians don't read family trees. They listen to other musicians. So does
influence between artists really follow the tree?</p>
<p>RIFF is a knowledge graph that puts both things in one place: genres and where they come from,
and artists and who influenced them. Then we can compare them with SPARQL.</p>

<h2>What we found</h2>
<p class="result">Of the artist pairs that cross a genre border, <strong>{percent(follow, total)}%</strong>
follow the family tree (a direct link or a link through one genre in between),
<strong>{percent(against, total)}%</strong> run against it, and <strong>{percent(hidden, total)}%</strong>
have no link in the tree at all.</p>
<p>So the tree explains much of how influence moves, but not all of it. Many of the routes with no link
are genres that sit close to each other and the tree just doesn't connect them. These results depend on
our choice of artists and genres, so they are a starting point for discussion and not a final answer.
See <a href="method.html">Method</a> for how to read the labels and for the limits.</p>
{html_table(result_rows("10_route_summary"))}

<h2>Routes with no link in the tree</h2>
<p>Artists link these genres, but the tree has no link between them. The weight is the number of artist pairs.</p>
{html_table(hidden_routes, MAX_ROWS)}

<h2>Links in the tree with no artists behind them</h2>
<p>The opposite case: {len(no_artists) - 1} links are in the tree, but no pair of artists in our graph
supports them. Some of this comes from our sources, which have much more about rock than about older
music.</p>
{html_table(no_artists, MAX_ROWS)}

<h2>A second question: instruments</h2>
<p>Do genres and influences shape which instruments artists play? For each instrument an artist plays
(leaving out the voice), we check two things. Does an artist who influenced them play it too? And does an
artist of one of the genres their own genre comes from play it?</p>
<p class="result">Both: <strong>{percent(sources.get("both", 0), uses)}%</strong>.
Only the influences: <strong>{percent(sources.get("influences only", 0), uses)}%</strong>.
Only the genre roots: <strong>{percent(sources.get("genre roots only", 0), uses)}%</strong>.
Neither: <strong>{percent(sources.get("neither", 0), uses)}%</strong>.</p>
<p>Most instruments are shared with both, mainly guitar, bass and drums, which almost everyone plays.
An instrument that only the influences explain is rare. The rows to look at are the rarer instruments in
the table below, such as turntables and the drum machine, which often appear with neither.</p>
{html_table(result_rows("17b_where_each_instrument_comes_from"))}

<h2>Instruments a genre adds to its roots</h2>
<p>At least two artists of the genre play these instruments, but no artist of a genre it comes from does.
The year is the earliest year Wikipedia gives for the genre. Read this table with care: for a solo artist we only know
their own instruments, not those of their backing band. The older genres in our list are mostly solo singers,
so drums or bass can look new in rock, ska or funk when they are not. Turntables in hip hop is a real case.</p>
{html_table(result_rows("16_new_instruments"), MAX_ROWS)}

<h2>What is in the graph</h2>
<table>
<tr><th>Item</th><th>Number</th></tr>
<tr><td>Genres</td><td>{genres}</td></tr>
<tr><td>Origin claims (dates and places of genres)</td><td>{origin_claims}</td></tr>
<tr><td>Links between genres</td><td>{links}</td></tr>
<tr><td>Artists</td><td>{artists}</td></tr>
<tr><td>Influence claims</td><td>{claims}</td></tr>
<tr><td>Artist pairs</td><td>{pairs}</td></tr>
<tr><td>Instruments</td><td>{instruments}</td></tr>
<tr><td>Artist plays instrument</td><td>{plays}</td></tr>
<tr><td>Triples</td><td>{len(graph)}</td></tr>
</table>
<p>Download: <a href="data/riff.ttl">ontology</a>, <a href="data/graph.ttl">graph</a>,
<a href="data/routes.ttl">genre routes</a>.</p>
"""
    make_page("index.html", "Home", body)


def short_name(graph, item):
    return graph.namespace_manager.normalizeUri(item)


def terms_table(graph, kind):
    rows = [["Term", "Meaning"]]
    for item in sorted(set(graph.subjects(RDF.type, kind)), key=str):
        comment = graph.value(item, RDFS.comment)
        rows.append([short_name(graph, item), str(comment) if comment else ""])
    return html_table(rows)


def build_ontology():
    graph = Graph()
    graph.parse("ontology/riff.ttl")
    body = f"""
<h1>Ontology</h1>
<p>The RIFF ontology extends <a href="https://w3id.org/polifonia/ontology/music-meta/">Music Meta</a>.
Music Meta already has artists, genres, recordings and a simple "is influenced by" link. It has no way
to say how we know about an influence, and it has no links between genres. RIFF adds those two things.</p>
<p>Namespace: <code>https://w3id.org/riff/ontology#</code>. Download: <a href="data/riff.ttl">riff.ttl</a>.</p>
<img src="data/riff_diagram.svg" alt="Diagram of the RIFF ontology">

<h2>Classes</h2>
{terms_table(graph, OWL.Class)}
<h2>Object properties</h2>
{terms_table(graph, OWL.ObjectProperty)}
<h2>Data properties</h2>
{terms_table(graph, OWL.DatatypeProperty)}
<h2>Individuals</h2>
{terms_table(graph, OWL.NamedIndividual)}
"""
    make_page("ontology.html", "Ontology", body)


def query_header(text, field):
    for line in text.split("\n"):
        if line.startswith("# " + field + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def build_queries():
    body = """
<h1>Queries</h1>
<p>Every query answers one competency question. Tables show the first rows only. All the results are in
the <code>results</code> folder of the project.</p>
"""
    for path in sorted(glob.glob("queries/*.rq")):
        name = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            text = f.read()
        code = "\n".join(line for line in text.split("\n")
                         if not line.startswith(("#", "PREFIX"))).strip()
        body += f"<h2>{name[:3].strip('_')}. {html.escape(query_header(text, 'Title'))}</h2>\n"
        body += f"<p>{html.escape(query_header(text, 'Question'))}</p>\n"
        body += f"<pre><code>{html.escape(code)}</code></pre>\n"
        if os.path.exists("results/" + name + ".csv"):
            body += html_table(result_rows(name), MAX_ROWS)
        elif os.path.exists("results/" + name + ".txt"):
            with open("results/" + name + ".txt", encoding="utf-8") as f:
                body += f"<p>Result: <strong>{f.read().strip()}</strong></p>\n"
        else:
            body += f"<p>Result: an RDF graph, saved as <code>results/{name}.ttl</code>.</p>\n"
    make_page("queries.html", "Queries", body)


def build_method():
    stats = result_rows("extraction_stats")
    overlap = result_rows("14_where_pairs_come_from")
    with open("scripts/method_text.html", encoding="utf-8") as f:
        text = f.read()
    text = text.replace("{{extraction_stats}}", html_table(stats))
    text = text.replace("{{pair_sources}}", html_table(overlap))
    make_page("method.html", "Method", text)


def copy_data_files():
    os.makedirs("docs/data", exist_ok=True)
    for path in ["ontology/riff.ttl", "ontology/riff_diagram.svg", "graph/graph.ttl", "graph/routes.ttl"]:
        shutil.copy(path, "docs/data/")


def main():
    graph = Graph()
    graph.parse("ontology/riff.ttl")
    graph.parse("graph/graph.ttl")
    graph.parse("graph/routes.ttl")
    copy_data_files()
    build_home(graph)
    build_ontology()
    build_queries()
    build_method()
    print("Pages written to docs/")


main()
