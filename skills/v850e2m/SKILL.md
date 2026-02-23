---
name: v850e2m
description: Use when the user asks about V850, V850E2M, or Renesas CPU architecture — instructions, registers, exceptions, addressing, memory protection, or assembly behavior. Also trigger when the user encounters V850E2M mnemonics (MOV, LD.W, Bcond, JARL, etc.), register names (PSW, EIPC, FPSR), or needs to understand disassembled V850 code.
---

# V850E2M CPU Architecture Reference

You have access to the full Renesas V850E2M User's Manual (Architecture) as a JSONL knowledge base. Use it to answer questions about V850E2M assembly instructions, registers, exceptions, memory protection, and CPU behavior. Always search before answering from memory — the reference is authoritative.

**Knowledge base:** `/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl`

## How to look things up

Query the JSONL with `Bash` using `grep | python3`. Do NOT use the `Grep` tool — JSONL lines are too long and get truncated.

### List matching chunks

```bash
grep PATTERN /Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl | python3 -c "
import json,sys
for line in sys.stdin:
    c=json.loads(line)
    print('[{}] {} (pp {})'.format(c['type'], c['title'], c['pages']))
"
```

### Read full content

```bash
grep PATTERN /Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl | python3 -c "
import json,sys
for line in sys.stdin:
    c=json.loads(line)
    print('--- {} ---'.format(c['title']))
    print('Hierarchy:', ' > '.join(c['hierarchy']))
    print()
    print(c['content'])
"
```

### Grep patterns

| Goal | PATTERN |
|------|---------|
| Exact mnemonic | `'"title": "MOV"'` |
| Keyword (case-insensitive) | `-i 'keyword'` |
| By type | `'"type": "register"'` |
| By category | `-i '"category": "branch'` |

**If grep returns nothing:** try case-insensitive (`-i`), try a partial match (e.g. `'MOV'` instead of `'"title": "MOV"'`), or broaden the search term. Multiple lookups are fine — search first to find relevant chunks, then read full content of the best matches.

## Chunk schema

Each JSONL line is a JSON object:

| Field | Description |
|---|---|
| `title` | Section or mnemonic name (`MOV`, `2.3.4 PSW  Program status word`) |
| `hierarchy` | Breadcrumb path array (`["PART 2 BASIC FUNCTION", "CHAPTER 5 INSTRUCTIONS", "Instruction Set", "MOV"]`) |
| `type` | `instruction` / `register` / `exception` / `protection` / `section` |
| `category` | Instruction category (see list below) |
| `pages` | Source PDF page(s) |
| `content` | Cleaned reference text |

## Knowledge base contents (477 chunks)

- **instruction** (171) — every V850E2M instruction with format, opcode, flags, operation pseudocode, and description. 98 basic + 73 floating-point.
- **register** (90) — program registers (r0-r31), system registers (PSW, EIPC, EIPSW, FEPC, FPSR, etc.), protection registers.
- **exception** (56) — exception types, cause lists, processing flow, acknowledgment priority, handler address switching.
- **protection** (24) — memory protection, peripheral device protection, timing supervision.
- **section** (136) — data types, addressing modes, instruction formats, opcode maps, pipelines, clock requirements.

### Instruction categories

Arithmetic, Bit manipulation, Bit search, Branch, Conditional operation, Data manipulation, Divide, Floating-point, Floating-point condition, High-speed divide, Load, Logical, Multiply, Multiply-accumulate, Saturated operation, Special, Store

### Instruction chunk structure

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
