import pytest
from repofix.gateway import validate_tool_arguments


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