# aire-k8s

LLM Gateway & Agentic Infrastructure on Kubernetes.

## Runtime

- GitHub Codespaces
- Linux x86_64
- AgentGateway standalone binary

## Setup

```bash
curl -sL https://agentgateway.dev/install | bash
agentgateway --version
which agentgateway
```

## Configuration

Runtime configuration is defined in:

```text
config.yaml
```

Provider credentials are injected through environment variables and must not be committed.

Required local file:

```text
.env
```

Required variable:

```text
OPENAI_API_KEY
```

## Run

```bash
source .env
agentgateway -f config.yaml
```

## Verify

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.4-nano","messages":[{"role":"user","content":"Hello"}]}'
```