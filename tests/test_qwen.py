import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from repofix.loop import run_loop
from repofix.qwen import make_qwen_next_action


def test_qwen_loop_returns_tool_result_with_the_original_call_id(tmp_path):
    (tmp_path / "sample.py").write_text("value = 1\n", encoding="utf-8")
    requested_call = SimpleNamespace(
        id="call_123",
        function=SimpleNamespace(name="read_file", arguments='{"relative_path":"sample.py"}'),
    )
    assistant_action = SimpleNamespace(role="assistant", tool_calls=[requested_call], content=None)
    assistant_stop = SimpleNamespace(role="assistant", tool_calls=None, content="value is 1")
    responses = iter((assistant_action, assistant_stop))
    requests = []

    def create(**request):
        requests.append({**request, "messages": list(request["messages"])})
        return SimpleNamespace(choices=[SimpleNamespace(message=next(responses))])

    client = Mock()
    client.chat.completions.create.side_effect = create
    messages = [{"role": "user", "content": "Read sample.py"}]
    tools = [{"type": "function", "function": {"name": "read_file"}}]
    decide = make_qwen_next_action(client, "qwen-test-model", messages, tools)

    result = run_loop(
        tmp_path, decide, max_steps=2, allowed_paths=[], expected_versions={}, test_profiles={},
    )

    read_result = {"status": "ok", "content": "value = 1\n", "error_code": None}
    assert result == {
        "stop_reason": "finished",
        "observations": [{"name": "read_file", "result": read_result}],
    }
    assert len(requests) == 2
    assert requests[0] == {
        "model": "qwen-test-model",
        "messages": messages,
        "tools": tools,
        "parallel_tool_calls": False,
    }
    conversation = requests[1]["messages"]
    assert conversation[:-1] == [*messages, assistant_action]
    assert conversation[-1]["role"] == "tool"
    assert conversation[-1]["tool_call_id"] == "call_123"
    assert json.loads(conversation[-1]["content"]) == read_result
    assert messages == [{"role": "user", "content": "Read sample.py"}]


def test_qwen_rejects_more_than_one_tool_call_in_one_reply():
    client = Mock()
    message = SimpleNamespace(tool_calls=[object(), object()])
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=message)],
    )
    decide = make_qwen_next_action(client, "qwen-test-model", [], [])

    with pytest.raises(ValueError):
        decide([])
