import chromadb
import os
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

from parser import get_all_chunks

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")
COLLECTION_NAME = "codebase"

# Per-repo caps so one huge repo (e.g. Django) can't blow up total indexing
# time when multiple repos are indexed together. Applied per repo_path, not
# globally, so every repo gets a fair share instead of the first one eating
# the whole budget. None = no cap.
MAX_FILES_PER_REPO = 600
MAX_CHUNKS_PER_REPO = 4000

model = SentenceTransformer(EMBEDDING_MODEL_NAME)
bm25 = None
bm25_chunks = []

client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection(name=COLLECTION_NAME)


def rebuild_index(repo_paths="flask-main"):
    global collection, bm25, bm25_chunks
    
    if isinstance(repo_paths, str):
        repo_paths = [repo_paths]

    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    all_chunks = []
    
    for repo_path in repo_paths:
        print(f"[indexer] indexing repo: {repo_path}")

        chunks = get_all_chunks(
            repo_path,
            max_files=MAX_FILES_PER_REPO,
            max_chunks=MAX_CHUNKS_PER_REPO,
        )

        repo_name = os.path.basename(os.path.abspath(repo_path))

        for chunk in chunks:
            chunk["repo_name"] = repo_name

        all_chunks.extend(chunks)

    # De-duplicate by absolute file path + exact code range. This matters
    # when repo_paths contains overlapping/nested paths (e.g. a parent repo
    # and one of its own subfolders indexed separately) — without this, the
    # same file gets walked twice and every chunk in it gets embedded and
    # stored twice, doubling both indexing time and search results.
    seen_chunks = set()
    deduped_chunks = []

    for chunk in all_chunks:
        abs_file = os.path.abspath(chunk["file"])
        key = (abs_file, chunk["start"], chunk["end"])

        if key in seen_chunks:
            continue

        seen_chunks.add(key)
        deduped_chunks.append(chunk)

    chunks = deduped_chunks

    bm25_chunks = chunks
    tokenized_chunks = [
        chunk["code"].split() 
        for chunk in chunks
    ]

    if not tokenized_chunks:
        bm25 = None
    else:
        bm25 = BM25Okapi(tokenized_chunks)

    # Batch-encode all chunks in one call instead of one at a time — each
    # individual model.encode() call pays fixed per-call overhead on top of
    # the actual compute, so encoding chunk-by-chunk in a loop is far
    # slower than a single batched call across all chunks.
    print(f"[indexer] embedding started: {len(chunks)} chunks")

    texts = [chunk["code"] for chunk in chunks]
    vectors = model.encode(texts, show_progress_bar=True).tolist() if texts else []

    print("[indexer] embedding done")

    ids = []
    documents = []
    metadatas = []
    
    for i, chunk in enumerate(chunks):
        ids.append(f"chunk_{i}")

        documents.append(chunk["code"])

        metadatas.append({
            "name": chunk["name"],
            "file": chunk["file"],
            "start": chunk["start"],
            "end": chunk["end"],
            "repo_name": chunk.get("repo_name", "unknown"),
        })

    print(f"[indexer] DB add started: {len(ids)} chunks")

    collection.add(
        ids=ids,
        embeddings=vectors,
        documents=documents,
        metadatas=metadatas,
    )

    print("[indexer] DB add done")
    print(f"Indexed {len(chunks)} chunks")

    return collection

def search(query: str, top_k: int = 5):
    if collection.count() == 0:
        return {
            "documents": [["Please index a repo first"]],
            "metadatas": [[{
                "repo_name": "system",
                "name": "empty_index",
                "file": "no_repo_indexed",
                "start": 0,
                "end": 0,
            }]],
        }
    query_vector = model.encode(query).tolist()

    vector_results = collection.query(
        query_embeddings=[query_vector],
        n_results=3,
        include=["documents", "metadatas", "distances"],
    )

    distances = vector_results.get("distances", [[]])[0]

    if not distances:
        return {
            "documents": [[]],
            "metadatas": [[]],
        }

    top_distance = distances[0]
    top_similarity = 1 - top_distance

    # NOTE: we no longer hard-return here on a weak top_similarity. That
    # early return was blocking BM25 from ever running, which defeats the
    # point of hybrid search — natural-language questions often embed
    # weakly against raw source code, which is exactly the case BM25's
    # keyword matching is meant to rescue. Both signals are now always
    # combined, and the "no relevant match" fallback only fires if BOTH
    # vector and BM25 agree there's nothing relevant.
    bm25_top_score = 0.0

    if bm25 is not None and bm25_chunks:
        bm25_scores = bm25.get_scores(query.split())
        bm25_top_score = max(bm25_scores) if len(bm25_scores) else 0.0

        bm25_indices = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[:3]
    else:
        bm25_indices = []

    documents = []
    metadatas = []
    seen = set()

    for doc, meta in zip(
        vector_results["documents"][0],
        vector_results["metadatas"][0],
    ):
        key = meta["file"] + str(meta["start"])
        if key not in seen:
            seen.add(key)
            documents.append(doc)
            metadatas.append(meta)

    for idx in bm25_indices:
        chunk = bm25_chunks[idx]

        key = chunk["file"] + str(chunk["start"])

        if key not in seen:
            seen.add(key)
            documents.append(chunk["code"])
            metadatas.append({
                "repo_name": chunk.get("repo_name", "unknown"),
                "name": chunk["name"],
                "file": chunk["file"],
                "start": chunk["start"],
                "end": chunk["end"],
            })

    if not documents and top_similarity < 0.35 and bm25_top_score <= 0:
        return {
            "documents": [["I could not find relevant code for this question. Try rephrasing."]],
            "metadatas": [[{
                "repo_name": "system",
                "name": "no_relevant_match",
                "file": "no_match",
                "start": 0,
                "end": 0,
            }]],
        }

    return {
        "documents": [documents[:top_k]],
        "metadatas": [metadatas[:top_k]],
    }

if __name__ == "__main__":
    collection = rebuild_index()

    results = search("how is error handled")

    for metadata in results["metadatas"][0]:
        print("Name:", metadata["name"])
        print("File:", metadata["file"])
        print("-" * 40)