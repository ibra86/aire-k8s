import os

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm


root_agent = LlmAgent(
    name="adk_website_assistant",
    model=LiteLlm(model=os.getenv("ADK_AGENT_MODEL", "openai/gpt-5-nano")),
    description="ADK A2A agent that answers concise questions about websites and Kubernetes workflows.",
    instruction=(
        "You are a concise ADK agent exposed through A2A. "
        "Answer in Markdown. If the request is unclear, ask one clarifying question."
    ),
)
