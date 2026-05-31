# aire-k8s

LLM Gateway & Agentic Infrastructure on Kubernetes.

## Runtime

- GitHub Codespaces
- Linux x86_64
- AgentGateway standalone binary
- Kubernetes through [abox](./abox/README.md)

## 1. AgentGateway standalone

Install AgentGateway:

```bash
curl -sL https://agentgateway.dev/install | bash
agentgateway --version
which agentgateway
```

Create a local `.env` file with your OpenAI key. Provider credentials are injected through environment variables and must not be committed.

```bash
OPENAI_API_KEY=...
```

Runtime configuration is defined in:

```text
config.yaml
```

Run AgentGateway:

```bash
source .env
agentgateway -f config.yaml
```

Validate the OpenAI-compatible AgentGateway endpoint:

```bash
curl http://localhost:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-5.4-nano","messages":[{"role":"user","content":"Reply with exactly: aire-k8s gateway is working"}]}'
```

Expected response content:

```text
aire-k8s gateway is working
```

Open the forwarded `15000` port to inspect the AgentGateway UI.

## 2. abox Kubernetes stack

The full Kubernetes setup lives in [abox](./abox/README.md). It provisions KinD, Flux CD, AgentGateway, kagent, and LoadBalancer support.

Run the stack:

```bash
cd abox
make run
```

The setup adds two shell shortcuts:

- `k` for `kubectl`
- `kk` for k9s

Check the cluster with k9s:

```bash
kk
```

In k9s, verify that nodes are ready and pods are running in

- `agentgateway-system`
- `flux-system`
- `kagent`

Inject the `OPENAI_API_KEY` env var into the `kagent` namespace as a Kubernetes Secret for the default kagent models:

```bash
k create secret generic kagent-openai \
  -n kagent \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client -o yaml | k apply -f -

KEY=$(k get secret kagent-openai -n kagent -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)
echo "${KEY:0:12}... length=${#KEY}"

k rollout restart deploy -n kagent
k get pods -n kagent -w
```

Create the secret used by the manual `openai-gpt-5-nano` model:

```bash
k create secret generic openai-gpt-5-nano \
  -n kagent \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client -o yaml | k apply -f -

KEY=$(k get secret kagent-openai -n kagent -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)
echo "${KEY:0:12}... length=${#KEY}"

k rollout restart deploy -n kagent
k get pods -n kagent -w
```

Apply the manual kagent resources:

```bash
k apply -f manual/modelconfig-openai-gpt-5-nano.yaml
k apply -f manual/mcpserver-fetch.yaml
k apply -f manual/agent-website-fetch.yaml
```

Or apply all manual resources at once:

```bash
k apply -f manual/
```

Verify that the model, MCP server, and agent are accepted:

```bash
k get modelconfig,mcpserver,agent -n kagent
k describe modelconfig openai-gpt-5-nano -n kagent
k describe mcpserver mcp-server-fetch -n kagent
k describe agent website-fetch-agent -n kagent
```

Delete the manual kagent resources when they are no longer needed:

```bash
k delete -f manual/
k delete secret openai-gpt-5-nano -n kagent --ignore-not-found
```

Open the kagent UI:

```bash
KG_UI_POD=$(k get po -n kagent -o name | grep pod/kagent-ui)
k port-forward -n kagent "$KG_UI_POD" 8080:8080
```
