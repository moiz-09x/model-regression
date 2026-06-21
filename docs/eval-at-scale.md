# Eval at Scale — Applying This System to Larger Production Systems

This document covers how the eval pattern built in this project scales to existing production systems, multi-agent architectures, and agentic workflows. It also lists the production tooling that teams use instead of building everything from scratch.

---

## Plugging into an existing system

When the system under test already exists, you don't change it — you add an eval harness alongside it. The production code is untouched. The harness wraps each LLM call in a testable interface.

```
production_system/
  agents/
    classifier.py
    retriever.py
    responder.py

eval/                          ← you add this
  golden_datasets/
    classifier_cases.json
    end_to_end_cases.json
  runs/
  src/
    harness.py                 ← wraps each agent in a standard interface
    scorer.py
    comparator.py
    reporter.py
```

The key move is finding the **seams** — points where a defined input enters and a structured output exits. Those seams are what you write golden datasets against.

---

## Multi-agent systems

### The two eval levels you always need

**Unit eval** — test each agent independently with crafted inputs and check its output in isolation. This tells you *which* agent broke.

**End-to-end eval** — run a test case through the full pipeline and check the final output. This tells you if the *combination* broke.

You need both. A system where every individual agent scores 95% can still fail 15% of the time end-to-end because each agent's variance compounds. Unit evals and end-to-end evals catch different failure modes.

### Defining "correct behavior" for agents that take actions

For classifiers and generators, correct behavior is straightforward — you compare output to expected output. For agents that take *actions* (call APIs, write to databases, send messages), you have two approaches:

**Mock and check intent** — mock all external side effects, run the agent, and check what actions it *attempted*. Did it call the right tool? With the right arguments? In the right order? This is more controllable and produces reproducible tests.

**Evaluate final state** — run the agent against a real or sandboxed environment and check whether the system ended up in the right state. More realistic but harder to set up and debug.

Most teams start with mocking. You move to state-based evaluation when you need higher confidence in production-like scenarios.

### Attribution — knowing which agent caused a failure

When a multi-agent pipeline fails an end-to-end test, your eval result tells you *that* something went wrong. It doesn't tell you *where*. Attribution requires **tracing** — recording every intermediate input and output across all agents for a given run. Without tracing, debugging a multi-agent failure means guessing.

See the tooling section below for tracing options.

---

## Agentic workflows

Agentic systems don't have a fixed input/output structure — the agent decides what steps to take. This breaks the simple "run input, check output" eval pattern. Two approaches:

**Outcome evaluation** — only check the final result, ignore how the agent got there. Simple to implement. Blind to reasoning failures: the agent might reach the right answer through broken reasoning and fail differently on the next similar input.

**Trajectory evaluation** — check the *sequence of steps* the agent took at each decision point. Was this the right tool call at step 2? Was the reasoning at step 4 sound? More expensive to build and score, but catches systematic reasoning problems that outcome evaluation misses.

LLM-as-judge (the same pattern used in this project for summary scoring) extends naturally to trajectory evaluation. You give the judge the full chain of reasoning and ask it to score individual decisions. The golden dataset for trajectory eval includes not just the expected final output but the expected sequence of steps.

---

## CI/CD at scale

The trigger logic becomes a matrix rather than a single rule:

| What changed | What to run |
|---|---|
| Prompt for Agent A | Agent A unit eval + end-to-end eval |
| Prompt for Agent B | Agent B unit eval + end-to-end eval |
| Orchestration logic | End-to-end eval only |
| Golden dataset | All evals that reference it |
| Scoring/eval infrastructure | Re-run last saved baseline to verify no eval bugs |

Each agent has its own eval suite. The orchestration layer has a separate end-to-end suite. CI triggers the right combination based on what files changed — same `paths` filter pattern, just applied per-suite.

---

## Production tooling

Rather than building everything from scratch, most teams use a combination of the following. Each tool covers a different part of the problem.

### Observability and tracing

These tools record every LLM call in production — inputs, outputs, latency, token usage, costs — and let you trace multi-agent runs step by step.

**[Langfuse](https://langfuse.com)** — open source, self-hostable. Strong multi-agent tracing, dataset management, and built-in eval runner. Works with any LLM provider. Good starting point for most teams.

**[Arize](https://arize.com)** — production ML observability with strong LLM support. Better for teams already using Arize for non-LLM models. More enterprise-focused.

**[LangSmith](https://smith.langchain.com)** — built by LangChain, tightly integrated with LangChain and LangGraph. Best choice if your agents are built on those frameworks. Has dataset management and online eval built in.

**[Helicone](https://helicone.ai)** — lightweight proxy that sits in front of any LLM API and logs every call with zero code changes. Useful for fast instrumentation of existing systems.

### Eval frameworks

These handle the scoring and dataset management layer — the equivalent of `src/scorer.py`, `src/evaluator.py`, and `data/` in this project.

**[DeepEval](https://github.com/confident-ai/deepeval)** — general-purpose eval framework. Pre-built metrics for hallucination, answer relevancy, contextual precision, bias, toxicity. Has a CI integration and a hosted dashboard. Good for teams that don't want to write their own scorer.

**[RAGAS](https://github.com/explodinggradients/ragas)** — focused specifically on RAG pipelines. Metrics: faithfulness, answer relevancy, context precision, context recall. Not useful for classification tasks like this project, but essential if your system retrieves documents before generating.

**[Braintrust](https://www.braintrust.dev)** — eval platform with dataset versioning, experiment tracking, and LLM-as-judge built in. Closer to what we built here but fully hosted. Good for teams that want the infrastructure managed.

**[Promptfoo](https://www.promptfoo.dev)** — prompt testing and red-teaming tool. Strong for adversarial testing, jailbreak detection, and comparing outputs across models. Complements a regression eval rather than replacing it.

### When to build vs when to use a tool

Build custom (like this project) when:
- You need full control over the eval logic
- You want to deeply understand how eval works before abstracting it
- Your eval criteria are highly specific and don't map to pre-built metrics

Use a framework when:
- You need standard metrics (hallucination, relevancy, toxicity) quickly
- You're working on a RAG system (RAGAS)
- You want tracing and eval in one platform (Langfuse, LangSmith)
- You need a team-visible dashboard without building the UI yourself

The pattern in this project — golden dataset, LLM-as-judge, diff against baseline, CI gate — is the same pattern these tools implement. Understanding it from scratch means you can evaluate any tool's tradeoffs and adapt when the tool doesn't fit.

---

## Practical approach for getting started on an existing system

Don't try to eval everything at once. The pattern that works:

1. Find the agent or LLM call that changes most often or fails most visibly in production
2. Build a golden dataset for just that one — 20–30 cases is enough to start
3. Get the eval loop running for that single agent: run, score, diff, alert
4. Add unit evals for adjacent agents as you have time
5. Add end-to-end evals once individual agent evals are stable
6. Add tracing when debugging multi-agent failures becomes a bottleneck

The core loop (golden dataset → eval run → diff → alert) stays the same regardless of system complexity. The complexity is in curating good golden datasets and deciding what "correct behavior" means for each agent — not in the infrastructure.
