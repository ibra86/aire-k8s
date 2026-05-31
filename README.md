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

Inject the OPENAI_API_KEY env var into the `kagent` namespace as a Kubernetes Secret:

```bash
kubectl create secret generic kagent-openai \
  -n kagent \
  --from-literal=OPENAI_API_KEY="$OPENAI_API_KEY" \
  --dry-run=client -o yaml | kubectl apply -f -

KEY=$(kubectl get secret kagent-openai -n kagent -o jsonpath='{.data.OPENAI_API_KEY}' | base64 -d)
echo "${KEY:0:12}... length=${#KEY}"

kubectl rollout restart deploy -n kagent
kubectl get pods -n kagent -w
```
