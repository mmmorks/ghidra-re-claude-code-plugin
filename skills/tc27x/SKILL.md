---
name: tc27x
description: Use when the user asks about TriCore, TC27x, TC1.6P, TC1.6E, AURIX, or Infineon CPU architecture — instructions, opcode formats, status flags, addressing, or assembly behavior. Also trigger when the user encounters TriCore mnemonics (ADD, LD.W, CALL, JEQ, MADD.Q, etc.), register names (D0-D15, A0-A15, PSW), or needs to understand disassembled TriCore code.
---

# TriCore TC1.6P/TC1.6E Instruction Set Reference

You have access to the Infineon TriCore TC1.6P & TC1.6E Instruction Set User Manual (Volume 2) as a JSONL knowledge base. Use it to answer questions about TriCore instructions, opcode formats, status flags, and CPU behavior. Always search before answering from memory — the reference is authoritative.

**Knowledge base:** `/Users/john/Code/ghidra-re-claude-code-plugin/tc27x_rag_chunks.jsonl`

## How to look things up

Query the JSONL with `Bash` using `grep | python3`. Do NOT use the `Grep` tool — JSONL lines are too long and get truncated.

### List matching chunks

```bash
grep PATTERN /Users/john/Code/ghidra-re-claude-code-plugin/tc27x_rag_chunks.jsonl | python3 -c "
import json,sys
for line in sys.stdin:
    c=json.loads(line)
    print('[{}] {} / {} (pp {})'.format(c['type'], c['title'], c['long_name'], c['pages']))
"
```

### Read full content

```bash
grep PATTERN /Users/john/Code/ghidra-re-claude-code-plugin/tc27x_rag_chunks.jsonl | python3 -c "
import json,sys
for line in sys.stdin:
    c=json.loads(line)
    print('--- {} ({}) ---'.format(c['title'], c['long_name']))
    print('Hierarchy:', ' > '.join(c['hierarchy']))
    print()
    print(c['content'])
"
```

### Grep patterns

| Goal | PATTERN |
|------|---------|
| Exact mnemonic | `'"title": "ADD"'` |
| Combined instruction | `'"title": "JGE'` (matches JGE / JGE.U) |
| Keyword (case-insensitive) | `-i 'keyword'` |
| By type | `'"type": "fpu"'` |
| By category | `-i '"category": "Branch'` |

**If grep returns nothing:** try case-insensitive (`-i`), try a partial match (e.g. `'ADD'` instead of `'"title": "ADD"'`), or broaden the search term. Multiple lookups are fine — search first to find relevant chunks, then read full content of the best matches.

## Chunk schema

Each JSONL line is a JSON object:

| Field | Description |
|---|---|
| `title` | Mnemonic name (`ADD`, `LD.W`, `ABS.B / ABS.H`) or section title |
| `long_name` | Descriptive name (`Add`, `Load Word`, `Absolute Value Packed Byte / Absolute Value Packed Half-word`) |
| `hierarchy` | Breadcrumb path array (`["Instruction Set", "CPU Instructions", "ADD"]`) |
| `type` | `instruction` / `fpu` / `section` |
| `category` | Instruction category (see list below) |
| `pages` | Source PDF page(s) |
| `content` | Cleaned reference text |

## Knowledge base contents (274 chunks)

- **instruction** (233) — every TriCore CPU instruction with syntax, opcode encoding, RTL operation, status flags, and examples.
- **fpu** (18) — floating-point instructions (ADD.F, MUL.F, FTOI, ITOF, etc.) with IEEE-754 exception flags.
- **section** (23) — instruction syntax, opcode formats, RTL functions, instruction set overview, DSP arithmetic, comparison/branch/load-store overview.

### Instruction categories

Absolute Value, Address Arithmetic, Arithmetic, Bit Field, Bit Operations, Branch, Compare, Conditional, Context, Count Leading, Division, Floating-Point, Load/Store, Logical, Min/Max, Move, Multiply/MAC, Pack/Unpack, Shift, System

### Instruction chunk structure

Each instruction chunk contains these sections in order:

1. Mnemonic + long name (e.g. `ADD` / `Add`)
2. `Description` — what the instruction does
3. Syntax + instruction format in parentheses (e.g. `(RR)`, `(RC)`, `(SRC)`)
4. Opcode encoding (bit fields)
5. RTL operation (pseudocode semantics)
6. For CPU instructions: `Status Flags` — C, V, SV, AV, SAV behavior
7. For FPU instructions: `Exception Flags` — FS, FI, FV, FZ, FU, FX behavior
8. `Examples`
9. `See Also` — related instructions

## TriCore quick reference

- **32-bit RISC+DSP**, unified processor core, 16-bit and 32-bit instruction widths
- **Data registers**: D0-D15 (32-bit), extended pairs E0-E14 (64-bit, even/odd)
- **Address registers**: A0-A15 (32-bit)
- **Special registers**: A10=SP, A11=RA, D15/A15=implicit operands for 16-bit instructions
- **Status flags in PSW**: C (carry), V (overflow), SV (sticky overflow), AV (advanced overflow), SAV (sticky advanced overflow)
- **FPU exception flags**: FS, FI, FV, FZ, FU, FX
- **Instruction formats**: RC, RR, RR1, RR2, RRR, RRR1, RRR2, SRC, SRR, SB, SBC, SBR, SBRN, SC, SLR, SLRO, SR, SRO, SRRS, SSR, SSRO, and more
- **Operand notation**: `D[n]`=data reg, `A[n]`=addr reg, `E[n]`=extended reg, `const9`=9-bit constant, `disp24`=24-bit displacement, `off18`=18-bit offset
