"""P03 demo-agent integration (T03.080, 16 §2).

The real demo card + real prompts + real tool registry, driven by scripted
FakeProvider sequences: a 3-step tool loop, then kill-after-step-2 with a
resume that completes without repeating any tool call.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

import sots.agents.tools  # noqa: F401 (register every tool)
from sots.agents.base import AgentContext, BaseAgent
from sots.agents.cards import load_cards
from sots.agents.failsafes.f16_killswitch import clear, engage
from sots.agents.tools.base import registered_tools
from sots.config import load_settings
from sots.models.agents import AgentCard, BudgetSlice
from sots.providers.context_pack import ContextPack
from sots.providers.fake import FakeProvider
from sots.providers.router import RoutingConfig, RoutingTask, load_routing
from sots.storage import db as storage_db
from sots.storage import repo as storage_repo
from sots.storage.db import Connection

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class DemoInputs(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    goal: str


class DemoOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    answer: str


class DemoAgent(BaseAgent[DemoInputs, DemoOutput]):
    output_model = DemoOutput

    def build_step_variables(self, ctx: AgentContext) -> dict[str, str]:
        assert isinstance(ctx.inputs, DemoInputs)
        return {"goal": ctx.inputs.goal}


def _demo_card() -> AgentCard:
    """The real `config/agents/_demo/demo_agent.yaml`, validated for real."""
    cards = load_cards(
        CONFIG_DIR / "agents",
        prompts_dir=PROMPTS_DIR,
        routing=load_routing(CONFIG_DIR / "routing.yaml"),
        tools=registered_tools(),
    )
    return cards["demo_agent"]


def _harness(tmp_path: Path) -> tuple[Connection, Path]:
    conn = storage_db.connect(tmp_path / "t.db")
    storage_db.migrate(conn)
    return conn, tmp_path / "data"


def _agent(
    tmp_path: Path, conn: Connection, fake: FakeProvider, card: AgentCard
) -> DemoAgent:
    settings = load_settings(CONFIG_DIR, env_file=None)
    routing = RoutingConfig(
        fallback_order=[],
        tasks={
            "classify.unit": RoutingTask(
                provider="fake", temperature=0.0, max_output_tokens=600
            )
        },
    )
    return DemoAgent(
        settings=settings,
        routing=routing,
        registry={"fake": fake},
        conn=conn,
        prompts_dir=PROMPTS_DIR,
        data_dir=tmp_path / "data",
    )


def _ctx(card: AgentCard, run_id: str, key: str = "demo1") -> AgentContext:
    return AgentContext(
        run_id=run_id,
        act="I",
        card=card,
        inputs=DemoInputs(goal="run the scripted demo loop"),
        context_pack=ContextPack(task="classify.unit", system_role="", pieces=[]),
        budget=BudgetSlice(scope="test", tokens_allowed=60000, cost_allowed=10.0),
        checkpoint_key=key,
    )


def _tool_json(tool: str, args: dict[str, Any], delay_s: float = 0.0) -> dict[str, Any]:
    return {
        "text": json.dumps(
            {"type": "tool", "tool": tool, "args": args,
             "thought": "reasoning", "final": None}
        ),
        "delay_s": delay_s,
    }


def _final_json(final: dict[str, Any], delay_s: float = 0.0) -> dict[str, Any]:
    return {
        "text": json.dumps(
            {"type": "final", "tool": None, "args": None,
             "thought": "done", "final": final}
        ),
        "delay_s": delay_s,
    }


async def test_demo_agent_three_step_loop(tmp_path: Path) -> None:
    conn, _ = _harness(tmp_path)
    try:
        card = _demo_card()
        fake = FakeProvider()
        fake.script_default("classify.unit", [
            _tool_json("compute", {"expression": "2 + 3"}),
            _tool_json("compute", {"expression": "10 * 5"}),
            _final_json({"answer": "5 and 50"}),
        ])
        result = await _agent(tmp_path, conn, fake, card).run(_ctx(card, "r1"))
        assert result.status == "ok"
        assert isinstance(result.output, DemoOutput)
        assert result.output.answer == "5 and 50"
        assert len(fake.calls) == 3
        runs = storage_repo.list_agent_runs(conn)
        assert len(runs) == 1 and runs[0].steps == 3
    finally:
        conn.close()


async def _wait_for_step(
    conn: Connection, key: str, step: int, timeout_s: float = 30.0
) -> None:
    """Poll the checkpoint until `step` is saved (fail, never hang)."""
    waited = 0.0
    while waited < timeout_s:
        row = storage_repo.get_checkpoint(conn, key)
        if row is not None:
            state = row["state"].get("state", {})
            if isinstance(state, dict) and state.get("step", 0) >= step:
                return
        await asyncio.sleep(0.02)
        waited += 0.02
    raise AssertionError(f"checkpoint {key!r} never reached step {step}")


async def test_demo_agent_kill_resume_no_repeats(tmp_path: Path) -> None:
    conn, data_dir = _harness(tmp_path)
    try:
        card = _demo_card()
        fake = FakeProvider()
        fake.script_default("classify.unit", [
            _tool_json("compute", {"expression": "2 + 3"}, delay_s=0.5),
            _tool_json("compute", {"expression": "10 * 5"}, delay_s=0.5),
            _final_json({"answer": "resumed"}, delay_s=0.5),
        ])
        first = asyncio.create_task(
            _agent(tmp_path, conn, fake, card).run(_ctx(card, "r1"))
        )
        await _wait_for_step(conn, "demo1", 1)
        engage(data_dir)  # lands during step 2; step 3 never starts
        result1 = await first
        assert result1.status == "cancelled"
        assert len(fake.calls) == 2

        clear(data_dir)
        result2 = await _agent(tmp_path, conn, fake, card).run(_ctx(card, "r2"))
        assert result2.status == "ok"
        assert isinstance(result2.output, DemoOutput)
        assert result2.output.answer == "resumed"
        assert len(fake.calls) == 3  # step 3 only: no repeated tool calls

        by_run = {run.run_id: run for run in storage_repo.list_agent_runs(conn)}
        assert by_run["r1"].status == "cancelled" and by_run["r1"].steps == 2
        assert by_run["r2"].status == "ok" and by_run["r2"].steps == 3
    finally:
        conn.close()
