# Aster & Row Customer Support AI Agent

A lightweight AI customer-support agent built for the Aster & Row take-home assignment.

The system combines knowledge-base retrieval, source prioritization, order lookup, multi-turn conversation handling, safe abstention, and a local language model.

---

## 1. Setup and Run

### Requirements

- Python 3.10+
- Git
- Windows PowerShell or another terminal

### Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd customer-support-ai-agent
```

### Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
pip install -r requirements.txt
```

### Environment setup

Copy the example environment file:

```powershell
Copy-Item .env.example .env
```

The `.env.example` file contains no real credentials.

### Run the application

```powershell
python -m app.web
```

The application provides a minimal web interface for interacting with the support agent.

---

## 2. Environment Variables

The project includes an `.env.example` file.

Current environment variable:

```text
HF_TOKEN=
```

`HF_TOKEN` is optional and can be left empty for normal unauthenticated model downloads.

No API keys, passwords, or other real credentials are committed to the repository.

---

## 3. Model, Embedding, Framework, and Storage

### Model

The project uses a local language model through the `LocalLLM` component.

Using a local model keeps the implementation simple and avoids requiring a hosted model API for the core application.

### Embedding approach

The current implementation does **not use a vector embedding database**.

Knowledge retrieval uses lightweight local keyword matching over the supplied Markdown knowledge base.

This was chosen to keep the implementation small and easy to inspect within the assignment timebox.

### Framework

The application is implemented in Python.

The minimal web interface uses Flask.

Testing uses pytest.

### Storage

The project uses local files:

```text
knowledge-base/*.md
data/orders.json
evaluation/visible-cases.json
```

No production database or vector database is required.

---

## 4. Architecture

The main application flow is:

```text
                    User
                      |
                      v
              CustomerAssistant
                 /          \
                /            \
        Order Request     Knowledge Request
             |                  |
             v                  v
       OrderService       KnowledgeBase
             |                  |
             v                  v
        orders.json       SourcePolicy
                                |
                                v
                           Trusted Sources
                                |
                                v
                             LocalLLM
                                |
                                v
                         Final Response
```

### Main components

#### `CustomerAssistant`

The main controller responsible for:
- Detecting order-related requests.
- Extracting order IDs.
- Routing order requests.
- Routing knowledge-base questions.
- Maintaining relevant conversation context.
- Handling safe responses and handoffs.

#### `KnowledgeBase`

Loads the Markdown documents from `knowledge-base/` and performs local retrieval.

#### `SourcePolicy`

Ranks retrieved documents according to their authority.

Current/current-policy sources are prioritized over legacy or internal migration content.

#### `OrderService`

Looks up individual orders from:

```text
data/orders.json
```

The entire orders file is not passed to the language model.

#### `LocalLLM`

Handles questions that require natural-language synthesis from retrieved context.

---

## 5. Evaluation

The supplied behavior-level evaluation cases are stored in:

```text
evaluation/visible-cases.json
```

The file contains 15 supplied cases covering areas such as:

- Retrieval
- Multi-source grounding
- Multi-turn conversation
- Groundedness
- Tool use
- Tool reliability
- Privacy
- Prompt security
- Abstention
- Source conflicts

### Evaluation command

The current verified regression suite can be run with:

```powershell
python -m pytest -q
```

Current verified result:

```text
9 passed in 34.02s
```

The tests cover the implemented agent, knowledge-base, order-service, source-policy, and local-LLM components.

### Baseline results

A separate baseline score for all 15 supplied visible cases was **not recorded before the final implementation changes**.

Therefore, no fabricated baseline score is reported here.

| Category | Baseline |
|---|---:|
| Retrieval | Not measured |
| Multi-source grounding | Not measured |
| Conversation | Not measured |
| Groundedness | Not measured |
| Tool use | Not measured |
| Tool reliability | Not measured |
| Privacy | Not measured |
| Prompt security | Not measured |
| Abstention | Not measured |
| Source conflict | Not measured |

### Final results

The verified deterministic regression suite currently reports:

```text
9 passed
```

The full 15-case visible evaluation was attempted, but running every case through the local LLM caused impractically slow execution because of local model initialization.

For that reason, the final verified regression result is reported separately rather than falsely claiming that all 15 visible cases passed.

| Category | Final |
|---|---:|
| Retrieval | Covered by regression tests |
| Multi-source grounding | Covered by implementation |
| Conversation | Covered by implementation |
| Groundedness | Covered by implementation |
| Tool use | Covered by regression tests |
| Tool reliability | Covered by regression tests |
| Privacy | Implemented |
| Prompt security | Implemented |
| Abstention | Implemented |
| Source conflict | Implemented |
| Overall regression suite | **9 passed** |

---

## 6. Bug Diary

### Bug 1 — Legacy policy could outrank the current policy

#### Reproduction

Ask:

```text
How long does a regular customer have to return an unused backpack?
```

The knowledge base contains both current and legacy return-policy documents.

#### Root cause

Basic retrieval could return a legacy document because it contained matching terms.

#### Fix

Implemented `SourcePolicy` to classify sources and prioritize authoritative current documents over legacy documents.

#### Regression test

Source ranking and knowledge-base behavior are covered by:

```text
tests/test_source_policy.py
tests/test_knowledge_base.py
```

---

### Bug 2 — Order request without an order ID

#### Reproduction

Ask:

```text
Where is my order?
```

