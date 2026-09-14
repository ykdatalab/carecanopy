# CareCanopy — AWS Setup and Reproduction Guide

This guide documents the AWS configuration required by the current CareCanopy MVP.

It reflects the implementation in the repository. It does not claim infrastructure automation that is not included in the repo.

## 1. Local environment

CareCanopy was built and tested with:

- Python 3.12.14
- boto3 1.43.92
- pydantic 2.13.5
- strands-agents 1.55.1
- streamlit 1.63.0

From the repository root:

```bash
python -m pip install -r requirements.txt
```

## 2. AWS region

The current MVP uses:

```text
ap-northeast-2
```

The region is currently defined in:

- `app/agent.py`
- `app/dynamo_state.py`
- `streamlit_app.py`

## 3. AWS credentials

CareCanopy uses the standard AWS credential provider chain through `boto3`.

Configure AWS credentials using your normal AWS method, for example:

```bash
aws configure
```

or use environment variables / an IAM role supported by the AWS SDK.

Do not commit access keys, secret keys, session tokens, or credential files to the repository.

A useful identity check is:

```bash
aws sts get-caller-identity
```

The AWS CLI is useful for setup and verification, but the Python application itself uses `boto3`.

## 4. Amazon Bedrock

CareCanopy currently uses this Bedrock model / inference profile:

```text
global.anthropic.claude-sonnet-4-5-20250929-v1:0
```

The AWS identity running CareCanopy must be able to invoke the configured Bedrock model.

At minimum, the relevant identity needs permission equivalent to:

```text
bedrock:InvokeModel
```

If model access, account policy, or regional availability prevents invocation, update the deployment configuration deliberately and re-test before using a different model.

The frozen benchmark in this repository was generated with the model identifier recorded above. Do not present results from another model as the same frozen benchmark.

## 5. Amazon DynamoDB

CareCanopy persists workflow state in this table:

```text
CareCanopyWorkflowStates
```

The partition key is:

```text
case_id  (String)
```

A minimal table can be created with the AWS CLI:

```bash
aws dynamodb create-table \
  --table-name CareCanopyWorkflowStates \
  --attribute-definitions AttributeName=case_id,AttributeType=S \
  --key-schema AttributeName=case_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ap-northeast-2
```

On PowerShell, the same command can be entered on one line:

```powershell
aws dynamodb create-table --table-name CareCanopyWorkflowStates --attribute-definitions AttributeName=case_id,AttributeType=S --key-schema AttributeName=case_id,KeyType=HASH --billing-mode PAY_PER_REQUEST --region ap-northeast-2
```

The application currently uses DynamoDB operations including:

- `GetItem`
- `PutItem`
- `Scan`

The AWS identity running the prototype therefore needs access to those operations on the CareCanopy table.

Verify the table:

```bash
aws dynamodb describe-table \
  --table-name CareCanopyWorkflowStates \
  --region ap-northeast-2
```

## 6. Amazon EventBridge Scheduler — proactive demo path

EventBridge Scheduler is used to demonstrate a proactive workflow:

> an overdue rehabilitation follow-up task can exist before the frontline worker initiates a chat.

The current repository does **not** contain infrastructure-as-code that provisions the EventBridge schedule.

The Streamlit UI reads proactive demo tasks from `CareCanopyWorkflowStates` and recognises items whose `case_id` begins with:

```text
PROACTIVE_DEMO_
```

The UI reads the following fields when they are present:

```text
case_id
reason
task_source
updated_at
```

A representative proactive-task record is conceptually:

```json
{
  "case_id": "PROACTIVE_DEMO_001",
  "reason": "Scheduled rehabilitation follow-up is overdue.",
  "task_source": "Amazon EventBridge Scheduler",
  "updated_at": "2026-09-14T00:00:00+00:00"
}
```

For the hackathon demo, EventBridge Scheduler should create or trigger creation of a DynamoDB task record matching that contract.

Important implementation truth:

- EventBridge creates / triggers the overdue workflow task.
- EventBridge does **not** generate a clinical report.
- The frontline worker still supplies the clinical observation used for routing.
- The MVP records a clinical-team notification action in workflow state; it does not claim to send an external clinical notification.

If reproducing the proactive path outside the original AWS account, create an EventBridge schedule and use an authorised target that writes the task item to the DynamoDB table above. The exact schedule/target wiring is account infrastructure and is not provisioned by this repository.

## 7. Run the Streamlit prototype

From the repository root:

```bash
streamlit run streamlit_app.py
```

The prototype needs working AWS credentials for:

- Bedrock reasoning
- DynamoDB persistence

The EventBridge-created proactive banner appears only when an appropriate `PROACTIVE_DEMO_...` item exists in the DynamoDB table.

## 8. Run development cases

```bash
python run_dev.py
```

These are development scenarios, not the frozen evaluation benchmark.

## 9. Run deterministic boundary probes

```bash
python run_boundary_probes.py
```

These probes deliberately simulate an unsafe LLM proposal and test whether selected hard boundaries override it deterministically.

The probe result is an implementation-level boundary test, not a claim of comprehensive clinical safety.

## 10. Run the frozen benchmark

```bash
python run_frozen_benchmark.py
```

The benchmark runner checks that files under `app/` still match:

```text
carecanopy-agent-v1-freeze
```

before evaluation.

Frozen benchmark outputs are stored separately and were tagged before external clinician labels were revealed.

Do not modify frozen routing / safety logic and then represent the new result as the original frozen benchmark.

## 11. Minimal AWS permission summary

For local reproduction, the AWS identity may need permissions corresponding to:

```text
bedrock:InvokeModel
dynamodb:GetItem
dynamodb:PutItem
dynamodb:Scan
dynamodb:DescribeTable
```

Additional EventBridge Scheduler permissions are needed only for provisioning / operating the proactive schedule and depend on the chosen target and execution role.

Use least privilege for any real deployment.

## 12. Current MVP boundaries

This is a hackathon prototype using synthetic patient scenarios.

It does not include:

- production authentication,
- EHR integration,
- PHI handling,
- infrastructure-as-code,
- AgentCore Gateway / Policy deployment,
- external clinical notification delivery,
- prospective clinical validation.

Those are production-extension concerns and should not be inferred from the demo.
