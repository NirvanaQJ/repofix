import hashlib
import subprocess
import sys
from collections import UserDict

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


def test_dispatch_apply_patch_requires_trusted_context(tmp_path):
    sample = tmp_path / "sample.py"
    original = b"value = 1\n"
    sample.write_bytes(original)
    arguments = {
        "patch": (
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -1 +1 @@\n"
            "-value = 1\n"
            "+value = 2\n"
        ),
    }
    allowed_paths = ["sample.py"]
    expected_versions = {"sample.py": hashlib.sha256(original).hexdigest()}

    with pytest.raises(ValueError, match="缺少补丁执行所需的参数"):
        dispatch_tool(tmp_path, "apply_patch", arguments, allowed_paths=allowed_paths)
    with pytest.raises(ValueError, match="缺少补丁执行所需的参数"):
        dispatch_tool(tmp_path, "apply_patch", arguments, expected_versions=expected_versions)

    for field, value in (
        ("allowed_paths", allowed_paths),
        ("expected_versions", expected_versions),
    ):
        with pytest.raises(ValueError, match="只能包含 patch"):
            dispatch_tool(
                tmp_path, "apply_patch", {**arguments, field: value},
                allowed_paths=allowed_paths, expected_versions=expected_versions,
            )
    assert sample.read_bytes() == original

    assert dispatch_tool(
        tmp_path, "apply_patch", arguments,
        allowed_paths=allowed_paths, expected_versions=expected_versions,
    ) == ["sample.py"]
    assert sample.read_bytes() == b"value = 2\n"


@pytest.mark.parametrize(
    "patch_text",
    [
        "not a patch\n",
        (
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -1 +1 @@\n"
            "-value = 99\n"
            "+value = 2\n"
        ),
    ],
    ids=["invalid_format", "old_line_does_not_match"],
)
def test_run_apply_patch_reports_git_failure(tmp_path, patch_text):
    sample = tmp_path / "sample.py"
    original = b"value = 1\n"
    sample.write_bytes(original)
    expected_versions = {"sample.py": hashlib.sha256(original).hexdigest()}

    result = run_tool(
        tmp_path, "apply_patch", {"patch": patch_text},
        allowed_paths=["sample.py"], expected_versions=expected_versions,
    )

    assert result == {"status": "error", "content": None, "error_code": "patch_failed"}
    assert sample.read_bytes() == original


def test_run_apply_patch_returns_structured_result(tmp_path):
    sample = tmp_path / "sample.py"
    original = b"value = 1\n"
    sample.write_bytes(original)
    arguments = {
        "patch": (
            "--- a/sample.py\n"
            "+++ b/sample.py\n"
            "@@ -1 +1 @@\n"
            "-value = 1\n"
            "+value = 2\n"
        ),
    }
    allowed_paths = ["sample.py"]
    expected_versions = {"sample.py": hashlib.sha256(original).hexdigest()}
    rejected = {"status": "error", "content": None, "error_code": "invalid_request"}

    assert run_tool(tmp_path, "apply_patch", arguments) == rejected
    assert run_tool(
        tmp_path, "apply_patch", {**arguments, "allowed_paths": allowed_paths},
        allowed_paths=allowed_paths, expected_versions=expected_versions,
    ) == rejected
    assert sample.read_bytes() == original

    assert run_tool(
        tmp_path, "apply_patch", arguments,
        allowed_paths=allowed_paths, expected_versions=expected_versions,
    ) == {"status": "ok", "content": ["sample.py"], "error_code": None}
    assert sample.read_bytes() == b"value = 2\n"


def test_run_inspect_diff_returns_structured_result(tmp_path):
    git = ["git", "-C", str(tmp_path)]
    subprocess.run([*git, "init", "--quiet"], check=True)

    for arguments in (None, {"relative_path": "sample.py"}, UserDict()):
        assert run_tool(tmp_path, "inspect_diff", arguments) == {
            "status": "error", "content": None, "error_code": "invalid_request",
        }
    assert run_tool(tmp_path, "inspect_diff", {}) == {
        "status": "error", "content": None, "error_code": "diff_failed",
    }

    sample = tmp_path / "sample.py"
    original = b"value = 1\n"
    sample.write_bytes(original)
    subprocess.run([*git, "add", "sample.py"], check=True)
    subprocess.run([
        *git, "-c", "user.name=RepoFix Test", "-c", "user.email=repofix@example.invalid",
        "-c", "commit.gpgSign=false", "commit", "--quiet", "-m", "baseline",
    ], check=True)
    assert run_tool(tmp_path, "inspect_diff", {}) == {
        "status": "ok", "content": "", "error_code": None,
    }

    patch = (
        "--- a/sample.py\n+++ b/sample.py\n@@ -1 +1 @@\n"
        "-value = 1\n+value = 2\n"
    )
    assert run_tool(
        tmp_path, "apply_patch", {"patch": patch},
        allowed_paths=["sample.py"],
        expected_versions={"sample.py": hashlib.sha256(original).hexdigest()},
    )["status"] == "ok"
    result = run_tool(tmp_path, "inspect_diff", {})
    assert result["status"] == "ok"
    assert result["error_code"] is None
    assert "-value = 1\n+value = 2\n" in result["content"]
    assert sample.read_bytes() == b"value = 2\n"


