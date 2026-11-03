"""Run the SPARQL queries in queries/ and the tests in tests/. Save the results in results/.

Run it from the project folder: python scripts/run_queries.py
A test is a query that looks for mistakes, so a test passes when it returns no rows.
"""
import csv
import glob
import os

from rdflib import Graph

from common import read_csv

CURATED_FILES = ["genres", "lineage", "artists", "genre_phases", "recordings",
                 "influences_wikidata", "influences_text", "influences_recordings"]


def file_name(path):
    return os.path.splitext(os.path.basename(path))[0]


def save_rows(path, result):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([str(name) for name in result.vars])
        for row in result:
            writer.writerow(["" if value is None else str(value) for value in row])


def run_queries(graph):
    for path in sorted(glob.glob("queries/*.rq")):
        name = file_name(path)
        with open(path, encoding="utf-8") as f:
            result = graph.query(f.read())

        if result.type == "SELECT":
            save_rows("results/" + name + ".csv", result)
            print(name, "-", len(result), "rows")
        elif result.type == "ASK":
            with open("results/" + name + ".txt", "w", encoding="utf-8") as f:
                f.write(str(result.askAnswer).lower() + "\n")
            print(name, "-", result.askAnswer)
        else:
            result.graph.serialize("results/" + name + ".ttl", format="turtle")
            print(name, "-", len(result.graph), "triples")

        # Query 09 makes the genre routes. Later queries need them.
        if name.startswith("09"):
            result.graph.serialize("graph/routes.ttl", format="turtle")
            for triple in result.graph:
                graph.add(triple)


def run_tests(graph):
    lines = []
    failed = 0
    for path in sorted(glob.glob("tests/*.rq")):
        name = file_name(path)
        with open(path, encoding="utf-8") as f:
            result = graph.query(f.read())
        problems = len(result)
        if problems == 0:
            lines.append(name + ": pass")
        else:
            failed += 1
            lines.append(name + ": FAIL, " + str(problems) + " problems")
            for row in list(result)[:10]:
                lines.append("    " + " | ".join(str(value) for value in row))
    with open("results/tests.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("Tests failed:", failed)


def save_extraction_stats():
    words = {}
    for row in read_csv("data/curated/influences_text.csv"):
        counts = words.setdefault(row["word"], {"candidates": 0, "kept": 0, "same claim": 0, "dropped": 0})
        counts["candidates"] += 1
        if row["keep"] == "yes":
            counts["kept"] += 1
        elif row["keep"] == "same claim":
            counts["same claim"] += 1
        else:
            counts["dropped"] += 1

    rows = []
    total = {"word": "all", "candidates": 0, "kept": 0, "same claim": 0, "dropped": 0}
    for word in sorted(words, key=lambda w: -words[w]["candidates"]):
        rows.append(dict(words[word], word=word))
        for name in ["candidates", "kept", "same claim", "dropped"]:
            total[name] += words[word][name]
    rows.append(total)
    for row in rows:
        row["precision"] = round((row["kept"] + row["same claim"]) / row["candidates"], 2)
    with open("results/extraction_stats.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["word", "candidates", "kept", "same claim", "dropped", "precision"])
        writer.writeheader()
        writer.writerows(rows)


def show_review_status():
    print("Rows still marked as draft:")
    for name in CURATED_FILES:
        rows = read_csv("data/curated/" + name + ".csv")
        drafts = sum(1 for row in rows if row.get("status") == "draft")
        print(" ", name + ":", drafts, "of", len(rows))


def main():
    graph = Graph()
    graph.parse("ontology/riff.ttl")
    graph.parse("graph/graph.ttl")
    run_queries(graph)
    run_tests(graph)
    save_extraction_stats()
    show_review_status()


main()
