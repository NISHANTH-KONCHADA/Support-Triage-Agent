# Support Triage Agent Runtime Guide

This folder contains the runnable Python implementation for the Support Triage Agent project.

## Files

- `main.py`: batch entry point that reads the ticket CSV and writes predictions
- `agent.py`: LLM-backed triage and response generation
- `retriever.py`: local corpus indexing and TF-IDF retrieval
- `requirements.txt`: Python dependencies

## Requirements

- Python 3.10+
- A valid `GROQ_API_KEY`

## Install

```bash
pip install -r code/requirements.txt
```

## Configure

You can export the key directly:

```bash
# Windows
set GROQ_API_KEY=your-key-here

# macOS / Linux
export GROQ_API_KEY=your-key-here
```

Or create a local `.env` file from the example:

```bash
copy code\.env.example code\.env
```

Then set:

```env
GROQ_API_KEY=your-key-here
```

## Run

```bash
python code/main.py
```

The script will:

1. Detect the main input CSV in `support_tickets/` or `support_issues/`
2. Process tickets one by one
3. Write incremental results to `output.csv`
4. Resume from existing output if a prior run was interrupted

## Implementation notes

- Retrieval is local-only and runs from the bundled `data/` corpus.
- The model is instructed to answer only from retrieved context.
- Unsupported, risky, or ambiguous requests are escalated instead of guessed.
- Output validation ensures every row matches the expected schema.
