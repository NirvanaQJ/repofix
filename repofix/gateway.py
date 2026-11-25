from pathlib import Path
from repofix.tools import read_file, list_symbols, search_code, apply_patch, inspect_diff, run_test_profile
import subprocess
def validate_tool_arguments(
    arguments: object,
) -> dict[str, str | int]:
    if not isinstance(arguments,dict):
        raise ValueError("arguments 必须是字典")
    for key in arguments:
       if key not in ("relative_path", "max_bytes"):
         raise ValueError(f"未知参数：{key}")
    if "relative_path" not in arguments:
        raise ValueError("缺少参数 \"relative_path\"")
    if not type(arguments["relative_path"]) is str:
        raise ValueError("\"relative_path\"必须为str类型")
    if "relative_path" in arguments and not arguments["relative_path"]:
        raise ValueError("参数 \"relative_path\" 不能为空")
    max_bytes = arguments.get("max_bytes", 65536)
    if type(max_bytes) is not int or not 1 <= max_bytes <= 65536:
       raise ValueError("max_bytes 必须是 1 到 65536 的整数")
    return {"relative_path": arguments["relative_path"],"max_bytes": max_bytes,}


TOOL_REGISTRY = {
    "read_file": read_file,
    "list_symbols": list_symbols,
    "search_code": search_code,
    "apply_patch": apply_patch,
    "inspect_diff": inspect_diff,
    "run_test_profile":run_test_profile
}

def dispatch_tool(
        workspace: Path,
        name: str,
        arguments: object,
        *,
        allowed_paths: list[str] | None = None,
        expected_versions: dict[str, str] | None = None,
        test_profiles: dict[str, list[str]] | None = None
) -> str | list[dict] | list[str]:
    
    if type(name) is not str:
        raise ValueError
    if name not in TOOL_REGISTRY:
       raise ValueError("未知工具")
    if name == "apply_patch":
        if not isinstance(arguments, dict):
           raise ValueError("arguments 必须是字典")
        if set(arguments) != {"patch"}:
            raise ValueError("arguments 必须且只能包含 patch")
        patch_text = arguments["patch"]
        if not isinstance(patch_text, str) or not patch_text:
           raise ValueError("patch 必须是非空字符串")
        if allowed_paths is None or expected_versions is None:
           raise ValueError("缺少补丁执行所需的参数")
        return apply_patch(workspace,patch_text.encode("utf-8"),allowed_paths=allowed_paths,expected_versions=expected_versions,)

    if name == "inspect_diff":
        if not isinstance(arguments, dict) or arguments:
            raise ValueError("inspect_diff 只接受空字典")
        return inspect_diff(workspace)

    if name == "run_test_profile":
        if not isinstance(arguments, dict) or set(arguments) != {"profile_id"}:
            raise ValueError("arguments 必须且只能包含 profile_id")

        profile_id = arguments["profile_id"]
        if not isinstance(profile_id, str) or not profile_id:
            raise ValueError("profile_id 必须是非空字符串")
        if test_profiles is None:
            raise ValueError("缺少测试配置表")

        return run_test_profile(workspace, profile_id, test_profiles)

    if name == "search_code":
        validated = validate_search_arguments(arguments)
    else:
        validated = validate_tool_arguments(arguments)
    tool = TOOL_REGISTRY[name]
    return tool(workspace, **validated)

def run_tool(
    workspace: Path,
    name: str,
    arguments: object,
    *,
    allowed_paths: list[str] | None = None,
    expected_versions: dict[str, str] | None = None,
    test_profiles: dict[str, list[str]] | None = None
) -> dict[str, object]:
    try:
        result = dispatch_tool(
           workspace,
           name,
           arguments,
           allowed_paths=allowed_paths,
           expected_versions=expected_versions,
           test_profiles=test_profiles
         )
    except FileNotFoundError:
        return {"status": "error", "content": None, "error_code": "file_not_found"}
    except UnicodeDecodeError:
        return {"status": "error", "content": None, "error_code": "invalid_encoding"}
    except SyntaxError:
        return {"status": "error", "content": None, "error_code": "invalid_syntax"}
    except ValueError:
        return {"status": "error", "content": None, "error_code": "invalid_request"}
    except OSError:
        return {"status": "error", "content": None, "error_code": "io_error"} 
    except subprocess.CalledProcessError:
        if name =="inspect_diff":
            return {"status": "error", "content": None, "error_code": "diff_failed"}
        else:
            return {"status": "error", "content": None, "error_code": "patch_failed"}
    else:
        return {"status": "ok", "content": result, "error_code": None}

def validate_search_arguments(
    arguments: object,
) -> dict[str, str | int]:
    if not isinstance(arguments, dict):
        raise ValueError
    
    if "query" not in arguments:
    
        raise ValueError
    if type(arguments["query"]) is not str:
        raise ValueError
    if not arguments["query"]:
        raise ValueError

    base_arguments = arguments.copy()
    base_arguments.pop("query")

    validated = validate_tool_arguments(base_arguments)
    validated["query"] = arguments["query"]

    return validated
