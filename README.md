# Customer Support AI Agent

A customer-support AI agent that combines a local language model, knowledge-base retrieval, source-policy filtering, and deterministic order lookup.

The system is designed to answer customer questions using only information available in the supplied knowledge base and order data. It is explicitly designed not to invent missing delivery information or expose private order information.

## Features

- Knowledge-base question answering
- Source attribution for knowledge-based answers
- Current-policy prioritization over legacy policy documents
- Order lookup
- Case-insensitive order IDs
- Cancelled-order handling
- Missing-ETA protection
- Protection against exposing private order information
- Local LLM inference without Ollama
- Simple browser-based interface
- Automated regression tests

---

## 1. Setup and Run

### Requirements

- Python 3.14 tested
- pip
- Internet connection for the initial Hugging Face model download
- CPU is sufficient for the included model

### Clone

```bash
git clone https://github.com/vishakhacp22hcompe-prog/customer-support-ai-agent.git
cd customer-support-ai-agent