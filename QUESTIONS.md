# Questions and Answers

This document consolidates the strongest answers from several model outputs into one practical version for the
`aire-k8s` stack.

## 1. How could we handle "agent got stuck" scenarios?

Handle this as a bounded workflow problem.

Recommended controls:

- Set hard limits for runtime, LLM turns, tool calls, retries, and total token budget.
- Add per-tool timeouts and retry only idempotent tool calls, preferably with backoff.
- Use a watchdog or heartbeat check to detect runs that make no progress.
- Persist checkpoints so failed runs can be retried or resumed safely.
- Send stuck runs to a failed-task/dead-letter state and optionally escalate to human review.
- Emit metrics and traces for stuck runs, tool latency, retry count, and final failure reason.

The desired behavior is not "wait forever"; it is "stop safely, explain why, and make retry/resume possible."

## 2. Any automatic timeout or circuit breaker patterns from this framework?

Partially. The stack provides useful primitives, but full agent-level circuit breaking still needs explicit design.

Available primitives:

- `kagent` model configs can define provider parameters such as `timeout` and `maxTokens`.
- MCP server resources can define tool-server timeouts.
- Kubernetes gives readiness/liveness probes and pod restarts.
- `agentgateway` can apply request limits, token limits, retries, provider health checks, and failover.
- Gateway/Envoy health policies can evict providers through passive health checks or outlier detection on failures such
  as `5xx`, timeouts, or `429`.

Still implement explicitly:

- max agent turns
- max tool-call depth
- max cumulative tokens per task
- max cumulative cost per task
- retry budget
- stuck-run state and human escalation path

## 3. How does kgateway handle model failover?

For LLM traffic in this stack, use `agentgateway`/AI gateway routing. The common pattern is priority-based failover.

Example:

```text
priority 0: OpenAI
priority 1: Claude
priority 2: local vLLM/Ollama model
```

Traffic goes to the highest-priority healthy provider. If that provider fails, times out, or returns rate-limit errors,
the gateway can route to the next provider. A health policy defines what counts as unhealthy, for example:

```text
response.code >= 500 || response.code == 429
```

Weighted routing can also be used for gradual migration or canary testing between providers.

## 4. Can we automatically switch from OpenAI to Claude to a local model?

Yes, if the models are exposed behind a gateway or common model abstraction.

Recommended pattern:

- Put OpenAI, Anthropic, and local OpenAI-compatible models behind one gateway.
- Give the agent one stable endpoint/model name.
- Configure provider priority, weights, and health-based failover at the gateway.
- Keep each provider key in Kubernetes Secrets.
- Decide which events trigger fallback: outage, timeout, `429`, budget breach, or latency threshold.
- Confirm the fallback model supports the required capabilities, especially tool calling, streaming, and structured
  outputs.

Directly in `kagent`, an agent usually references one `ModelConfig`. Multiple `ModelConfig` resources are possible, but
automatic cross-provider fallback is cleaner at the gateway layer.

## 5. Could we seamlessly handle response formats from these providers?

Mostly, but only if we standardize the contract.

Providers differ in request shape, tool-call format, streaming events, structured output support, error payloads, and
usage reporting. To make switching safe:

- Prefer one normalized API contract, usually OpenAI-compatible chat/tool calling.
- Use a gateway or adapter layer to normalize provider-specific differences.
- Avoid provider-specific response features in portable agents.
- Enforce JSON schema or structured outputs for business-critical responses.
- Test tool calling and streaming separately for each provider.

The gateway can hide many differences, but "seamless" still depends on using the common subset intentionally.

## 6. Can we version the agents built from kagent?

Yes. kagent agents are Kubernetes resources, so they can be versioned like other Kubernetes manifests.

Recommended approach:

- Store `Agent`, `ModelConfig`, `MCPServer`, prompts, and related policy YAML in Git.
- Review changes through PRs.
- Tag releases.
- Add labels or annotations such as `app.kubernetes.io/version`.
- Pin prompt, model, tool, and MCP server versions where possible.
- Use immutable names for major versions, for example `website-agent-v1` and `website-agent-v2`.
- Roll back by reverting Git and reapplying the previous manifest.

The Kubernetes resource is the runtime object; Git should be the source of truth.

## 7. Any blue/green or canary deployment patterns for agents?

Yes. Use normal Kubernetes and gateway traffic patterns.

Patterns:

- Blue/green: run `agent-v1` and `agent-v2` side by side, then switch the route.
- Canary: send a small percentage of traffic to the new agent.
- Header-based testing: route only test users or requests with a specific header to the new agent.
- Shadow testing: copy traffic to a new agent and evaluate the result without returning it to users.
- Promote or roll back based on error rate, latency, cost, tool failures, and answer-quality checks.

For custom ADK agents deployed as regular Kubernetes workloads, Argo Rollouts, Gateway API, service mesh routing, or
gateway weights can provide the traffic split.

## 8. What is the `fastmcp-python` framework?

FastMCP is a Python framework for building MCP servers with minimal protocol boilerplate.

