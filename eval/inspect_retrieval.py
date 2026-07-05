import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

from questions import QUESTIONS
import indexer


def _normalize(text):
    return text.strip().replace("\\", "/").lower()


def _file_matches(expected_file, actual_file):
    return _normalize(expected_file) in _normalize(actual_file)


def get_all_indexed_metadata():
    """Pull every stored chunk's metadata directly from Chroma — bypasses
    search() and top_k entirely, so this tells us what's actually indexed,
    independent of ranking."""
    raw = indexer.collection.get(include=["metadatas"])
    return raw.get("metadatas", [])


def evaluate_retrieval():
    all_metadata = get_all_indexed_metadata()
    print(f"Total chunks in collection: {len(all_metadata)}\n")

    not_indexed = []
    not_chunked = []
    ranking_failed = []
    ranking_ok = []

    for i, item in enumerate(QUESTIONS, start=1):
        question = item["q"]
        expected_file = item["expected_file"]
        expected_function = item["expected_function"]

        # Bucket 1 check: is the expected file indexed AT ALL, anywhere,
        # regardless of ranking or search()?
        file_chunks = [
            m for m in all_metadata
            if _file_matches(expected_file, m.get("file", ""))
        ]

        if not file_chunks:
            not_indexed.append(item)
            print(f"[{i}] NOT_INDEXED — {expected_file} never appears in the collection at all")
            continue

        # Bucket 2 check: among chunks from that file, is there one whose
        # chunk name matches expected_function? (tree-sitter chunk granularity)
        function_chunk = next(
            (m for m in file_chunks if expected_function.lower() in m.get("name", "").lower()),
            None,
        )

        if function_chunk is None:
            not_chunked.append(item)
            print(f"[{i}] NOT_CHUNKED — {expected_file} is indexed ({len(file_chunks)} chunk(s)), "
                  f"but no chunk named like '{expected_function}'. Found names: "
                  f"{[m.get('name') for m in file_chunks][:5]}")
            continue

        # Bucket 3 check: file+function ARE indexed correctly — now test if
        # search() actually surfaces it for this question's phrasing.
        search_results = indexer.search(question, top_k=5)
        result_metas = search_results.get("metadatas", [[]])[0]

        surfaced = any(
            _file_matches(expected_file, m.get("file", ""))
            for m in result_metas
        )

        if surfaced:
            ranking_ok.append(item)
            print(f"[{i}] OK — indexed, chunked, and ranked into top results")
        else:
            ranking_failed.append(item)
            found_files = [m.get("file") for m in result_metas]
            print(f"[{i}] RANKING_FAILED — {expected_file}/{expected_function} exists as a proper "
                  f"chunk, but search(\"{question}\") returned instead: {found_files}")

    total = len(QUESTIONS)
    print("\n======================")
    print("Retrieval Diagnosis")
    print("======================")
    print(f"Not indexed at all:            {len(not_indexed)}/{total}")
    print(f"Indexed but not chunked right: {len(not_chunked)}/{total}")
    print(f"Chunked right, ranking failed: {len(ranking_failed)}/{total}")
    print(f"Fully working (indexed+ranked):{len(ranking_ok)}/{total}")


if __name__ == "__main__":
    evaluate_retrieval()