def test_run_test_profile_preserves_exit_codes_and_rejects_invalid_requests(tmp_path):
    profiles = {
        "smoke": [sys.executable, "-c", "print('ready')"],
        "failure": [
            sys.executable, "-c",
            "import sys; print('failed', file=sys.stderr); sys.exit(1)",
        ],
    }
    name = "run_test_profile"
    smoke = {"profile_id": "smoke"}
    rejected = {"status": "error", "content": None, "error_code": "invalid_request"}

    assert run_tool(tmp_path, name, smoke, test_profiles=profiles) == {
        "status": "ok",
        "content": {"exit_code": 0, "stdout": "ready\n", "stderr": ""},
        "error_code": None,
    }
    assert run_tool(tmp_path, name, {"profile_id": "failure"}, test_profiles=profiles) == {
        "status": "ok",
        "content": {"exit_code": 1, "stdout": "", "stderr": "failed\n"},
        "error_code": None,
    }

    assert run_tool(tmp_path, name, smoke) == rejected
    for arguments in ({}, {"profile_id": ""}, {"profile_id": 1},
                      {"profile_id": "unknown"}, {**smoke, "argv": []}):
        assert run_tool(tmp_path, name, arguments, test_profiles=profiles) == rejected


def test_run_test_profile_reports_timeout(tmp_path):
    profiles = {"slow": [sys.executable, "-c", "import time; time.sleep(2)"]}
    name = "run_test_profile"
    arguments = {"profile_id": "slow"}

    assert run_tool(
        tmp_path, name, arguments, test_profiles=profiles, test_timeout_seconds=0.2,
    ) == {"status": "error", "content": None, "error_code": "timeout"}
    assert run_tool(
        tmp_path, name, {**arguments, "test_timeout_seconds": 300},
        test_profiles=profiles, test_timeout_seconds=0.2,
    ) == {"status": "error", "content": None, "error_code": "invalid_request"}


def test_container_test_profile_forwards_trusted_image_and_preserves_failure(tmp_path, monkeypatch):
    commands = []

    def run_docker(argv, **kwargs):
        commands.append(argv)
        return subprocess.CompletedProcess(argv, 1, "", "failed\n")

    monkeypatch.setattr("repofix.tools.subprocess.run", run_docker)
    profiles = {"smoke": ["python", "-V"]}
    image = "python:3.14"
    arguments = {"profile_id": "smoke"}

    result = run_tool(
        tmp_path, "run_test_profile", arguments, test_profiles=profiles, test_container_image=image,
    )
    assert result == {
        "status": "ok",
        "content": {"exit_code": 1, "stdout": "", "stderr": "failed\n"},
        "error_code": None,
    }
    rejected = run_tool(
        tmp_path, "run_test_profile", {**arguments, "test_container_image": "other"},
        test_profiles=profiles, test_container_image=image,
    )
    assert rejected == {"status": "error", "content": None, "error_code": "invalid_request"}
    assert len(commands) == 1
    assert commands[0][:3] == ["docker", "run", "--name"]
    assert commands[0][-3:] == [image, "python", "-V"]


@pytest.mark.parametrize("cleanup_error", [None, "exit", "timeout"])
def test_container_test_profile_cleans_up_the_named_container(tmp_path, monkeypatch, cleanup_error):
    calls = []

    def run_docker(argv, *, timeout, check, **kwargs):
        calls.append((argv, timeout, check))
        if argv[1] == "run" or cleanup_error == "timeout":
            raise subprocess.TimeoutExpired(argv, timeout)
        if cleanup_error == "exit":
            raise subprocess.CalledProcessError(1, argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr("repofix.tools.subprocess.run", run_docker)
    result = run_tool(
        tmp_path, "run_test_profile", {"profile_id": "slow"},
        test_profiles={"slow": ["python", "-V"]}, test_container_image="python:3.14",
        test_timeout_seconds=0.2,
    )

    expected_code = "timeout" if cleanup_error is None else "test_cleanup_failed"
    assert result == {"status": "error", "content": None, "error_code": expected_code}
    (launch, run_timeout, run_check), cleanup = calls
    assert launch[:3] == ["docker", "run", "--name"]
    assert launch[3].startswith("repofix-test-")
    assert (run_timeout, run_check) == (0.2, False)
    assert cleanup == (["docker", "rm", "--force", launch[3]], 5, True)
