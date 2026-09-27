"""Explicit dependencies for retained portfolio work, without extra model roles."""

import asyncio


STAGES = {
    "research": [], "independent_ideal": ["research"], "current_assessment": ["research"],
    "plays": ["independent_ideal", "current_assessment"], "reviews": ["plays"],
    "provisional": ["reviews"], "challenge_research": ["provisional"],
    "source_checks": ["challenge_research"], "investment_cases": ["challenge_research"],
    "settlement": ["source_checks"],
    "final_source_changes": ["settlement"], "final_case_refresh": ["final_source_changes"],
    "consistency": ["final_source_changes"], "targeted_revision": ["consistency"],
    "commentary": ["targeted_revision"], "reader": ["commentary"],
}


def workflow_plan():
    return {"contract": "portfolio-work-plan-v1", "model_concurrency": 4,
        "nodes": {name: {"depends_on": deps, "status": "scope_pending", "request_count": None,
            "reason": "Scope depends on upstream evidence and decisions", "optional": name == "targeted_revision"}
            for name, deps in STAGES.items()},
        "estimate_status": "partial_scope", "remaining_seconds": None,
        "estimate_basis": "No wall-time promise before downstream scope and comparable provider timings are established."}


def plan_summary(plan):
    if not plan:
        return None
    terminal = {"complete", "with_limitations", "not_needed", "failed", "retained_partial"}
    nodes = plan["nodes"]
    result = {"contract": plan["contract"], "model_concurrency": plan["model_concurrency"],
        "nodes": {name: {key: value for key, value in row.items() if key not in {"cases", "batch_fact_ids"}}
                  for name, row in nodes.items()},
        "finished_stages": sum(row.get("status") in terminal for row in nodes.values()),
        "total_stages": len(nodes),
        "unscoped_stages": sum(row.get("status") == "scope_pending" for row in nodes.values()),
        "estimate_status": "partial_scope", "remaining_seconds": None,
        "estimate_basis": plan["estimate_basis"]}
    if nodes.get("reader", {}).get("status") == "complete":
        result.update(estimate_status="finished", remaining_seconds=0)
    return result


async def record_work(runtime, name, **fields):
    plan = runtime.partial.setdefault("work_plan", workflow_plan())
    plan["nodes"][name] = {**plan["nodes"].get(name, {}), **fields}
    # Plans are small, separate from the full research artifact.
    runtime.progress.work_plan = plan_summary(plan)
    if name == "reader" and fields.get("status") == "complete":
        plan.update(estimate_status="finished", remaining_seconds=0)
    await runtime.asave_request("work-plan:" + name, partial_records={"work_plan": plan})


async def check_and_develop_cases(evidence, cases, verify, develop, runtime):
    """Start a case when its observations finish, not when every case finishes."""
    condition = asyncio.Condition()
    state = {"evidence": evidence, "finished_ids": set(), "source_done": False}
    pending = list(enumerate(cases))
    results = {}
    await record_work(runtime, "investment_cases", status="admitted", request_count=len(cases),
        reason="Each case waits only for its own source-support dependencies",
        cases=[{"id": row["id"], "fact_ids": sorted(row["fact_ids"])} for row in cases])

    async def observations(current, finished):
        async with condition:
            state["evidence"] = current
            state["finished_ids"].update(finished)
            condition.notify_all()

    async def sources():
        result = await verify(observations)
        async with condition:
            state.update(evidence=result, source_done=True)
            condition.notify_all()
        return result

    async def worker():
        while True:
            async with condition:
                await condition.wait_for(lambda: not pending or state["source_done"] or any(
                    set(case["fact_ids"]) <= state["finished_ids"] for _, case in pending))
                if not pending:
                    return
                entry = next((entry for entry in pending if state["source_done"] or
                    set(entry[1]["fact_ids"]) <= state["finished_ids"]))
                pending.remove(entry)
                current = state["evidence"]
            index, case = entry
            results[index] = await develop(case, current)
            await runtime.asave_request("developed-case:" + case["id"],
                partial_records={"developed_cases": {case["id"]: results[index]}})

    source_task = asyncio.create_task(sources())
    tasks = [source_task, *(asyncio.create_task(worker()) for _ in range(min(2, len(cases))))]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    await record_work(runtime, "investment_cases", status="complete", completed=len(results))
    return source_task.result(), [results[i] for i in sorted(results)]
