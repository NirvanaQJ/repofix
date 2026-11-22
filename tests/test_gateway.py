import pytest
from repofix.gateway import validate_tool_arguments, dispatch_tool,run_tool, validate_search_arguments


def test_validate_default_arguments():
    arguments = {"relative_path": "sample.py"}

    result = validate_tool_arguments(arguments)

    assert result == {
        "relative_path": "sample.py",
        "max_bytes": 65536,
    }
    assert arguments == {"relative_path": "sample.py"}
    assert result is not arguments
    arguments = {"relative_path": "sample.py", "max_bytes": 1}
    assert validate_tool_arguments(arguments) == arguments
    arguments = {"relative_path": "sample.py", "max_bytes": 65536}
    assert validate_tool_arguments(arguments) == arguments
    with pytest.raises(ValueError):validate_tool_arguments({})
    with pytest.raises(ValueError):validate_tool_arguments({"relative_path": ""})
    with pytest.raises(ValueError):validate_tool_arguments({"relative_path": 1})
    with pytest.raises(ValueError):validate_tool_arguments({"relative_path": "sample.py", "workspace": "/tmp"})
    invalid_limits = [0, -1, 65537, True, False, "3", 3.0, None]
    for limit in invalid_limits:
        with pytest.raises(ValueError):validate_tool_arguments({
            "relative_path": "sample.py",
            "max_bytes": limit,
        })
    with pytest.raises(ValueError):validate_tool_arguments(None)
    with pytest.raises(ValueError):validate_tool_arguments([])      

def test_dispatch_tool(tmp_path):
    source = "def greet():\n    return 1\n"
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")

    assert dispatch_tool(
        tmp_path, "read_file", {"relative_path": "sample.py"}
    ) == source
    assert dispatch_tool(tmp_path, "list_symbols", {"relative_path": "sample.py"}) == [{"name": "greet", "kind": "function", "line": 1}] 
    with pytest.raises(ValueError, match="文件过大"):dispatch_tool(tmp_path, "read_file",{"relative_path": "sample.py", "max_bytes": 2},) 


def test_dispatch_tool_boundaries(tmp_path):
    with pytest.raises(ValueError, match="未知工具"):
        dispatch_tool(tmp_path, "shell", {})
    with pytest.raises(ValueError):
        dispatch_tool(tmp_path, [],{"relative_path": "sample.py"})
    with pytest.raises(ValueError, match="未知参数"):
        dispatch_tool(tmp_path, "read_file",{"relative_path": "sample.py", "workspace": "/tmp"})  
    with pytest.raises(FileNotFoundError):
        dispatch_tool(tmp_path, "read_file", {"relative_path": "missing.txt"})

def test_run_tool(tmp_path):
    source = "def greet():\n    return 1\n"
    (tmp_path / "sample.py").write_text(source, encoding="utf-8")

    assert run_tool(
        tmp_path, "read_file", {"relative_path": "sample.py"}
    ) == {
        "status": "ok",
        "content": source,
        "error_code": None,
    }

    assert run_tool(
        tmp_path, "list_symbols", {"relative_path": "sample.py"}
    ) == {
    "status": "ok",
    "content": [{"name": "greet", "kind": "function", "line": 1}],
    "error_code": None,
    }   

    assert run_tool(
            tmp_path, "read_file", {"relative_path": "missing.txt"}
        ) == {
    "status": "error",
    "content": None,
    "error_code": "file_not_found",
    }            

def test_run_tool_errors(tmp_path):
    (tmp_path / "bad.bin").write_bytes(b"\xff")
    (tmp_path / "broken.py").write_text(
        "def broken(:\n", encoding="utf-8"
    )

    assert run_tool(
        tmp_path, "read_file", {"relative_path": "bad.bin"}
    ) == {
        "status": "error",
        "content": None,
        "error_code": "invalid_encoding",
    }
    assert run_tool(
            tmp_path, "list_symbols", {"relative_path": "broken.py"}
        ) == {
            "status": "error",
            "content": None,
            "error_code": "invalid_syntax",
        }
    assert run_tool(
                tmp_path, "shell", {}
            ) == {
                "status": "error",
                "content": None,
                "error_code": "invalid_request",
            }
    assert run_tool(
                tmp_path, "read_file", {"relative_path": "."}
            ) == {
                "status": "error",
                "content": None,
                "error_code": "io_error",
            }

def test_validate_search_arguments():
       arguments = {"relative_path": "sample.py", "query": "alpha"}
       result = validate_search_arguments(arguments)

       assert result == {
        "relative_path": "sample.py",
        "max_bytes": 65536,
        "query": "alpha",
        }
       assert arguments=={"relative_path": "sample.py", "query": "alpha"}
       assert result is not arguments
       assert validate_search_arguments({
        "relative_path": "sample.py",
        "query": "alpha",
        "max_bytes": 7,
           })=={
        "relative_path": "sample.py",
        "max_bytes": 7,
        "query": "alpha",
        }
       with pytest.raises(ValueError):validate_search_arguments(None)
       with pytest.raises(ValueError):validate_search_arguments([])
       with pytest.raises(ValueError):validate_search_arguments({"relative_path": "sample.py"})
       
       for invalid_query in ["", None, 1, []]:
          with pytest.raises(ValueError):validate_search_arguments({"relative_path": "sample.py","query": invalid_query,
        })
       with pytest.raises(ValueError):validate_search_arguments({"relative_path": "sample.py","query": "alpha","workspace": "/tmp"})
        
def test_run_search_code(tmp_path):
    (tmp_path / "sample.py").write_text(
        "alpha\nbeta alpha\n", encoding="utf-8"
    )
    name = "".join(["search", "_code"])

    assert run_tool(
        tmp_path, name,
        {"relative_path": "sample.py", "query": "alpha"},
    ) == {
        "status": "ok",
        "content": [
            {"line": 1, "text": "alpha"},
            {"line": 2, "text": "beta alpha"},
        ],
        "error_code": None,
    }

    assert run_tool(
            tmp_path, name,
            {"relative_path": "sample.py", "query": "missing"},
        ) == {
            "status": "ok",
            "content": [
            
            ],
            "error_code": None,
        }


    assert run_tool(
        tmp_path, name,
        {"relative_path": "sample.py"},
    ) == {
        "status": "error",
        "content":None,
        "error_code": "invalid_request",
    }

    assert run_tool(
            tmp_path, name,
            {"relative_path": "sample.py", "query": "missing","workspace": "/tmp"},
        ) == {
            "status": "error",
            "content":None,
            "error_code": "invalid_request",
        }    

    assert run_tool(
                tmp_path, name,
                {"relative_path": "sample.py", "query": "missing","max_bytes":2},
            ) == {
                "status": "error",
                "content":None,
                "error_code": "invalid_request",
            }                                   

    assert run_tool(
                tmp_path, "read_file",
                {"relative_path": "sample.py", "query": "alpha"},
            ) == {
                "status": "error",
                "content":None,
                "error_code": "invalid_request",
            }                                                    