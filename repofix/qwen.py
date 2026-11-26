import json


def make_qwen_next_action(client, model, messages, tools):
    conversation = list(messages)
    pending_call_id = None

    def next_action(observations):
        nonlocal pending_call_id
        if pending_call_id is not None:
            conversation.append({
                "role": "tool",
                "tool_call_id": pending_call_id,
                "content": json.dumps(observations[-1]["result"], ensure_ascii=False),
            })
            pending_call_id = None

        completion = client.chat.completions.create(
            model=model,
            messages=conversation,
            tools=tools,
            parallel_tool_calls=False,
        )
        message = completion.choices[0].message
        conversation.append(message)
        calls = message.tool_calls or []
        if not calls:
            return None
        if len(calls) !=1:
            raise ValueError
        call = calls[0]
        pending_call_id = call.id
        return {"name": call.function.name, "arguments": json.loads(call.function.arguments)}

    return next_action