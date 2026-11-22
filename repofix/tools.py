from pathlib import Path
import ast, hashlib

def read_file(
    workspace: Path,
    relative_path: str,
    max_bytes: int = 65536,
) -> str:
    if max_bytes <= 0:
        raise ValueError("max_bytes 必须大于 0")
    path = Path(relative_path)
    if path.is_absolute():
       raise ValueError("不要使用绝对路径")

    workspace_real = workspace.resolve()

    target =(workspace_real / path).resolve()

    if not target.is_relative_to(workspace_real):
        raise ValueError("路径超出工作区")

    with target.open("rb") as f:
        content = f.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError("文件过大")

    return content.decode("utf-8")

def run_read_file(
    workspace: Path,
    relative_path: str,
    max_bytes: int = 65536,
) -> dict[str, str | None]:
    try:
        text = read_file(workspace, relative_path, max_bytes)
        
    except FileNotFoundError:
        return {"status": "error", "content": None, "error_code": "file_not_found"}
    except UnicodeDecodeError:
        return {"status": "error", "content": None, "error_code": "invalid_encoding"}
    except ValueError:
        return {"status": "error", "content": None, "error_code": "invalid_request"}
    except OSError:
        return {"status": "error", "content": None, "error_code": "io_error"} 
    else:  
        return {"status": "ok", "content": text, "error_code": None}


def list_symbols(
    workspace: Path,
    relative_path: str,
    max_bytes: int = 65536,
) -> list[dict]:
    text = read_file(workspace, relative_path, max_bytes)
    tree = ast.parse(text)
    symbols = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef)):
            symbols.append({"name": node.name, "kind": "function", "line": node.lineno})
        elif isinstance(node, (ast.ClassDef)):
            symbols.append({"name": node.name, "kind": "class", "line": node.lineno})
        elif isinstance(node, (ast.AsyncFunctionDef)):
            symbols.append({"name": node.name, "kind": "async_function", "line": node.lineno})
    return symbols

def search_code(
    workspace: Path,
    relative_path: str,
    query: str,
    max_bytes: int = 65536,
) -> list[dict]:
    if type(query) is not str:
        raise ValueError
    if not query:
        raise ValueError
    text = read_file(workspace, relative_path, max_bytes)
    matches = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if query in line:
           matches.append({"line": line_no, "text": line})
    return matches

def read_file_at_version(
    workspace: Path,
    relative_path: str,
    expected_sha256: str,
    max_bytes: int = 65536,
) -> str:
    text = read_file(workspace, relative_path, max_bytes)
    data = text.encode("utf-8")
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError("文件版本不匹配")
    return text    
    

    