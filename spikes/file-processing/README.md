# Spike: Compare file-processing approaches

[`compare.py`](compare.py) is a Python CLI tool that empirically compares two ways of
giving an LLM access to an uploaded file:

| Mode | Approach |
|------|----------|
| **Direct injection** | Extract full file text → concatenate into prompt |
| **Tool-call** | Send file metadata + tools; LLM pulls only what it needs |

The script runs both modes against three sample files (short / medium / long) with two
question types (targeted Q&A and full-document summarisation), then prints a comparison
table and saves `results.md`.

> **Note:** The documents in [`samples/`](samples/) are entirely synthetic and do not
> represent any real organisation, product, or individual.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An Azure OpenAI or Microsoft Foundry endpoint accessible via the OpenAI v1 API

## Running locally

```bash
cp .env.sample .env
# Edit .env with your OPENAI_BASE_URL, OPENAI_API_KEY, and MODEL_NAME
uv run compare.py
```

Progress is printed to stderr; the results table is printed to stdout and saved to `results.md`.

## Running in GitHub Actions

1. Add the following to your repository:
   - **Secret:** `OPENAI_API_KEY`
   - **Variables:** `OPENAI_BASE_URL`, `MODEL_NAME`
2. Go to **Actions → Compare file-processing approaches → Run workflow**.
3. After the run completes, download `results.md` from the workflow artifacts.