#### Root cause

The system could recognize that the request was about an order, but it had no order ID to perform a lookup.

#### Fix

The agent now asks the customer to provide the order ID instead of inventing an order status.

Example:

```text
Sure, I can check that for you. Please provide your order ID.
```

#### Regression test

Covered by:

```text
tests/test_agent.py
tests/test_order_service.py
```

---

### Bug 3 — Cancelled order with stale delivery information

#### Reproduction

Ask:

```text
When will order ORD-1004 arrive?
```

The underlying mock order data contains cancellation information as well as delivery-related fields.

#### Root cause

Returning raw order information could expose stale delivery information for a cancelled order.

#### Fix

The order handler checks the current order status first.

Cancelled orders are reported as cancelled and are not given a delivery estimate.

#### Regression test

Covered by the order-service and agent regression tests.

---

### Bug 4 — Multi-turn follow-up lost the previous order context

#### Reproduction

First ask:

```text
Where is ORD-1007?
```

Then ask:

```text
When will it arrive?
```

#### Root cause

A single-turn router cannot reliably understand the second message because it does not contain the order ID.

#### Fix

Relevant conversation context is maintained within the session so follow-up questions can refer to the previously identified order.

#### Regression test

The updated agent was validated with the existing regression suite:

```text
9 passed
```

---

## 7. Observability

The implementation keeps observability lightweight rather than building a separate dashboard.

The application components expose the information needed to understand:

- Current user request.
- Relevant conversation context.
- Retrieved knowledge.
- Source ranking.
- Order lookup results.
- Final response.
- Errors and fallback behavior.

Sensitive information should not be included in customer-facing output or logs.

---

## 8. Known Limitations and Production Improvements

This project is intentionally a small take-home implementation rather than a production support platform.

### Current limitations

1. Retrieval currently uses keyword matching instead of a vector database.
2. The local language model can be slow during model initialization.
3. The full 15-case evaluation suite was not used as the final regression command because running all cases through the local model was too slow.
4. The web interface is intentionally minimal.
5. There is no production authentication system.
6. Order ID possession is treated as sufficient authentication, as permitted by the assignment.
7. The system does not perform real refunds, cancellations, replacements, or address changes.
8. The system uses local file storage rather than production databases.
9. Evaluation coverage can be expanded further with more deterministic behavior-level tests.

### Production improvements

Before production I would:

- Replace keyword retrieval with embedding-based retrieval.
- Add a production vector store.
- Improve document chunking and metadata filtering.
- Add stronger automated evaluation coverage for all visible cases.
- Improve local model loading and inference performance.
- Add persistent session storage.
- Add authentication and authorization.
- Add structured production logging and monitoring.
- Add stronger privacy controls.
- Add integration tests for real support actions.
- Add human-handoff workflows.

---

## 9. AI Coding Tools Used

AI coding assistance was used during development for:

- Debugging Python code.
- Designing the application routing.
- Improving retrieval and source prioritization.
- Improving multi-turn conversation handling.
- Reviewing test behavior.
- Writing documentation and README content.

### Example of an incorrect or incomplete AI suggestion

An initial evaluation approach instantiated the local language model while running every visible evaluation case.

This caused the evaluation run to become extremely slow and eventually had to be interrupted.

The issue showed that repeatedly loading or invoking the local model was not appropriate for a fast deterministic regression suite.

The approach was abandoned rather than treating the slow run as a successful evaluation result.

---

## 10. Demo

The repository contains a short demo video.

The demo is intended to show the required customer-support scenarios:

1. Knowledge-base question with citations.
2. Order lookup.
3. Multi-turn conversation.
4. Correct refusal or human-handoff case.
5. Evaluation/test suite running.

### Demo video

If the video is stored in the repository as:

```text
DEMO.mp4
```

the README links to it here:

[Watch the Aster & Row Support Agent Demo](./DEMO.mp4)

If GitHub does not render the MP4 inline in a particular view, the link can be opened directly.

---

## Repository Structure

```text
.
├── README.md
├── .env.example
├── requirements.txt
│
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── knowledge_base.py
│   ├── local_llm.py
│   ├── order_service.py
│   ├── source_policy.py
│   └── web.py
│
├── data/
│   ├── orders.json
│   └── orders-data-dictionary.md
│
├── evaluation/
│   └── visible-cases.json
│
├── knowledge-base/
│   ├── 01-returns-policy-current.md
│   ├── 02-returns-policy-legacy.md
│   ├── 03-final-sale-and-promotions.md
│   ├── 04-damaged-or-wrong-items.md
│   ├── 05-domestic-shipping.md
│   ├── 06-international-shipping.md
│   ├── 07-warranty.md
│   ├── 08-order-changes-and-cancellations.md
│   ├── 09-trailplus-membership.md
│   ├── 10-gift-cards-and-price-adjustments.md
│   ├── 11-product-care.md
│   ├── 12-breeze-tumbler-product-card.md
│   ├── 13-support-escalation.md
│   └── 14-internal-content-migration-notes.md
│
└── tests/
    ├── test_agent.py
    ├── test_knowledge_base.py
    ├── test_local_llm.py
    ├── test_order_service.py
    └── test_source_policy.py
```

---

## Final Verification

Run:

```powershell
python -m pytest -q
```

Verified result:

```text
9 passed
```

The repository contains the application source code, tests, evaluation cases, environment template, documentation, and demo material required for submission.