# Support Triage Agent

Support Triage Agent is a support ticket triage project that classifies, routes, and drafts grounded responses for three support ecosystems: HackerRank, Claude, and Visa.

The project was originally built during the HackerRank Orchestrate challenge and has been cleaned up here as a standalone portfolio-ready repository. It combines local-document retrieval with an LLM-based decision layer so responses stay tied to the bundled knowledge base instead of free-form guessing.

## Why this project is interesting

- Multi-brand support routing in a single pipeline
- Retrieval-augmented generation over a local support corpus 
- Deterministic-friendly setup with offline document indexing
- Safe escalation behavior for risky, ambiguous, or unsupported requests
- Simple terminal workflow that is easy to demo and extend

## How it works

1. The retriever scans the local `data/` corpus and builds a TF-IDF index.
2. For each ticket, the agent fetches the most relevant support chunks.
3. The LLM classifies the request, drafts a grounded reply, and decides whether to reply or escalate.
4. Results are written to `support_tickets/output.csv`.

## Project structure

```text
.
|-- code/
|   |-- agent.py
|   |-- main.py
|   |-- retriever.py
|   |-- requirements.txt
|   `-- README.md
|-- data/
|   |-- claude/
|   |-- hackerrank/
|   `-- visa/
|-- support_tickets/
|   |-- sample_support_tickets.csv
|   |-- support_tickets.csv
|   `-- output.csv
|-- AGENTS.md
|-- problem_statement.md
`-- evalutation_criteria.md
```

## Tech stack

- Python
- Groq API
- TF-IDF retrieval with scikit-learn
- CSV-based batch processing

## Quickstart

```bash
pip install -r code/requirements.txt
```

Set your API key:

```bash
# Windows
set GROQ_API_KEY=your-key-here

# macOS / Linux
export GROQ_API_KEY=your-key-here
```

Then run:

```bash
python code/main.py
```

## Output schema

The generated CSV includes:

- `status`
- `product_area`
- `response`
- `justification`
- `request_type`

## Portfolio talking points

- Built a grounded support agent instead of a generic chatbot
- Designed safe escalation behavior for high-risk support cases
- Used retrieval to reduce hallucinations and keep replies traceable to source material
- Structured the system so it can be swapped from one model provider to another with minimal changes

## Notes

- Secrets should stay in environment variables or a local `.env` file.
- The current implementation uses Groq for inference and local files for knowledge retrieval.
- The original challenge documents are still included for context and provenance.
