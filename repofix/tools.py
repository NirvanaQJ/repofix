from pathlib import Path
import ast, hashlib, subprocess, uuid

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

def validate_patch_targets(
    target_paths: list[str],
    allowed_paths: list[str],
) -> None:
    for tmp in target_paths:
        if tmp not in allowed_paths:
            raise ValueError(f"补丁修改了未授权路径：{tmp}")

    return    


def parse_patch_numstat(output: bytes) -> list[str]:
    output=output.split(b"\x00")
    result=[]
    for tmp in output:
        if not tmp:
            continue
        _, _, path_bytes = tmp.split(b"\t", 2)
        data=path_bytes.decode("utf-8")
        result.append(data)
    return result
def unquote_git_path(path: bytes) -> bytes:
    if not path.startswith(b'"'):
        return path
    if len(path) < 2 or not path.endswith(b'"'):
        raise ValueError("Git 路径缺少结束引号")

    escapes = {
        b"a": b"\a",
        b"b": b"\b",
        b"t": b"\t",
        b"n": b"\n",
        b"v": b"\v",
        b"f": b"\f",
        b"r": b"\r",
        b'"': b'"',
        b"\\": b"\\",
    }
    payload = path[1:-1]
    decoded = bytearray()
    index = 0

    while index < len(payload):
        current = payload[index]
        if current == ord('"'):
            raise ValueError("Git 路径包含未转义的引号")
        if current != ord("\\"):
            decoded.append(current)
            index += 1
            continue

        marker = payload[index + 1:index + 2]
        if marker in escapes:
            decoded.extend(escapes[marker])
            index += 2
            continue

        digits = payload[index + 1:index + 4]
        if (
            len(digits) != 3
            or digits[0] not in b"0123"
            or any(digit not in b"01234567" for digit in digits[1:])
        ):
            raise ValueError("Git 路径包含无效转义")

        decoded.append(int(digits, 8))
        index += 4

    return bytes(decoded)


def extract_rename_paths(lines: list[bytes]) -> list[bytes]:
    prefixes = (b"rename from ", b"rename to ")
    paths = []
    for prefix in prefixes:
        for line in lines:
            if line.startswith(prefix):
                paths.append(unquote_git_path(line[len(prefix):]))
    return paths


def check_patch_scope(
    workspace: Path,
    patch: bytes,
    allowed_paths: list[str],
) -> list[str]:
    result = subprocess.run(
    ["git", "apply", "--numstat", "-z", "-"],
    cwd=workspace,
    input=patch,
    capture_output=True,
    check=True,
    )
    patch_list=parse_patch_numstat(result.stdout)
    for path_bytes in extract_rename_paths(patch.split(b"\n")):
        path = path_bytes.decode("utf-8")
        if path not in patch_list:
            patch_list.append(path)

    validate_patch_targets(patch_list, allowed_paths)
    return patch_list

def apply_patch(
    workspace: Path,
    patch: bytes,
    allowed_paths: list[str],
    expected_versions: dict[str, str],
) -> list[str]:
    documents = check_patch_scope(workspace, patch, allowed_paths)
    for i in documents:
        if i not in expected_versions:
            raise ValueError
        read_file_at_version(workspace, i, expected_versions[i])

    subprocess.run(
    ["git", "apply", "-"],
    cwd=workspace,
    input=patch,
    capture_output=True,
    check=True,
    )
    return documents

def inspect_diff(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--no-textconv", "--no-color", "HEAD", "--"],
        cwd=workspace,
        capture_output=True,
        check=True,
        )
    return result.stdout.decode("utf-8")

def build_test_container_argv(
    workspace: Path,
    image: str,
    argv: list[str],
    *,
    container_name: str | None = None,
) -> list[str]:
    name_args = ["--name", container_name] if container_name is not None else []
    return [
        "docker", "run", *name_args,
        "--network", "none",
        "--user", "65534:65534",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--rm",
        "--pull", "never",
        "--cpus", "1",
        "--memory", "2g",
        "--memory-swap", "2g",
        "--pids-limit", "64",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=64m,mode=1777",
        "--mount", f"type=bind,src={workspace},dst=/workspace,readonly",
        "--workdir", "/workspace",
        image, *argv,
    ]

class TestContainerCleanupError(RuntimeError):
    pass
def run_test_profile(
    workspace: Path,
    profile_id: str,
    profiles: dict[str, list[str]],
    timeout_seconds: float = 30,
    *, container_image: str | None = None
) -> dict[str, int | str]:
    if profile_id not in profiles:
        raise ValueError(f"未知测试配置：{profile_id}")

    argv = profiles[profile_id]
    container_name = None
    if container_image is not None:
        container_name = f"repofix-test-{uuid.uuid4().hex}"
        argv = build_test_container_argv(
            workspace, container_image, argv,
            container_name=container_name,
        )
    try:
      result = subprocess.run(
        argv,
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds
       )
    except subprocess.TimeoutExpired:
        if container_name is not None:
            try:
                subprocess.run(
                    ["docker", "rm", "--force", container_name],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise TestContainerCleanupError(container_name) from exc
        raise
    return {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}

