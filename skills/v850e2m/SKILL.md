---
name: v850e2m
description: Use when the user asks about V850E2M CPU instructions, registers, exceptions, addressing, or architecture. Looks up Renesas V850E2M architecture reference material from a local JSONL knowledge base.
---

# V850E2M CPU Architecture Reference

You have access to the full Renesas V850E2M User's Manual (Architecture) as a JSONL knowledge base. Use it to answer questions about V850E2M assembly instructions, registers, exceptions, memory protection, and CPU behavior.

**Knowledge base location:** `/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl`

## How to look things up

Use the `Grep` tool to search the JSONL file. Each line is a self-contained JSON object, so matching lines give you complete chunks. Always search before answering from memory — the reference is authoritative.

### Look up an instruction by mnemonic

Use `Grep` with the exact mnemonic in the title field:

```
Grep(pattern='"title": "MOV"', path="/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl", output_mode="content")
```

The title field uses exact mnemonic names: `ADD`, `MOV`, `LD.W`, `Bcond`, `ABSF.D`, etc.

### Search by keyword across all chunks

```
Grep(pattern="PSW", path="/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl", output_mode="content", -i=true)
```

This returns every JSONL line mentioning the keyword. Parse the JSON from the output to read `title`, `type`, `hierarchy`, and `content` fields.

### Filter by chunk type

```
Grep(pattern='"type": "register"', path="/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl", output_mode="content")
```

Types: `instruction`, `register`, `exception`, `protection`, `section`

### Filter by instruction category

```
Grep(pattern='"category": "Branch instruction"', path="/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl", output_mode="content")
```

### Handling long output

If a keyword search returns too many results, use `head_limit` to cap the output:

```
Grep(pattern="KEYWORD", path="/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl", output_mode="content", head_limit=5)
```

Then refine your search with a more specific pattern.

## Chunk schema

Each JSONL line is a JSON object:

| Field | Description |
|---|---|
| `title` | Section or mnemonic name (`MOV`, `2.3.4 PSW  Program status word`) |
| `hierarchy` | Breadcrumb path array (`["PART 2 BASIC FUNCTION", "CHAPTER 5 INSTRUCTIONS", "Instruction Set", "MOV"]`) |
| `type` | `instruction` / `register` / `exception` / `protection` / `section` |
| `category` | Instruction category (e.g. `Arithmetic instruction`, `Branch instruction`, `Floating-point instruction`) |
| `pages` | Source PDF page(s) |
| `content` | Cleaned reference text |

## What's in the knowledge base (477 chunks)

- **instruction** (171) — every V850E2M instruction with format, opcode, flags, operation pseudocode, and description. Covers 98 basic and 73 floating-point instructions.
- **register** (90) — program registers (r0-r31), system registers (PSW, EIPC, EIPSW, FEPC, FPSR, etc.), protection registers.
- **exception** (56) — exception types, cause lists, processing flow, acknowledgment priority, handler address switching.
- **protection** (24) — memory protection, peripheral device protection, timing supervision.
- **section** (136) — data types, addressing modes, instruction formats, opcode maps, pipelines, clock requirements.

## Instruction chunk structure

Each instruction chunk contains these sections in order:

1. `<Category>` tag (e.g. `<Arithmetic instruction>`)
2. Short description and mnemonic
3. `[Instruction format]` — assembly syntax
4. `[Operation]` — pseudocode semantics
5. `[Format]` — instruction format type (I–XIV)
6. `[Opcode]` — binary encoding
7. `[Flags]` — CY, OV, S, Z, SAT behavior (`"1"` = set, `"0"` = clear, `"--"` = unchanged)
8. `[Description]` — detailed explanation
9. Optional `[Comment]`, `[Caution]`, `[Remark]`

## V850E2M quick reference

- **32-bit RISC**, little-endian, 32 general-purpose registers (r0=zero, r3=sp, r4=gp, r30=ep, r31=lp)
- **Return register**: r10 (r10+r11 for 64-bit)
- **Argument registers**: r6-r9
- **Instruction widths**: 16-bit, 32-bit, and 48-bit
- **Condition flags in PSW**: CY (carry), OV (overflow), S (sign), Z (zero), SAT (saturation)
- **Exception levels**: EI (maskable interrupts), FE (non-maskable), DB (debug)

## Usage guidelines

- **Always search the JSONL** before answering architecture questions — don't rely on recall alone
- **Combine with Ghidra** — when encountering unknown V850E2M instructions in Ghidra disassembly, look them up here to understand semantics before annotating
- **Multiple lookups are fine** — do a keyword search first to find relevant chunks, then read the full content of the best matches
- When the user asks about a general topic (e.g. "how do exceptions work"), search by type (`exception`) and read the overview chunks first
