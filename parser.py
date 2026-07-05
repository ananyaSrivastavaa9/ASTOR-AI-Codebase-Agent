from tree_sitter import Language, Parser
import tree_sitter_python

from walker import walk_repo

language = Language(tree_sitter_python.language())
parser = Parser(language)


def get_node_text(node, code_bytes):
    return code_bytes[node.start_byte:node.end_byte].decode(
        "utf-8",
        errors="ignore"
    )


def find_name(node, code_bytes):
    for child in node.children:
        if child.type == "identifier":
            return get_node_text(child, code_bytes)

    return "unknown"


def extract_chunks_from_file(file_path: str):
    try:
        with open(file_path, "rb") as f:
            code_bytes = f.read()
    except FileNotFoundError:
        return []
    except Exception:
        return []

    tree = parser.parse(code_bytes)
    chunks = []

    def visit(node):
        if node.type in ["function_definition", "class_definition"]:
            chunks.append({
                "code": get_node_text(node, code_bytes),
                "name": find_name(node, code_bytes),
                "file": file_path,
                "start": node.start_point[0] + 1,
                "end": node.end_point[0] + 1,
                "type": node.type,
            })

        for child in node.children:
            visit(child)

    visit(tree.root_node)

    return chunks

def get_all_chunks(repo_path: str = "flask-main", max_files: int = None, max_chunks: int = None):
    all_chunks = []
    files = walk_repo(repo_path, max_files=max_files)

    print(f"[parser] parsing {len(files)} files from {repo_path} ...")

    for i, file_path in enumerate(files, start=1):
        chunks = extract_chunks_from_file(file_path)
        all_chunks.extend(chunks)

        if i % 200 == 0:
            print(f"[parser] parsed {i}/{len(files)} files, {len(all_chunks)} chunks so far")

        if max_chunks is not None and len(all_chunks) >= max_chunks:
            print(f"[parser] hit max_chunks={max_chunks}, stopping parse early")
            all_chunks = all_chunks[:max_chunks]
            break

    print(f"[parser] finished {repo_path}: {len(all_chunks)} chunks from {len(files)} files")

    return all_chunks

if __name__ == "__main__":
    one_file = "flask-main/flask-main/src/flask/app.py"

    print("Testing one Flask file:", one_file)

    test_chunks = extract_chunks_from_file(one_file)

    for chunk in test_chunks[:10]:
        print("=" * 50)
        print("Name:", chunk["name"])
        print("Type:", chunk["type"])
        print("File:", chunk["file"])
        print("Start:", chunk["start"])
        print("End:", chunk["end"])
        print(chunk["code"][:300])

    print("Chunks in one file:", len(test_chunks))

    print("\nNow running on all Flask files...")

    all_chunks = get_all_chunks()

    print("Total chunks found:", len(all_chunks))