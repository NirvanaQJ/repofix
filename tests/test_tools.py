import subprocess
import sys

import pytest, hashlib
from repofix.tools import read_file, run_read_file, list_symbols, search_code, read_file_at_version, validate_patch_targets
from repofix.tools import parse_patch_numstat, check_patch_scope, apply_patch, inspect_diff, run_test_profile

def test_read_file(tmp_path):
    (tmp_path / "sample.py").write_text("你好\n", encoding="utf-8")

    assert read_file(tmp_path, "sample.py") == "你好\n"

    with pytest.raises(ValueError):read_file(tmp_path, "/sample.py")

    with pytest.raises(ValueError):read_file(tmp_path, "../sample.py")
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("外部文件", encoding="utf-8")
    (workspace / "link.txt").symlink_to(outside)

    with pytest.raises(ValueError):read_file(workspace, "link.txt")

    with pytest.raises(FileNotFoundError):read_file(tmp_path, "src/sample.py")

    (tmp_path / "small.txt").write_text("你", encoding="utf-8")
    assert read_file(tmp_path, "small.txt", max_bytes=3) == "你"
    with pytest.raises(ValueError, match="文件过大"):
        read_file(tmp_path, "small.txt", max_bytes=2)
    with pytest.raises(ValueError, match="max_bytes 必须大于 0"):
        read_file(tmp_path, "small.txt", max_bytes=0)
    with pytest.raises(ValueError, match="max_bytes 必须大于 0"):
        read_file(tmp_path, "small.txt", max_bytes=-1)

def test_run_read_file(tmp_path):
    (tmp_path / "sample.txt").write_text("你", encoding="utf-8")

    assert run_read_file(tmp_path, "sample.txt") == {
        "status": "ok",
        "content": "你",
        "error_code": None,
    }

    assert run_read_file(tmp_path, "missing.txt") == {
        "status": "error",
        "content": None,
        "error_code": "file_not_found",
    }

    assert run_read_file(tmp_path, "/sample.txt") == {
        "status": "error",
        "content": None,
        "error_code": "invalid_request",
    }

    assert run_read_file(tmp_path, "sample.txt", max_bytes=2) == {
        "status": "error",
        "content": None,
        "error_code": "invalid_request",
    }
    (tmp_path / "bad.bin").write_bytes(b"\xff")
    assert run_read_file(tmp_path, "bad.bin") == {
        "status": "error",
        "content": None,
        "error_code": "invalid_encoding",
    }

    assert run_read_file(tmp_path, ".") == {
        "status": "error",
        "content": None,
        "error_code": "io_error",
    }

