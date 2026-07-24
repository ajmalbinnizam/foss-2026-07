# Beyond the Unpredictable Loop — Slide Notes
### Quick reference for study alongside the notebooks

---

## Slide 1 — Title
**Beyond the Unpredictable Loop**
Building Production-Grade Agentic Workflows with LangGraph and smolagents

Presenters: Sreejith Surendran (Senior Manager, IBS) · Ajmal Nizamudin (Senior Data Engineer, IBS)

---

## Slide 3 — The Fallacy of Pure Autonomy

**1. Runaway Loops**
Purely autonomous loops look magic in demos, but crash in production. Unmonitored LLMs will eventually get stuck looping on errors, ballooning token usage and burning APIs rapidly.

**2. Brittle JSON Structures**
Historically, tool-calling forces models to structure outputs as strict JSON. When a model hallucinates a missing bracket or a faulty key, the parsing system crashes completely.

---

## Slide 4 — High API Latency in JSON Chains

JSON execution loops require back-and-forth roundtrips to evaluate conditions.

In the "Code-as-Actions" framework, logic runs in a **single turn**, reducing runtime latency by **up to 75%**.

---

## Slide 5 — The Hybrid Blueprint

**Macro-control** for strict boundaries combined with **micro-execution** for local operational autonomy.

> LangGraph handles routing. smolagents handles execution.

---

## Slide 6 — LangGraph: The Macro-Manager

| Feature | What it does |
|---------|-------------|
| **State Graphs** | Strict, predictable routing via directed graph architecture instead of raw LLM decisions |
| **Central State** | Single auditable `TypedDict` context passed through each node — enables backtracking and monitoring |
| **Human Gates** | `interrupt_before` breakpoints that pause execution for human approval before writing to production |

---

## Slide 7 — smolagents: The Micro-Executor

| Feature | What it does |
|---------|-------------|
| **Code-as-Actions** | LLM writes Python code inside a local runtime instead of outputting JSON blobs |
| **AST Sandboxing** | Checks dynamically written code with an Abstract Syntax Tree before execution — blocks dangerous OS calls |
| **Self-Correction** | Captures runtime exceptions and feeds tracebacks back to the model for instant code fixing |

---

## Slide 8 — Framework Comparison

| Capability | CrewAI | LangGraph | smolagents |
|------------|--------|-----------|------------|
| Control Flow | Autonomous routing | Deterministic state machine | Autonomous scripting |
| Action Execution | JSON tool schemas | Custom code nodes | Runtime code generation |
| Safety Level | Low (infinite loops possible) | High (strict edges) | Medium (AST sandboxed) |
| Optimal Use | Text-heavy agent collabs | Enterprise routing & states | Efficient computation & data |

---

## Slide 9 — Lifecycle of an Orchestrated Task

```
1. Graph Trigger    LangGraph initiates node, passes state to context
        ↓
2. Script Action    smolagent writes a 4-line Python script to process data
        ↓
3. Safe Execution   Code runs inside AST-sandboxed parser → structured result dict
        ↓
4. State Handoff    LangGraph parses values, updates state, routes predictably
```

---

## Slide 10 — How smolagents Tools Work

Tools are defined with just a Python function + type hints + docstring:

```python
from smolagents import tool

@tool
def fetch_logs(service: str, count: int = 5) -> str:
    """Queries raw system error logs.

    Args:
        service: The service name to query logs for.
        count: Number of log lines to return.
    """
    logs = db.query(service)
    return "\n".join(logs[-count:])
```

- Uses standard type annotations (`count: int`) — no JSON schema required
- Docstring becomes the prompt schema the LLM reads
- Saves development time, keeps code simple and readable

---

## Slide 11 — Code-as-Actions is Hyper-Efficient

By letting the LLM write self-contained loops locally inside an AST interpreter, you eliminate multi-turn network roundtrips to the cloud model API.

High-performance agent nodes complete in **single-turn generations**, dramatically minimising overall operational overhead.

**Benchmark:** Code agents use ~30% fewer steps than JSON tool-calling agents on the same tasks.

---

## Slide 12 — Call to Action

> Build deterministic, reliable agent workflows today.
> Start with `notebooks/01_smolagents_basics.ipynb`

---

## Notebook Study Path — Why Each One Matters

**`01_smolagents_basics.ipynb`**
Shows the core trick behind Code-as-Actions: the LLM writes real Python — filters, loops, conditions — instead of one rigid JSON call per action. This is *why* smolagents needs fewer round trips than classic tool-calling.

**`02_langgraph_basics.ipynb`**
Turns branching and human approval into an explicit, visualisable graph instead of nested if/else buried in a function — and shows execution genuinely pausing mid-run and resuming later with a real decision, not a hardcoded one.

**`03_a2a_basics.ipynb`**
Introduces the A2A protocol as a common interface (Agent Card + Task) so independently-built specialist agents can be called the same way regardless of what's inside them — like microservices, but for agents.

**`foss_demo.ipynb` — the FOSS Contribution Matchmaker**
This is where it all clicks together. It's not a new concept — it's LangGraph, A2A, and smolagents wired into one real, runnable system, so you see the whole architecture working end-to-end for the first time. **Study this one to get the core idea of how everything fits.**

---

## Live Demo: Watch Dropshipping Pipeline

The Matchmaker teaches the architecture. **This is the actual live stage demo** — the same
patterns (multi-agent delegation + a LangGraph human gate), but with a real supplier signal,
a real storefront, and a real approval tapped live on stage.

### The Flow (easy-to-explain version)

```
Supplier message arrives (WhatsApp/Telegram text + photo)
        ↓
Manager Agent (smolagents CodeAgent) delegates to 3 specialists
        ↓
  1. Ingestion Agent        → extracts title, cost, color, dial type
  2. Market Research Agent  → searches the web, computes margin %
  3. Copywriter Agent       → writes storefront + broadcast copy
        ↓
LangGraph Guardrail Node — checks: is margin > 20%?
        │
        ├─ margin ≤ 20%  → auto-approved, no pause
        │
        └─ margin > 20%  → PAUSE (interrupt()) → Telegram approval request
                                    ↓
                       Human taps [Approve] live on stage
                                    ↓
                       Graph resumes — Command(resume="approve")
                                    ↓
                       Publish node writes store_data.json
                                    ↓
        Storefront (localhost:5000) updates live in front of the audience
```

### Points to Tell (stage narration)

1. "A supplier just sent us a deal over WhatsApp — just raw text and a photo, nothing structured."
2. "Three agents split the work — one cleans up the message, one checks the real market price, one writes the sales pitch. Nobody wrote if/else to route between them — the manager agent decided that."
3. "Here's the guardrail: if the margin looks too good to be true — over 20% — the system will **not** auto-publish. It pauses and asks a human."
4. "That's the same `interrupt()` pattern from `02_langgraph_basics.ipynb` — execution genuinely freezes mid-run and waits."
5. "I'll approve this live, right now, from my phone." *(tap the Telegram button)*
6. "Watch it resume — the decision gets handed back into the exact paused state, and the pipeline finishes."
7. "The storefront just updated live at `localhost:5000` — zero manual data entry, one human decision."

**The punchline for the audience:** the pattern you just watched — pause, notify a human, resume with their decision — is *exactly* what you built yourself in `02_langgraph_basics.ipynb`. This is that same idea, on stage, with real consequences.
