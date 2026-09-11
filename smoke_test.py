from strands import Agent
from strands.models import BedrockModel

model = BedrockModel(
    model_id="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region_name="ap-northeast-2",
    temperature=0.1,
    max_tokens=200,
)

agent = Agent(
    model=model,
    system_prompt=(
        "You are a test agent for CareCanopy, "
        "an AI agent for safe delegation in community rehabilitation. "
        "Reply very briefly."
    ),
)

response = agent(
    "A community rehabilitation worker reports that a scheduled follow-up "
    "was completed normally with no new symptoms. Reply only: CONNECTION_OK"
)

print(response)