def test_list_symbols(tmp_path):
    source = (
        "def outer():\n"
        "    def inner():\n"
        "        pass\n"
        "    return inner\n"
        "\n"
        "async def worker():\n"
        "    pass\n"
        "\n"
        "class Box:\n"
        "    def method(self):\n"
        "        pass\n"
    )
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")
    assert list_symbols(tmp_path, "sample.py") == [
        {"name": "outer", "kind": "function", "line": 1},
        {"name": "worker", "kind": "async_function", "line": 6},
        {"name": "Box", "kind": "class", "line": 9},
    ]

    (tmp_path / "plain.py").write_text("value = 1\n", encoding="utf-8")

    assert list_symbols(tmp_path, "plain.py") == []

    (tmp_path / "broken.py").write_text("def broken(:\n", encoding="utf-8")

    with pytest.raises(SyntaxError):
        list_symbols(tmp_path, "broken.py")

    with pytest.raises(FileNotFoundError):
        list_symbols(tmp_path, "missing.py")

    (tmp_path / "large.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="文件过大"):
        list_symbols(tmp_path, "large.py", max_bytes=2)

def test_search_code(tmp_path):
    source = "alpha\n\n  beta alpha alpha\nALPHA\nx.y\nxay\n"
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")

    assert search_code(tmp_path, "sample.py", "alpha") == [
        {"line": 1, "text": "alpha"},
        {"line": 3, "text": "  beta alpha alpha"},
    ]

    assert search_code(tmp_path, "sample.py", "missing") == []

    assert search_code(tmp_path, "sample.py", ".") == [{"line": 5, "text": "x.y"}]


def test_search_code_boundaries(tmp_path):
    (tmp_path / "sample.py").write_text("alpha\n", encoding="utf-8")

    for invalid_query in ["", None, 1, []]:
        with pytest.raises(ValueError):
            search_code(tmp_path, "sample.py", invalid_query)
    assert search_code(tmp_path, "sample.py", "alpha", 6)==[{"line": 1, "text": "alpha"}]

    with pytest.raises(ValueError,match="文件过大"):search_code(tmp_path, "sample.py", "alpha", 5)
    with pytest.raises(FileNotFoundError):search_code(tmp_path, "missing.py", "alpha")
    with pytest.raises(ValueError,match="路径超出工作区"):search_code(tmp_path, "../sample.py", "alpha")

def test_read_file_at_version(tmp_path):
    (tmp_path / "sample.py").write_text("你好\n", encoding="utf-8")
    path=tmp_path / "sample.py"
    data = hashlib.sha256(path.read_bytes()).hexdigest()
    assert read_file_at_version(tmp_path, "sample.py", data)=="你好\n"
    (tmp_path / "sample.py").write_text("您好\n", encoding="utf-8")
    with pytest.raises(ValueError, match="文件版本不匹配"):read_file_at_version(tmp_path, "sample.py", data)


def test_read_file_at_version_byte_limit(tmp_path):
    (tmp_path / "sample.py").write_text("你", encoding="utf-8")
    path=tmp_path / "sample.py"
    data = hashlib.sha256(path.read_bytes()).hexdigest()
    assert read_file_at_version(tmp_path, "sample.py", data, max_bytes=3)=="你"
    with pytest.raises(ValueError, match="文件过大"):read_file_at_version(tmp_path, "sample.py", data, max_bytes=2)
    

def test_validate_patch_targets():
    allowed_paths = ["more_itertools/more.py"]
    assert validate_patch_targets(["more_itertools/more.py"], allowed_paths) is None
    
    with pytest.raises(ValueError,match=r"tests/test_more\.py"):validate_patch_targets(["more_itertools/more.py","tests/test_more.py"],allowed_paths)

def test_validate_rename_targets():
    with pytest.raises(ValueError, match=r"new\.py"):validate_patch_targets(["old.py", "new.py"],["old.py"])
    with pytest.raises(ValueError, match=r"old\.py"):validate_patch_targets(["old.py", "new.py"],["new.py"])
    assert validate_patch_targets(["old.py", "new.py"],["old.py", "new.py"]) is None

def test_parse_patch_numstat():
    output = b"1\t1\tsample.py\x00" + b"2\t0\tdir/other\tfile.py\x00"
    assert parse_patch_numstat(output)==["sample.py", "dir/other\tfile.py"]

def test_check_patch_scope(tmp_path):
    sample = tmp_path / "sample.py"
    other = tmp_path / "other.py"
    sample.write_text("value = 1\n", encoding="utf-8")
    other.write_text("value = 1\n", encoding="utf-8")
    sample_patch = (
    b"--- a/sample.py\n"
    b"+++ b/sample.py\n"
    b"@@ -1 +1 @@\n"
    b"-value = 1\n"
    b"+value = 2\n"
)
    other_patch = (
    b"--- a/other.py\n"
    b"+++ b/other.py\n"
    b"@@ -1 +1 @@\n"
    b"-value = 1\n"
    b"+value = 2\n"
)
    allowed_paths = ["sample.py"]
    assert check_patch_scope(tmp_path, sample_patch, allowed_paths) == ["sample.py"]

    with pytest.raises(ValueError, match=r"other\.py"): check_patch_scope(tmp_path, sample_patch + other_patch, allowed_paths)
    assert sample.read_text(encoding="utf-8")=="value = 1\n"
    assert other.read_text(encoding="utf-8")=="value = 1\n"

    
@pytest.mark.parametrize("new_name", ["new.py", "草稿.py"])
def test_check_patch_scope_rename(tmp_path, new_name):
    patch_repo = tmp_path / "patch_repo"
    patch_repo.mkdir()
    contents = "value = 1\n"
    (patch_repo / "old.py").write_text(contents, encoding="utf-8")

    git = ["git", "-C", str(patch_repo)]
    subprocess.run([*git, "init", "--quiet"], check=True)
    subprocess.run([*git, "add", "old.py"], check=True)
    base_tree = subprocess.check_output([*git, "write-tree"], text=True).strip()
    subprocess.run([*git, "mv", "old.py", new_name], check=True)
    patch = subprocess.check_output([
        *git, "-c", "core.quotePath=true",
        "diff", "--cached", "--find-renames", base_tree,
    ])

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    old_path = workspace / "old.py"
    old_path.write_text(contents, encoding="utf-8")

    targets = check_patch_scope(workspace, patch, ["old.py", new_name])
    assert set(targets) == {"old.py", new_name}

    with pytest.raises(ValueError, match=r"old\.py"):
        check_patch_scope(workspace, patch, [new_name])

    assert old_path.read_text(encoding="utf-8") == contents
    assert not (workspace / new_name).exists()


def test_apply_patch_checks_all_files_before_writing(tmp_path):
    paths = ["sample.py", "other.py"]
    original = b"value = 1\n"
    expected_hash = hashlib.sha256(original).hexdigest()
    versions = {path: expected_hash for path in paths}
    for path in paths:
        (tmp_path / path).write_bytes(original)

    patch = "".join(
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        "-value = 1\n"
        "+value = 2\n"
        for path in paths
    ).encode("utf-8")

    rejected_cases = [
        (["sample.py"], versions, r"未授权路径：other\.py"),
        (paths, {"sample.py": expected_hash}, None),
        (paths, {**versions, "other.py": "0" * 64}, "文件版本不匹配"),
    ]
    for allowed_paths, expected_versions, message in rejected_cases:
        with pytest.raises(ValueError, match=message):
            apply_patch(tmp_path, patch, allowed_paths, expected_versions)
        assert [(tmp_path / path).read_bytes() for path in paths] == [original, original]

    assert apply_patch(tmp_path, patch, paths, versions) == paths
    for path in paths:
        assert (tmp_path / path).read_bytes() == b"value = 2\n"


def test_inspect_diff_reads_patch_result(tmp_path):
    sample = tmp_path / "sample.py"
    original = b"value = 1\n"
    sample.write_bytes(original)
    git = ["git", "-C", str(tmp_path)]
    subprocess.run([*git, "init", "--quiet"], check=True)
    subprocess.run([*git, "add", "sample.py"], check=True)
    subprocess.run([
        *git, "-c", "user.name=RepoFix Test", "-c", "user.email=repofix@example.invalid",
        "-c", "commit.gpgSign=false", "commit", "--quiet", "-m", "baseline",
    ], check=True)

    assert inspect_diff(tmp_path) == ""

    patch = (
        b"--- a/sample.py\n"
        b"+++ b/sample.py\n"
        b"@@ -1 +1 @@\n"
        b"-value = 1\n"
        b"+value = 2\n"
    )
    versions = {"sample.py": hashlib.sha256(original).hexdigest()}
    apply_patch(tmp_path, patch, ["sample.py"], versions)

    diff = inspect_diff(tmp_path)
    assert "diff --git a/sample.py b/sample.py\n" in diff
    assert "-value = 1\n+value = 2\n" in diff
    assert sample.read_bytes() == b"value = 2\n"


def test_run_test_profile_selects_registered_command_and_preserves_result(tmp_path):
    (tmp_path / "sample.txt").write_text("workspace", encoding="utf-8")
    profiles = {
        "smoke": [
            sys.executable, "-c",
            "from pathlib import Path; print(Path('sample.txt').read_text(encoding='utf-8'))",
        ],
        "failure": [
            sys.executable, "-c",
            "import sys; print('failed', file=sys.stderr); raise SystemExit(1)",
        ],
    }

    assert run_test_profile(tmp_path, "smoke", profiles) == {
        "exit_code": 0, "stdout": "workspace\n", "stderr": "",
    }
    assert run_test_profile(tmp_path, "failure", profiles) == {
        "exit_code": 1, "stdout": "", "stderr": "failed\n",
    }
    with pytest.raises(ValueError, match="未知测试配置：unknown"):
        run_test_profile(tmp_path, "unknown", profiles)
