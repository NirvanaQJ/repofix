import pytest
from repofix.tools import read_file, run_read_file, list_symbols, search_code


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