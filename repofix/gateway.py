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
    
    