# Ghidra RE Claude Code Plugin

Firmware and embedded systems reverse engineering with Ghidra via GhidraMCP.

## Skills

- **ghidra** (`/ghidra`) — RE methodology, GhidraMCP tool usage, firmware analysis workflow, type system, gotchas
- **v850e2m** (`/v850e2m`) — Renesas V850E2M CPU architecture reference (instructions, registers, exceptions, memory protection). Queries `v850e2m_rag_chunks.jsonl` — 477 chunks from the full User's Manual.
- **tc27x** (`/tc27x`) — TriCore TC1.6P/TC1.6E instruction set reference (CPU, FPU instructions, opcode formats, status flags). Queries `tc27x_rag_chunks.jsonl` — 274 chunks from the Instruction Set User Manual (Volume 2).

## Project layout

```
commands/          User-facing slash commands
skills/            Skill definitions (methodology + reference material)
  ghidra/          RE skill (GhidraMCP workflow)
  v850e2m/         V850E2M architecture reference skill
  tc27x/           TriCore instruction set reference skill
v850e2m_rag_chunks.jsonl   V850E2M manual as JSONL chunks for RAG
tc27x_rag_chunks.jsonl     TriCore ISA manual as JSONL chunks for RAG
pdf_to_rag_chunks.py       Script that generated the V850E2M JSONL
tc27x_pdf_to_rag_chunks.py Script that generated the TC27x JSONL
.mcp.json          GhidraMCP bridge configuration
```
