from pathlib import Path
from repofix.tools import read_file, list_symbols, search_code
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
}

def dispatch_tool(
        workspace: Path,
        name: str,
        arguments: object,
) -> str | list[dict]:
    
    if type(name) is not str:
        raise ValueError
    if name not in TOOL_REGISTRY:
       raise ValueError("未知工具")
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
) -> dict[str, object]:
    try:
        result = dispatch_tool(workspace, name, arguments)
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
    