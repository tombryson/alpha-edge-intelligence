import asyncio
import tempfile
import unittest
from pathlib import Path

from backend.scenario_router.event_queue import ScenarioRouterEventQueue


async def _wait_for_status(queue, event_key, expected, timeout=1.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if queue.get(event_key).get("status") == expected:
            return queue.get(event_key)
        await asyncio.sleep(0.01)
    raise AssertionError(f"Event {event_key} did not reach {expected}: {queue.get(event_key)}")


def test_stopped_queue_can_restart_on_a_new_event_loop(tmp_path):
    queue = ScenarioRouterEventQueue(tmp_path)

    async def first_lifespan():
        async def waiting(_payload):
            await asyncio.sleep(60)
        await queue.start(waiting)
        await queue.enqueue("restart-event", {"value": 1})
        await _wait_for_status(queue, "restart-event", "processing")
        await queue.stop()

    async def second_lifespan():
        async def complete(payload):
            return payload
        await queue.start(complete)
        await _wait_for_status(queue, "restart-event", "succeeded")
        # Bind the now-empty queue to this loop too, to cover clean shutdown.
        await asyncio.sleep(0.01)
        await queue.stop()

    asyncio.run(first_lifespan())
    asyncio.run(second_lifespan())


class ScenarioRouterEventQueueTests(unittest.IsolatedAsyncioTestCase):
    async def test_persists_then_processes_event(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = ScenarioRouterEventQueue(Path(directory))
            await queue.enqueue("gmail-1", {"gmail_message_id": "gmail-1"})

            seen = []

            async def processor(payload):
                seen.append(payload["gmail_message_id"])
                return {"status": "ok", "ticker": "ASX:BRK"}

            await queue.start(processor)
            record = await _wait_for_status(queue, "gmail-1", "succeeded")
            await queue.stop()

            self.assertEqual(seen, ["gmail-1"])
            self.assertEqual(record["result"]["status"], "ok")

    async def test_retries_transient_failure_then_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            queue = ScenarioRouterEventQueue(
                Path(directory),
                max_attempts=2,
                retry_delay_seconds=0.01,
            )
            calls = 0

            async def processor(payload):
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise RuntimeError("temporary upstream failure")
                return {"status": "ok"}

            await queue.start(processor)
            await queue.enqueue("gmail-2", {"gmail_message_id": "gmail-2"})
            record = await _wait_for_status(queue, "gmail-2", "succeeded")
            await queue.stop()

            self.assertEqual(calls, 2)
            self.assertEqual(record["attempts"], 2)

    async def test_start_recovers_an_unfinished_event_from_disk(self):
        with tempfile.TemporaryDirectory() as directory:
            first_queue = ScenarioRouterEventQueue(Path(directory))
            await first_queue.enqueue("gmail-3", {"gmail_message_id": "gmail-3"})

            recovered_queue = ScenarioRouterEventQueue(Path(directory))

            async def processor(payload):
                return {"status": "ok", "ticker": "ASX:EIQ"}

            await recovered_queue.start(processor)
            record = await _wait_for_status(recovered_queue, "gmail-3", "succeeded")
            await recovered_queue.stop()

            self.assertEqual(record["result"]["ticker"], "ASX:EIQ")
