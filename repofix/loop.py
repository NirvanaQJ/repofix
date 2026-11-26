from repofix.gateway import run_tool

#next_action是本轮模型替身
def run_loop(
    workspace, next_action, *,
    max_steps, allowed_paths, expected_versions, test_profiles,
):
    observations = []
    for turn in range(max_steps):
        next = next_action(observations)
        if next is None:
            return {"stop_reason": "finished", "observations": observations}
        result = run_tool(
              workspace,
              next["name"],
              next["arguments"],
              allowed_paths=allowed_paths,
              expected_versions=expected_versions,
              test_profiles=test_profiles
                )
        observations.append({"name": next["name"], "result": result})
    return {"stop_reason": "step_limit", "observations": observations}