It lets developers expose Python functions as MCP tools using decorators, type hints, and docstrings. It can also expose
resources and prompts. In practice, it is useful for quickly turning internal APIs, scripts, search functions, database
lookups, or Kubernetes helpers into MCP tools.

In the kagent ecosystem, `kmcp` can scaffold a FastMCP Python project.

## 9. Is it the easiest path to MCP?

For Python teams, often yes.

FastMCP is usually the fastest path from "I have a Python function" to "I have an MCP tool server." It handles schema
generation, validation, protocol negotiation, and transport details.

It is not always the best path:

- Use an existing MCP server if one already fits.
- Use an OpenAPI-to-MCP adapter if the source is already an HTTP API.
- Use the TypeScript MCP SDK if the team is TypeScript-first.
- Add production concerns separately: auth, logging, timeouts, packaging, deployment, and rate limits.

## 10. FinOps: how much control can I have?

You can have strong control, but not absolute control, if all model traffic goes through one managed path.

Control points:

- model selection
- provider fallback order
- request rate limits
- token rate limits
- per-agent or per-tenant quotas
- max output tokens
- budget-aware routing
- usage logging, chargeback tags, and team/environment policies

The important rule is to avoid direct provider calls from many places. Route calls through a gateway or shared model
client so cost controls are enforceable.

## 11. Token-level or per-agent-level tracking?

Both are possible.

Token-level tracking:

- Track prompt tokens, completion tokens, total tokens, model, provider, latency, and request outcome.
- Enforce max output tokens and token-based rate limits.
- Export usage as metrics or structured events.

Per-agent tracking:

- Give each agent a stable identity through route, namespace, API key, JWT claim, service account, or labels.
- Aggregate usage by agent identity.
- Attach quotas or budgets to each agent.
- Export to Prometheus/Grafana and alert when a specific agent exceeds expected usage.

## 12. Can I implement custom cost controls?

Yes.

Common patterns:

- Gateway middleware that checks a budget store before each LLM call.
- Redis-backed counters for rolling token or USD budgets.
- OPA/admission policies to reject expensive or unsafe agent specs.
- Budget-aware routing: cheaper model first, premium model only when approved.
- A controller that watches usage metrics and pauses, scales, or patches agents.

Budget checks should happen before the model call whenever possible; after-the-fact reporting is useful but does not
prevent spend.

## 13. Per-agent budgets or depth of token limits?

Use layered limits.

Recommended budget layers:

- Per request: timeout, max input size, max output tokens.
- Per task/session: max turns, max tool calls, max retries, max cumulative tokens, max cumulative cost.
- Per agent: hourly/daily/monthly quota.
- Per tenant/user/team: chargeback and quota.
- Per provider/model: fallback only when allowed by cost policy.

Depth controls are especially important for agents because runaway loops usually come from repeated model/tool/model
cycles, not one large request.

## 14. Is vLLM suitable for agents with many tool-call round trips, or better for single-shot inference?

vLLM is suitable for agent workloads, but it is an inference server, not an agent orchestrator.

It helps with:

- high-throughput serving
- OpenAI-compatible API
- continuous batching
- PagedAttention
- prefix caching
- structured outputs
- local/self-hosted model serving

For many back-and-forth tool calls, vLLM can help when repeated context benefits from prefix caching. However, every
tool round trip is still another model call, so agent design still matters: reduce unnecessary turns, compact context,
set step limits, and keep tools fast.

## 15. Does llm-d's scheduler help when an agent makes 15 LLM calls?

Yes, if those calls go to self-hosted models served through llm-d/vLLM.

llm-d helps at the inference-serving layer with:

- model routing
- flow control
- prefix/KV-cache-aware scheduling
- session-aware routing
- prefill/decode-aware load balancing
- better accelerator utilization

For an agent making many related calls, cache-aware routing can reduce recomputation and improve time-to-first-token.

Limits:

- It does not reduce the logical number of agent steps.
- It does not reduce external provider cost for OpenAI/Anthropic calls.
- It cannot parallelize a sequential agent loop where every step waits for a tool result.

So llm-d improves serving efficiency; gateway policy and agent orchestration still control cost and behavior.

## References

- [kagent overview](https://kagent.dev/)
- [kagent API reference](https://kagent.dev/docs/kagent/resources/api-ref)
- [kagent Anthropic provider configuration](https://www.kagent.dev/docs/kagent/supported-providers/anthropic)
- [agentgateway model failover](https://agentgateway.dev/docs/kubernetes/2.2.x/llm/failover/)
- [agentgateway rate limiting](https://agentgateway.dev/docs/standalone/main/configuration/resiliency/rate-limits/)
- [FastMCP Python with kagent/kmcp](https://www.kagent.dev/docs/kmcp/develop/fastmcp-python)
- [vLLM structured outputs](https://docs.vllm.ai/en/v0.18.1/features/structured_outputs/)
- [llm-d proposal](https://github.com/llm-d/llm-d/blob/main/docs/proposals/llm-d.md)
