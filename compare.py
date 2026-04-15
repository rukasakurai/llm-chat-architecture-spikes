# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "openai>=1.0.0",
#   "python-dotenv>=1.0.0",
# ]
# ///

"""
compare.py — Spike: Direct injection vs. tool-call file processing with LLMs.

Runs both modes against a set of sample files and questions, then prints a
comparison table and saves results.md.

Required environment variables (can be set in .env — see .env.sample):
  OPENAI_BASE_URL  — Azure OpenAI or Foundry endpoint, e.g.
                     https://your-resource.openai.azure.com/openai/v1/
  OPENAI_API_KEY   — API key for the endpoint above
  MODEL_NAME       — Deployment name (default: "gpt-5")
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()

MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-5")

# The OpenAI client picks up OPENAI_BASE_URL and OPENAI_API_KEY automatically.
client = OpenAI()

SAMPLES_DIR = Path(__file__).parent / "samples"

# ---------------------------------------------------------------------------
# Test matrix
# ---------------------------------------------------------------------------

SCENARIOS: list[dict[str, Any]] = [
    {
        "file": "meeting-notes.md",
        "label": "short",
        "questions": [
            {
                "type": "qa",
                "text": "What does this document say about the QA timeline for the v2.4 release?",
            },
            {
                "type": "summarise",
                "text": "Summarise this document in 3 bullet points.",
            },
        ],
    },
    {
        "file": "technical-spec.md",
        "label": "medium",
        "questions": [
            {
                "type": "qa",
                "text": "What does this document say about rate limiting and query complexity?",
            },
            {
                "type": "summarise",
                "text": "Summarise this document in 3 bullet points.",
            },
        ],
    },
    {
        "file": "research-report.md",
        "label": "long",
        "questions": [
            {
                "type": "qa",
                "text": "What does this document say about long-duration energy storage technologies?",
            },
            {
                "type": "summarise",
                "text": "Summarise this document in 3 bullet points.",
            },
        ],
    },
]

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    file: str
    file_size_tokens: int
    question_type: str
    question: str
    mode: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tool_calls: int
    latency_s: float
    response_text: str
    token_savings_vs_direct: int = field(default=0)


# ---------------------------------------------------------------------------
# Tool implementations (used by Mode 2)
# ---------------------------------------------------------------------------


def read_section(lines: list[str], start_line: int, end_line: int) -> str:
    """Return lines[start_line:end_line+1] (0-indexed, inclusive end)."""
    total = len(lines)
    start = max(0, start_line)
    end = min(total - 1, end_line)
    if start > end:
        return f"[No content: start_line {start_line} > end_line {end_line} or out of range 0–{total - 1}]"
    return "\n".join(lines[start : end + 1])


def search_file(text: str, query: str) -> str:
    """Return up to 3 passages (~500 chars each) matching query (case-insensitive)."""
    query_lower = query.lower()
    text_lower = text.lower()
    results: list[str] = []
    start = 0
    while len(results) < 3:
        idx = text_lower.find(query_lower, start)
        if idx == -1:
            break
        ctx_start = max(0, idx - 200)
        ctx_end = min(len(text), idx + 300)
        snippet = text[ctx_start:ctx_end]
        results.append(snippet.strip())
        start = idx + len(query_lower)
    if not results:
        return f"[No matches found for '{query}']"
    passages = "\n\n---\n\n".join(f"Passage {i + 1}:\n{p}" for i, p in enumerate(results))
    return passages


# ---------------------------------------------------------------------------
# Mode 1: Direct injection
# ---------------------------------------------------------------------------


def run_direct(file_text: str, filename: str, question: str) -> tuple[int, int, int, float, str]:
    """Send the full file text + question to the model. Return (in, out, total, latency, response)."""
    system_prompt = (
        "You are a helpful assistant. Answer questions accurately based on the provided document."
    )
    user_message = f"Document ({filename}):\n\n{file_text}\n\n---\n\nQuestion: {question}"

    print(f"  [direct] sending request …", file=sys.stderr)
    t0 = time.monotonic()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    latency = time.monotonic() - t0

    usage = response.usage
    in_tok = usage.prompt_tokens
    out_tok = usage.completion_tokens
    total_tok = usage.total_tokens
    text = response.choices[0].message.content or ""
    print(
        f"  [direct] done — in={in_tok}, out={out_tok}, total={total_tok}, latency={latency:.1f}s",
        file=sys.stderr,
    )
    return in_tok, out_tok, total_tok, latency, text


# ---------------------------------------------------------------------------
# Mode 2: Tool-call
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_section",
            "description": "Returns lines start_line to end_line from the file (0-indexed, inclusive).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_line": {
                        "type": "integer",
                        "description": "First line to retrieve (0-indexed).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Last line to retrieve (0-indexed, inclusive).",
                    },
                },
                "required": ["start_line", "end_line"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_file",
            "description": (
                "Returns the top 3 most relevant passages (~500 chars each) "
                "based on case-insensitive substring search."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword or phrase to search for.",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


def run_tool_call(
    file_text: str, filename: str, question: str
) -> tuple[int, int, int, int, float, str]:
    """
    Send metadata + tools to the model and execute tool calls until a final answer.
    Return (in_tokens, out_tokens, total_tokens, tool_call_count, latency, response).
    """
    lines = file_text.splitlines()
    total_lines = len(lines)
    preview = file_text[:200]
    file_type = Path(filename).suffix.lstrip(".") or "text"

    system_prompt = (
        f"You are a helpful assistant. The user wants to ask a question about the file '{filename}'.\n"
        f"File type: {file_type}\n"
        f"Total lines: {total_lines}\n"
        f"Preview (first 200 chars):\n{preview}\n\n"
        "You have access to the file via tools. Use read_section to read specific line ranges "
        "(0-indexed), or search_file to find relevant passages. Only retrieve what you need to "
        "answer the question."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    total_in = 0
    total_out = 0
    total_total = 0
    tool_call_count = 0
    max_iterations = 10
    final_text = ""

    print(f"  [tool-call] starting agentic loop (max {max_iterations} iterations) …", file=sys.stderr)
    t0 = time.monotonic()

    for iteration in range(max_iterations):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        usage = response.usage
        total_in += usage.prompt_tokens
        total_out += usage.completion_tokens
        total_total += usage.total_tokens

        choice = response.choices[0]
        msg = choice.message

        # Append assistant message (need dict form for the next request)
        assistant_msg: dict[str, Any] = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in msg.tool_calls
            ]
        messages.append(assistant_msg)

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            print(
                f"  [tool-call] iteration {iteration + 1}: {len(msg.tool_calls)} tool call(s)",
                file=sys.stderr,
            )
            for tc in msg.tool_calls:
                tool_call_count += 1
                fn_name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}

                if fn_name == "read_section":
                    result = read_section(lines, args.get("start_line", 0), args.get("end_line", 0))
                elif fn_name == "search_file":
                    result = search_file(file_text, args.get("query", ""))
                else:
                    result = f"[Unknown tool: {fn_name}]"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
        else:
            # Model gave a final answer (stop or no tool calls)
            final_text = msg.content or ""
            print(
                f"  [tool-call] final answer after {iteration + 1} iteration(s), "
                f"{tool_call_count} tool call(s)",
                file=sys.stderr,
            )
            break
    else:
        # Hit max iterations — use whatever the last message content was
        final_text = messages[-1].get("content") or ""
        print(
            f"  [tool-call] reached max iterations ({max_iterations}), using last response",
            file=sys.stderr,
        )

    latency = time.monotonic() - t0
    print(
        f"  [tool-call] done — in={total_in}, out={total_out}, total={total_total}, "
        f"tools={tool_call_count}, latency={latency:.1f}s",
        file=sys.stderr,
    )
    return total_in, total_out, total_total, tool_call_count, latency, final_text


# ---------------------------------------------------------------------------
# Estimate file size in tokens (rough: 1 token ≈ 4 chars)
# ---------------------------------------------------------------------------


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------


def run_all_scenarios() -> list[RunResult]:
    results: list[RunResult] = []

    for scenario in SCENARIOS:
        filename = scenario["file"]
        file_path = SAMPLES_DIR / filename
        file_text = file_path.read_text(encoding="utf-8")
        file_size_tokens = estimate_tokens(file_text)

        for q in scenario["questions"]:
            question_type = q["type"]
            question_text = q["text"]

            print(
                f"\n{'=' * 60}\n"
                f"File: {filename}  |  Q-type: {question_type}\n"
                f"Q: {question_text}\n"
                f"{'=' * 60}",
                file=sys.stderr,
            )

            # --- Mode 1 ---
            in1, out1, tot1, lat1, resp1 = run_direct(file_text, filename, question_text)
            direct_result = RunResult(
                file=filename,
                file_size_tokens=file_size_tokens,
                question_type=question_type,
                question=question_text,
                mode="direct",
                input_tokens=in1,
                output_tokens=out1,
                total_tokens=tot1,
                tool_calls=0,
                latency_s=lat1,
                response_text=resp1,
            )
            results.append(direct_result)

            # --- Mode 2 ---
            in2, out2, tot2, n_tools, lat2, resp2 = run_tool_call(
                file_text, filename, question_text
            )
            tool_result = RunResult(
                file=filename,
                file_size_tokens=file_size_tokens,
                question_type=question_type,
                question=question_text,
                mode="tool-call",
                input_tokens=in2,
                output_tokens=out2,
                total_tokens=tot2,
                tool_calls=n_tools,
                latency_s=lat2,
                response_text=resp2,
                token_savings_vs_direct=tot1 - tot2,
            )
            results.append(tool_result)

    return results


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def build_table(results: list[RunResult]) -> str:
    header = (
        "| File | Size (tokens) | Question Type | Mode | "
        "Input Tokens | Output Tokens | Total Tokens | Tool Calls | "
        "Latency (s) | Token Savings vs Direct |"
    )
    separator = (
        "|---|---|---|---|---|---|---|---|---|---|"
    )
    rows = [header, separator]
    for r in results:
        savings = r.token_savings_vs_direct if r.mode == "tool-call" else "—"
        rows.append(
            f"| {r.file} | {r.file_size_tokens} | {r.question_type} | {r.mode} | "
            f"{r.input_tokens} | {r.output_tokens} | {r.total_tokens} | "
            f"{r.tool_calls} | {r.latency_s:.2f} | {savings} |"
        )
    return "\n".join(rows)


def build_summary(results: list[RunResult]) -> str:
    tool_call_results = [r for r in results if r.mode == "tool-call"]

    qa_savings = [r.token_savings_vs_direct for r in tool_call_results if r.question_type == "qa"]
    summ_savings = [
        r.token_savings_vs_direct for r in tool_call_results if r.question_type == "summarise"
    ]

    avg_qa = sum(qa_savings) / len(qa_savings) if qa_savings else 0
    avg_summ = sum(summ_savings) / len(summ_savings) if summ_savings else 0

    lines = [
        "## Summary",
        "",
        f"- **Average token savings (Q&A questions):** {avg_qa:.0f} tokens",
        f"- **Average token savings (full-document questions):** {avg_summ:.0f} tokens",
        "",
        "## Response Quality Comparison",
        "",
    ]

    # Group by (file, question_type) and show responses side by side
    seen: set[tuple[str, str, str]] = set()
    for r in results:
        key = (r.file, r.question_type, r.question)
        if key in seen:
            continue
        seen.add(key)

        direct = next(
            (x for x in results if x.file == r.file and x.question == r.question and x.mode == "direct"),
            None,
        )
        tool = next(
            (x for x in results if x.file == r.file and x.question == r.question and x.mode == "tool-call"),
            None,
        )

        lines.append(f"### {r.file} — {r.question_type}")
        lines.append(f"**Question:** {r.question}")
        lines.append("")
        lines.append("**Mode 1 (Direct injection) response:**")
        lines.append("")
        lines.append(direct.response_text if direct else "_not available_")
        lines.append("")
        lines.append("**Mode 2 (Tool-call) response:**")
        lines.append("")
        lines.append(tool.response_text if tool else "_not available_")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def build_results_md(results: list[RunResult]) -> str:
    table = build_table(results)
    summary = build_summary(results)
    return f"# Results\n\n{table}\n\n{summary}"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    print("Starting comparison runs …", file=sys.stderr)
    results = run_all_scenarios()

    table = build_table(results)
    summary = build_summary(results)
    output = f"# Results\n\n{table}\n\n{summary}"

    print("\n" + table)
    print("\n" + summary)

    results_path = Path(__file__).parent / "results.md"
    results_path.write_text(output, encoding="utf-8")
    print(f"\nResults saved to {results_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
