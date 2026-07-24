"""3 smolagents (Ingestion, MarketResearch, Copywriter) wired under a manager CodeAgent.

Current smolagents (1.26+) has no `ManagedAgent` wrapper class — a sub-agent becomes
"managed" simply by giving it a `name` + `description` and passing it in the parent's
`managed_agents=[...]` list. The manager then calls it like any other tool.
"""

import os

from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel, ToolCallingAgent


def load_key(name: str):
    if os.environ.get(name):
        print(f"{name} loaded from environment")
        return
    try:
        from google.colab import userdata

        os.environ[name] = userdata.get(name)
        print(f"{name} loaded from Colab Secrets")
        return
    except Exception:
        pass
    try:
        from dotenv import load_dotenv

        load_dotenv()
        if os.environ.get(name):
            print(f"{name} loaded from .env file")
            return
    except ImportError:
        pass
    import getpass

    os.environ[name] = getpass.getpass(f"{name}: ")


def build_manager_agent() -> CodeAgent:
    load_key("GROQ_API_KEY")
    model = LiteLLMModel(model_id="groq/llama-3.3-70b-versatile")

    ingestion_agent = ToolCallingAgent(
        tools=[],
        model=model,
        name="ingestion_agent",
        description=(
            "Sanitizes a raw supplier message (text + optional image path) into a "
            "structured spec: title, base_cost (float, USD), color, dial_type. "
            "Always return the specs as a JSON object."
        ),
    )

    market_research_agent = CodeAgent(
        tools=[DuckDuckGoSearchTool()],
        model=model,
        name="market_research_agent",
        description=(
            "Given a product title and base_cost, searches the web for a comparable "
            "market price and computes margin_pct = (market_price - base_cost) / "
            "market_price * 100. Returns market_price and margin_pct."
        ),
    )

    copywriter_agent = CodeAgent(
        tools=[],
        model=model,
        name="copywriter_agent",
        description=(
            "Given product specs, market_price, and margin_pct, writes a short storefront "
            "product description and a high-converting Telegram/WhatsApp broadcast message."
        ),
    )

    manager_agent = CodeAgent(
        tools=[],
        model=model,
        managed_agents=[ingestion_agent, market_research_agent, copywriter_agent],
        name="manager_agent",
        description="Orchestrates ingestion, market research, and copywriting for a new supplier drop.",
    )
    return manager_agent


MANAGER_PROMPT_TEMPLATE = """A new supplier signal has arrived:

Raw message: {raw_message}
Image path: {image_path}

1. Delegate to ingestion_agent to extract structured specs (title, base_cost, color, dial_type).
2. Delegate to market_research_agent to find a comparable market price and compute margin_pct.
3. Delegate to copywriter_agent to write the storefront description and broadcast copy.

Return your final answer as a single JSON object with keys:
specs (object), market_price (float), margin_pct (float), description (string), broadcast_copy (string).
"""
