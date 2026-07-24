"""LangGraph safety layer wrapped around the smolagents manager.

Mirrors the interrupt-and-resume shape from notebooks/02_langgraph_basics.ipynb, but uses the
dynamic `interrupt()` function (langgraph.types) instead of static `interrupt_before=[...]`,
because the approval step here needs to carry a *value* back in (which channel approved it,
what the decision was) rather than just resume a boolean already sitting on state.

Uses MemorySaver rather than a sqlite checkpointer: the Telegram bot poller and this graph run
in the same notebook process for a live demo, so in-memory persistence across the interrupt is
enough, and it avoids an extra `langgraph-checkpoint-sqlite` dependency.
"""

import json
import os
import uuid
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.types import Command, interrupt

STORE_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "store_data.json")

MARGIN_APPROVAL_THRESHOLD = 20.0


class DropshipState(TypedDict):
    raw_message: str
    image_path: str
    specs: dict
    market_price: float
    margin_pct: float
    description: str
    broadcast_copy: str
    approved: bool
    published: bool


def make_run_multi_agent_node(manager_agent, prompt_template: str):
    """Closure so the node can call the smolagents manager without workflow.py importing
    multi_agent_system.py directly (keeps the two modules independently testable)."""

    def run_multi_agent_node(state: DropshipState) -> dict:
        prompt = prompt_template.format(raw_message=state["raw_message"], image_path=state["image_path"])
        raw_result = manager_agent.run(prompt)
        result = raw_result if isinstance(raw_result, dict) else json.loads(raw_result)
        return {
            "specs": result["specs"],
            "market_price": float(result["market_price"]),
            "margin_pct": float(result["margin_pct"]),
            "description": result["description"],
            "broadcast_copy": result["broadcast_copy"],
        }

    return run_multi_agent_node


def evaluate_margin_node(state: DropshipState) -> dict:
    """Thin-margin listings (< 20%) are the risky/marginal case and get a human sanity-check
    before publishing; comfortably profitable listings (>= 20%) auto-approve."""
    if state["margin_pct"] >= MARGIN_APPROVAL_THRESHOLD:
        return {"approved": True}

    decision = interrupt(
        {
            "question": "Approve publishing this listing?",
            "title": state["specs"].get("title"),
            "market_price": state["market_price"],
            "margin_pct": state["margin_pct"],
        }
    )
    return {"approved": decision == "approve"}


def publish_node(state: DropshipState) -> dict:
    if not state["approved"]:
        return {"published": False}

    with open(STORE_DATA_PATH) as f:
        catalog = json.load(f)

    new_watch = {
        "id": f"w{uuid.uuid4().hex[:8]}",
        "title": state["specs"].get("title", "New Arrival"),
        "price": round(state["market_price"], 2),
        "image": "https://placehold.co/400x400/1a1a1a/d4af37?text=" + state["specs"].get("title", "New").replace(" ", "+"),
        "description": state["description"],
        "status": "published",
    }
    catalog.insert(0, new_watch)

    with open(STORE_DATA_PATH, "w") as f:
        json.dump(catalog, f, indent=2)

    return {"published": True}


def build_graph(manager_agent, prompt_template: str):
    builder = StateGraph(DropshipState)
    builder.add_node("run_multi_agent", make_run_multi_agent_node(manager_agent, prompt_template))
    builder.add_node("evaluate_margin", evaluate_margin_node)
    builder.add_node("publish", publish_node)

    builder.set_entry_point("run_multi_agent")
    builder.add_edge("run_multi_agent", "evaluate_margin")
    builder.add_edge("evaluate_margin", "publish")
    builder.add_edge("publish", END)

    return builder.compile(checkpointer=MemorySaver())


def resume_graph(graph, config: dict, decision: str) -> dict:
    """Shared resume path for both the Telegram callback and the local fallback in
    telegram_bot.py — the graph doesn't care which transport supplied the decision."""
    return graph.invoke(Command(resume=decision), config)
