# Ghidra RE Claude Code Plugin

Firmware and embedded systems reverse engineering with Ghidra via GhidraMCP.

## Skills

- **ghidra** (`/ghidra`) — RE methodology, GhidraMCP tool usage, firmware analysis workflow, type system, gotchas
- **v850e2m** (`/v850e2m`) — Renesas V850E2M CPU architecture reference (instructions, registers, exceptions, memory protection). Queries `v850e2m_rag_chunks.jsonl` — 477 chunks from the full User's Manual.

## Project layout

```
commands/          User-facing slash commands
skills/            Skill definitions (methodology + reference material)
  ghidra/          RE skill (GhidraMCP workflow)
  v850e2m/         V850E2M architecture reference skill
v850e2m_rag_chunks.jsonl   V850E2M manual as JSONL chunks for RAG
pdf_to_rag_chunks.py       Script that generated the JSONL from the source PDF
.mcp.json          GhidraMCP bridge configuration
```
