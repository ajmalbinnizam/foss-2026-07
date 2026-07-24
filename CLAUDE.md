# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

Companion repo for a FOSS meetup talk ("Beyond the Unpredictable Loop: Building Production-Grade
Agentic Workflows with LangGraph and smolagents"), presented by Sreejith Surendran and Ajmal
Nizamudin. It is a set of four **Jupyter/Colab notebooks** — there is no application code, package
manifest, build system, linter, or test suite. All work happens inside notebook cells.

The live demo scenario is the **FOSS Contribution Matchmaker**: given a GitHub profile URL +
interests, it produces a personalised "Your First PR" plan. The scenario was deliberately chosen
because it needs live GitHub data and multi-step specialist reasoning — a single LLM call can't
replicate it (a prior "paste a repo URL, get a description" demo was rejected for exactly that
reason).

## Repo structure

```
notebooks/
  01_smolagents_basics.ipynb   study: CodeAgent vs ToolCallingAgent, @tool decorator
  02_langgraph_basics.ipynb    study: StateGraph, conditional routing, human-in-the-loop gates
  03_a2a_basics.ipynb          study: A2A protocol + the 3 specialist agents, standalone (no LangGraph wiring)
  foss_demo.ipynb              live audience demo — the only place the full LangGraph + A2A + smolagents pipeline is wired together
slides_export/slide_notes.md   slide-by-slide reference notes for the talk
Beyond_the_Unpredictable_Loop.pptx  the talk deck
watch-dropship-demo/          second, self-contained stage demo — see its own README.md; not wired into the FOSS Matchmaker pipeline above
```

`watch-dropship-demo/` is an independent demo (a supplier-signal → multi-agent pricing/copy →
LangGraph approval-gate → storefront pipeline) for a different talk. It has its own
`requirements.txt`, `.env.example`, and `README.md`, and shares nothing at runtime with the
`notebooks/` pipeline described below beyond the same `load_key()` convention and Groq/LiteLLM
model choice.

Notebooks 01-03 are meant to be studied in order; each is self-contained (installs its own deps,
loads its own API key) so it can be opened standalone in Colab. `03_a2a_basics.ipynb` deliberately
stops after defining the 3 A2A agents (`RepoFinderAgent`, `ComplexityRaterAgent`,
`OnboardingGuideAgent`) — it does not wire them into a LangGraph pipeline, since that would just
duplicate `foss_demo.ipynb`. `foss_demo.ipynb` inlines its own copies of the same three agent
classes (there is no shared `.py` module) and is the only notebook that builds the full
`MatchmakerState` graph. When changing an agent's behavior (e.g. `OnboardingGuideAgent`'s prompt
or tools), update it in **both** `03_a2a_basics.ipynb` and `foss_demo.ipynb` to keep the agent
definitions in sync; the LangGraph wiring itself only needs to change in `foss_demo.ipynb`.

## Running notebooks

These notebooks are designed to run in Google Colab (see badges in README.md) or a local Jupyter
kernel. There is no requirements.txt — each notebook installs its own dependencies in its first
code cell via `pip install`:

- `01_smolagents_basics.ipynb`: `smolagents[toolkit]`, `litellm`
- `02_langgraph_basics.ipynb`: `langgraph`, `grandalf` (for ASCII graph rendering)
- `03_a2a_basics.ipynb` / `foss_demo.ipynb`: `smolagents[toolkit]`, `litellm`, `langgraph`, `requests`

API keys are loaded via a `load_key()` helper repeated in each notebook, which tries in order:
already-set env var → Colab Secrets (`google.colab.userdata`) → local `.env` file (via
`python-dotenv`) → interactive `getpass` prompt. Required: `GROQ_API_KEY` (LLM inference, via
Groq's free Llama 3.3 70B tier — no HuggingFace account needed). Optional: `GITHUB_TOKEN` (raises
GitHub API rate limit from 60/hr to 5000/hr; matters when many people run the demo at once). Copy
`.env.example` to `.env` for local runs — never paste raw key values into chat or commit `.env`.

There is no automated test suite; correctness is validated by running notebook cells top-to-bottom
and inspecting printed output (agent traces, graph ASCII/mermaid diagrams, final contribution
plan).

## Architecture (the Matchmaker pipeline)

The demo is a **hybrid** of two frameworks plus a protocol, each with a distinct job — this
division of responsibility is the point of the talk, not an implementation detail to gloss over:

- **LangGraph** — the macro-orchestrator. A `StateGraph` over a single `MatchmakerState`
  `TypedDict` routes deterministically between nodes (`parse_input` → `analyze_profile` →
  `repo_discovery` → `complexity_rating` → `onboarding` → `format_plan` → `END`). LangGraph itself
  never calls an LLM — every node is plain Python (string parsing, GitHub REST calls via the
  shared `gh_get()` helper). This determinism is intentional: the graph must be auditable and
  can't loop unpredictably.
- **A2A protocol** (mocked in-process) — three specialist agents, each implementing a common
  `A2AAgent` base (`agent_card` property + `_handle(task)` + `send_task()`), consuming/producing
  `A2ATask` dataclasses with `state`/`artifacts`. In production each would be an independent HTTP
  service exposing `/.well-known/agent.json`; here they're plain Python classes called in-process,
  but the interface is meant to look identical either way:
  - `RepoFinderAgent` — searches the GitHub search API for repos matching skill profile + experience level.
  - `ComplexityRaterAgent` — rates a repo beginner/intermediate/advanced using deterministic heuristics, no LLM.
  - `OnboardingGuideAgent` — the one LLM-touching agent. Wraps a smolagents `CodeAgent` internally to fetch and summarize `CONTRIBUTING.md` + starter issues.
- **smolagents** — the only place an LLM actually runs, and only inside `OnboardingGuideAgent`.
  Uses `CodeAgent` (writes Python as its action, not JSON tool calls) via `LiteLLMModel` pointed at
  `groq/llama-3.3-70b-versatile`. Tools are plain typed Python functions decorated with `@tool`,
  where the docstring becomes the prompt schema.

Call chain: `LangGraph node → A2AAgent.send_task() → (OnboardingGuideAgent only) CodeAgent.run() → @tool functions → GitHub REST API`.

When extending this demo, preserve the boundary: routing/control-flow logic belongs in LangGraph
nodes (deterministic Python), and only `OnboardingGuideAgent`'s inner CodeAgent should make LLM
calls. Adding LLM calls into LangGraph nodes or into `RepoFinderAgent`/`ComplexityRaterAgent`
would undercut the "macro-manager vs micro-executor" architecture the talk is demonstrating.
