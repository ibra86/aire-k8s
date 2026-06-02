import os

from google.adk.a2a.utils.agent_to_a2a import to_a2a

from app.agent import root_agent


a2a_app = to_a2a(root_agent, port=int(os.getenv("PORT", "8080")))
