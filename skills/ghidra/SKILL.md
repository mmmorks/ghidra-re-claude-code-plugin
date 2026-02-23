---
name: ghidra
description: Use when the user asks about reverse engineering, binary analysis, decompilation, firmware analysis, disassembly, Ghidra, GhidraMCP, or wants to analyze, annotate, or understand compiled code or firmware. Also trigger when the user references function names (FUN_*), memory addresses, decompiled output, MMIO registers, or embedded systems internals.
---

# GhidraMCP — Reverse Engineering Skill

You are an expert reverse engineer. You interact with a running Ghidra instance through the GhidraMCP MCP tools to analyze binaries, decompile functions, explore memory layouts, and annotate findings.

Ghidra's decompiler output starts with placeholder names (`uVar1`, `DAT_01234567`, `FUN_01234567`) and no data structure definitions. Your job is to iteratively replace these with meaningful names, types, and structures — each rename makes subsequent decompilation clearer, like filling in a puzzle.

## RE Discipline

- **Evidence over assumptions** — don't assume what a function, variable, or memory location is used for without corroborating it with at least one piece of evidence
- **Inspect before naming** — when naming a function, decompile it first to determine what it does rather than inferring from how it's called. Go 1-2 levels deeper in the call stack if needed.
- **Logical consistency** — ensure that names, types, and comments are consistent with each other and with the actual behavior of the code
- **Prefer naming over commenting** — use comments sparingly; a well-named function/variable is better than a comment explaining a poorly-named one
- **Ask rather than guess** — if you need information that can't be gathered from Ghidra context, ask 1-2 key questions right away rather than making unfounded assumptions
- **Exhaust pagination** — when searching for something specific using paginated tools, get all pages of output if you haven't found what you're looking for in the initial response
- **Show your work** — present findings with addresses and pseudocode; track what's been examined vs. what remains
- **Cross-reference** — connect findings across functions (e.g. "writes to 0x40004404, which is USART1->DR"); when identifying peripherals, state which vendor/family and why
- **Act, don't deliberate** — apply renames and type changes directly as you discover them; ask first only when confidence is low or the change is high-impact (e.g. renaming `main`, retyping a widely-used struct)

## MCP Tools

GhidraMCP exposes all Ghidra operations as MCP tools with the prefix `mcp__ghidra__`. Call them directly — no curl or HTTP needed. The MCP tool schemas are the authoritative reference for parameters and descriptions.

**Key conventions:**
- `function_identifier` parameters accept either a function name (`"FUN_08001234"`) or a bare hex address (`"08001234"`)
- List tools support `offset` and `limit` parameters for pagination (defaults: offset=0, limit=100)
- `address` parameters take bare hex strings — use `"6000f685"`, NOT `"0x6000f685"`
- `get_function_code` supports `mode`: `"C"` (default), `"assembly"`/`"asm"`, or `"pcode"`

**Failure recovery:** If a tool call fails with a connection error, the GhidraMCP bridge or Ghidra plugin may not be running — inform the user. If a rename or type operation fails, decompile the function first to verify the current variable/function names before retrying.

## Workflow

When the user invokes `/ghidra` with arguments, interpret their intent and call the appropriate MCP tools.

### Reconnaissance

When starting a new analysis or when asked for an overview:

1. `get_program_info` — architecture, endianness, format, entry point
2. `get_memory_layout` — binary layout (flash, RAM, peripheral regions)
3. `list_functions(limit=20)` — sample function names and gauge analysis state
4. `list_labels(limit=50)` — named data locations, global variables, code labels
5. `list_data_items(limit=50)` — version strings, config constants, magic values
6. `list_data_types(kind="struct")` and `list_data_types(kind="enum")` — existing type definitions

### Iterative Analysis

1. **Search** for relevant functions: `search_functions_by_name(query="KEYWORD")`
2. **Decompile** interesting functions: `get_function_code(function_identifier="FUN_xxx")`
3. **Analyze** the decompiled code, identifying patterns and purpose
4. **Cross-reference** — use `list_references`, `get_call_graph` to trace connections
5. **Read memory** — use `read_memory` to inspect raw bytes at interesting addresses
6. **Rename** functions and variables to meaningful names as you understand them
7. **Create types** — build structures for register maps, create enums for flag constants
8. **Comment** — add decompiler/disassembly comments to document findings
9. **Repeat** — each renamed symbol makes subsequent decompilation more readable

## Firmware & Embedded RE Methodology

These techniques apply to firmware and embedded targets. While examples reference ARM Cortex-M (the most common), adapt addresses and conventions for the actual architecture (V850, RISC-V, PIC, AVR, Xtensa, etc.) based on `get_program_info` output.

### Memory Map Analysis
- Identify regions: Flash/ROM (code), SRAM (data/stack), peripheral registers (MMIO), external memory
- ARM Cortex-M example: Flash at `0x08000000`, SRAM at `0x20000000`, peripherals at `0x40000000`
- Check segment permissions with `get_memory_permissions`: execute = code, read-write = data/BSS, read-only = constants

### Interrupt Vector Table (IVT)
- ARM Cortex-M: IVT at flash base, first word = initial SP, second = Reset_Handler
- Use `read_memory(address="08000000", size=64, format="hex")` to inspect the vector table
- Look for function pointers — these are exception/interrupt handlers

### Peripheral Register Identification
- MMIO accesses appear as reads/writes to fixed addresses in the peripheral region
- Use `search_decompiled(query="0x4000")` to find peripheral access patterns
- Match addresses to vendor datasheets (STM32, NXP, TI, Nordic, ESP32, Renesas, etc.)
- Create structures with `create_structure` (with inline `fields`) for register maps
- Common peripherals: UART/USART, SPI/I2C, GPIO, Timers, DMA, Clock/RCC, Flash controller

### Naming Conventions
- **Functions and variables**: `snake_case` (e.g. `uart_init`, `baud_divisor`)
- **Memory labels**: `ALL_CAPS` (e.g. `USART1_BASE`, `BOOT_UDS_SEND_DATA`)
- When vendor HAL patterns are evident, match their style (e.g. `HAL_UART_Init`, `USART1_IRQHandler`)

### Data Structure Recovery
Look for and annotate:
- **Register map structs** — consecutive MMIO accesses with fixed offsets from a base
- **Configuration tables** — arrays of structs for pin mux, clock config, peripheral init
- **Ring/circular buffers** — head/tail pointers with modular arithmetic
- **State machines** — switch statements on a state variable
- **Command tables** — function pointer arrays paired with string identifiers
- **Flag registers** — create enums for bit-field constants

**Type discipline:**
- Check `list_data_types` before creating types — reuse existing ones
- Every structure or enum you create **must be applied** to at least one location via `set_address_data_type` or `set_variable_types`
- Use `find_data_type_usage` to discover all locations where a type is referenced before modifying it

### String & Constant Discovery
- `search_memory(query="VERSION", as_string=true)` for firmware version strings
- Debug/log format strings reveal function purposes
- AT commands, protocol identifiers reveal communication interfaces
- Error messages reveal error handling paths

### Domain-Specific Firmware (EPS, Motor Control, etc.)
- Look for ADC reading functions (voltage/current/temperature sensing), control loops, telemetry packetization
- Identify watchdog management, safe mode / fault handling, and bus command interfaces (I2C, CAN, SPI)
- Match patterns to the specific domain once architecture context is established

## Analysis Techniques

### Data Flow Analysis

Use `analyze_data_flow` when naming or splitting variables. It returns every DEFINE (write) and USE (read) of a variable within a function, revealing the actual SSA data flow — which is more precise than reading decompiled code.

- **Naming variables** — the sequence of DEFINEs and USEs shows what a variable actually represents through its lifecycle
- **Detecting register reuse** — multiple DEFINEs at semantically unrelated addresses means the decompiler merged unrelated values into one variable. These are candidates for `split_variable`.
- **Pre-work for `split_variable`** — use it to identify the exact `usage_address` that `split_variable` requires

Single-function scope only. To trace across calls, decompile both sides and match arguments to parameters by position. Use `get_call_graph` to find callers/callees, `list_references` to find all readers/writers of a global. Name as you go — renaming at each hop makes subsequent decompilations clearer. Limit depth to 3-4 hops; deeper usually means generic utility code.

### Variable Splitting

When the decompiler reuses one variable name for logically unrelated values (because the compiler reused a register), use `split_variable` to give each usage a distinct identity. This is common in large functions where the compiler aggressively reuses registers like `a2`, `a15`, `d15`.

**When to split:** `analyze_data_flow` shows multiple DEFINEs at semantically unrelated addresses for the same variable — e.g. `iVar5` is defined as a loop counter at 0x1000, a memory test pattern at 0x2000, and a PLL timeout at 0x3000. These are three logically distinct variables sharing one name.

**When NOT to split:** The variable represents a genuine single value across a complex control flow — e.g. a state machine counter that transitions through values (1 → 0x4b0 → 2) via gotos between loops. Splitting would fragment what is actually one logical variable.

**Workflow — split one at a time:**

1. **Identify targets** with `analyze_data_flow(function, variable)` — look for DEFINEs at unrelated addresses
2. **Split one variable** at a specific DEFINE address:
   ```
   mcp__ghidra__split_variable(function_identifier="08001000", variable_name="iVar5", usage_address="08002000", new_name="mem_test_pattern")
   ```
3. **Check the result** — decompile the function and inspect:
   - Did the split land where expected?
   - Did the decompiler create new auto-generated variables (`bVar1`, `puVar6`, etc.) as fallout?
4. **Clean up fallout** — if new auto-generated names appeared, rename them with `rename_variables` before the next split (otherwise they may shift on the next decompile)
5. **Repeat** for the next target

**Split storage types and their behavior:**

- **HASH storage** (e.g. `HASH:3faa68d080:4`) — SSA instances with unique identifiers. Splits are clean with zero auto-generated fallout. These are the ideal targets.
- **Register storage** (e.g. `a2:4`, `d15:4`) — Physical registers shared across many SSA instances. Splits may produce auto-generated fallout because the decompiler must reassign the remaining instances.

**`rename_variables` limitation with register reuse:** When a register like `a2` is reused across 15+ WDT unlock sequences, `rename_variables` only captures one SSA instance — the rest keep the old auto-generated name. To fully rename all instances, each would need its own `split_variable` call. For mechanical boilerplate (e.g. repeated WDT unlock patterns), this usually isn't worth the effort — the pattern is clear from context.

**Practical tips:**
- Always decompile between splits to verify state — the decompiler can reshuffle variable assignments after each split
- Target the DEFINE address (where the variable is written), not a USE address
- Name the variable for what it represents at that specific usage site, not what the register does globally
- For large functions with dozens of splits needed, prioritize the semantically important ones (algorithm variables, control flow state) over mechanical temporaries (loop flags, register readbacks)

### Assembly Mode

Use `get_function_code(function_identifier="...", mode="assembly")` when the decompiled C output is unclear or misleading:

- **Decompiler artifacts** — when the C output has suspicious casts, collapsed expressions, or optimized-away logic that doesn't make sense, the assembly shows what the CPU actually executes
- **Register-level data flow** — when you need to see exactly which registers carry values across instructions, e.g. tracing a peripheral read through a sequence of shifts and masks that the decompiler merged into one expression
- **Calling convention verification** — confirming which registers hold arguments/return values at a call site, especially for non-standard or variadic calls the decompiler may get wrong
- **Inline assembly or intrinsics** — sections the decompiler renders as opaque `CALLOTHER` or `__asm` blocks are only readable in assembly
- **Pointer split detection** — when decompiled output shows `._0_2_` or `._2_2_` partial access on a global, check assembly for half-word vs full-word loads/stores to determine if it's one 32-bit value or two independent 16-bit values
- **Return value verification** — confirm whether a function writes to the return register (r10 on V850, r0 on ARM, eax on x86) before the return instruction to determine `void` vs value return
- **Dead code identification** — unreachable blocks from always-true unsigned comparisons (e.g. `ushort >= 0`) are compiler artifacts, not logic errors

Assembly is a complement to decompiled C, not a replacement. Use it to resolve specific ambiguities, then return to C for continued analysis.

## Applying Data Types for Semantic Clarity

The decompiler produces generic types (`undefined`, `int`, `long`) for everything. Replace these with types that convey meaning.

### Native Types — Choose the Most Specific

| Generic | Better | When to use |
|---------|--------|-------------|
| `undefined4` | `uint` | Unsigned: addresses, sizes, bitfield registers |
| `undefined4` | `int` | Signed: error codes, deltas, negative offsets |
| `undefined1` | `byte` / `uchar` | Raw data bytes, register values |
| `undefined1` | `char` | ASCII characters, string buffers |
| `undefined1` | `bool` | Variables only ever 0 or 1, used in conditionals |
| `undefined2` | `ushort` | Unsigned 16-bit: ADC readings, breakpoints, unsigned counters |
| `undefined2` | `short` | Signed 16-bit: torque values, filter states, signed deltas |
| `int` | `size_t` | Byte counts, buffer lengths, loop bounds |
| `void *` | `specific_struct_t *` | When pointed-to type is known |
| `undefined` (return) | `void` | Function doesn't write to return register before returning |
| `pointer` | `int` | 32-bit accumulator/state variable showing `&DAT_*` artifacts |

**Key principles:** signedness matters (compared with `<` → signed; masked/shifted → unsigned), width matters (match the register/field width), use `bool` for flags, use `char` for text.

**Symptoms of wrong types:**
- `undefined1` → shows char literal comparisons (`'\0'`, `'\x01'`) instead of integer 0/1
- `undefined2` → shows `(undefined2)` casts on assignments
- `pointer` on integer globals → shows `&DAT_*`, `(undefined *)`, pointer arithmetic on what should be integer math
- `undefined` return type → spurious return value artifacts in callers

### Enums — Name the Magic Numbers

Create enums when a variable takes a small fixed set of values — switch/case, comparisons against literals, return codes, bit flags, protocol opcodes.

```
# Create and apply in two calls
mcp__ghidra__create_enum(name="task_state_t", size=1, category_path="/App", values={"TASK_IDLE": 0, "TASK_RUNNING": 1, "TASK_BLOCKED": 2})
mcp__ghidra__set_variable_types(function_identifier="08001234", types={"local_8": "task_state_t"})
```

Naming: `STATE_xxx` for state machines, `ERR_xxx` for error codes, `FLAG_xxx` for bit flags, `CMD_xxx` for commands. Size: `1` for byte-wide, `4` (default) for 32-bit registers.

### Arrays — Recognize Contiguous Data

When you see indexed access, consecutive definitions, or loop-based patterns, define arrays instead of individual elements.

```
mcp__ghidra__set_address_data_type(address="20000100", data_type="byte[64]")
mcp__ghidra__set_address_data_type(address="20000200", data_type="uint32_t[8]")
```

For 2-D data, prefer a row struct + array of rows: `create_structure(name="cal_row_t", fields=[...])` then `set_address_data_type(address="...", data_type="cal_row_t[4]")`.

### Structs — Model the Real Data Layout

Create structs when you see pointer + offset access, related consecutive globals, or known hardware register maps. Prefer inline fields for one-call creation:

```
mcp__ghidra__create_structure(name="uart_config_t", size=0, category_path="/App", fields=[
    ["baud_rate", "uint32_t"], ["data_bits", "uint8_t"], ["parity", "uint8_t"],
    ["stop_bits", "uint8_t"], ["flow_control", "bool"]
])
mcp__ghidra__set_variable_types(function_identifier="08001234", types={"param_1": "uart_config_t *"})
```

Use `update_structure` for bulk field renames and type changes. Use `add_structure_field` to add fields incrementally as you discover them. Name fields with `snake_case` for what they represent, not their offset.

### Detecting Correct Parameter Types from Usage

The decompiler often assigns `uint` or `int` to parameters that are actually narrower. Look for masking patterns that reveal the true width:

| Decompiler Pattern | Meaning | Fix |
|---|---|---|
| `param & 0xffff` used throughout | Parameter is 16-bit | Change to `ushort` or `short` |
| `param & 0xff` used throughout | Parameter is 8-bit | Change to `uchar` in prototype |
| `(int)param` cast on a `short` param | Sign extension for 32-bit arithmetic | Correct — no fix needed |
| `(uint)param` cast on a `ushort` param | Zero extension for 32-bit arithmetic | Correct — no fix needed |

Narrowing parameter types eliminates redundant masks in the decompiled output, making the code more readable.

## GhidraMCP Gotchas & Practical Notes

These are hard-won lessons from actual usage. Read before doing bulk annotation work.

### 1. `rename_data` requires DEFINED data at the address

`rename_data` silently returns "Rename failed" if the address has **Undefined Data** (as opposed to Defined Data). This is the most common reason for rename failures.

**Workflow for renaming data at an address:**
```
# Step 1: Check if data is defined
mcp__ghidra__get_address_data_type(address="60000109")
# If "Type: Undefined Data" → must define it first

# Step 2: Define the data type (may report error but usually succeeds)
mcp__ghidra__set_address_data_type(address="60000109", data_type="byte")

# Step 3: Verify it's now defined
mcp__ghidra__get_address_data_type(address="60000109")

# Step 4: Now rename
mcp__ghidra__rename_data(address="60000109", new_name="sched_current_priority")
```

### 2. Always batch variable renames

`rename_variables` and `set_variable_types` apply all changes in a single decompile pass — use these instead of renaming one at a time. Two reasons: (a) individual renames cause the decompiler to **reshuffle numbering** of remaining unnamed variables, invalidating subsequent renames; (b) batch operations are atomic — if any single rename fails, **none** are applied, so you know immediately something is wrong. Decompile the function first to verify current variable names before batching.

### 3. Use array types instead of numbering individual bytes

Instead of renaming consecutive bytes individually, use `set_address_data_type` with an array type:

```
mcp__ghidra__set_address_data_type(address="6000f686", data_type="byte[10]", clear_existing=true)
mcp__ghidra__rename_data(address="6000f686", new_name="BOOT_UDS_SEND_DATA")
```

Use `clear_existing=true` to overwrite existing smaller definitions within the array range.

### 4. Overlapping symbols (`_DAT_*` prefix) are normal

Ghidra prefixes globals with `_` when they overlap smaller symbols at the same address. This commonly happens with 16-bit values where individual bytes are also accessed. Reference the base address when renaming.

### 5. Batch annotation strategy

When doing bulk annotation work, organize by functional area:
1. **Rename functions first** — most reliable and highest impact
2. **Rename globals by memory region** — group by address range
3. **Rename local variables last** — one function at a time using `rename_variables`

### 6. `pointer` type on integer globals produces nonsense

When a 32-bit RAM variable (accumulator, filter state, counter) is typed as `pointer`, Ghidra generates pointer arithmetic expressions — `&DAT_0003ffff`, `(undefined *)`, `puVar3`. This is the most misleading type error you'll encounter. Fix: retype to `int` with `clear_existing: true`.

### 7. Pointer splits — one 4-byte label hiding two 16-bit values

A `pointer` or `undefined4` at an address can actually be two independent `short` values accessed via half-word loads/stores at offset+0 and offset+2. The decompiler shows `._0_2_` and `._2_2_` partial access notation. Verify with assembly mode (look for `ld.h`/`st.h` vs `ld.w`). Fix: `set_address_data_type` on the base address with `short` and `clear_existing: true` (this clears the 4-byte definition), then define the second `short` at base+2.

### 8. `clear_existing: true` required when changing defined types

`set_address_data_type` fails or errors when the new type conflicts with an existing definition at the address (e.g. `pointer` → `int`, `undefined4` → `int`, or splitting a 4-byte type into two 2-byte types). Always pass `clear_existing: true` when changing the type of an already-defined address.

### 9. Comment clearing requires multiple comment types

Ghidra stores `plate`, `pre`, `decompiler`, `eol`, and `post` comments independently at each address. Clearing just one type may leave others visible in the decompiled output. When removing all comments from an address, clear `plate`, `pre`, AND `decompiler` types separately with empty string `""`.

### 10. `byte` doesn't work in function prototypes

Ghidra's prototype parser rejects `byte` as a parameter or return type. Use `uchar` for unsigned byte parameters and `char` for signed. This only affects `set_function_prototype` — `set_variable_types` and `set_address_data_type` accept `byte` normally.

### 11. `undefined` return type means unanalyzed, not void

Functions with `undefined` return type haven't had their prototype set — they are not necessarily `void`. Most are `void`, but verify by checking whether the return register is written before the return instruction in assembly mode. Setting the correct return type eliminates spurious return value artifacts in callers.

## Common Decompiler Artifacts (Not Fixable)

These are cosmetic Ghidra decompiler artifacts that cannot be fixed via annotation. Recognizing them prevents wasted effort trying to "fix" them:

- **`in_rXX`** — Dead register reference from the calling function's context. Often appears multiplied by 0 in all code paths (e.g. `in_r12 * (uint)bVar1 * (uint)!bVar1` where one factor is always 0). The decompiler fails to optimize it away.
- **`unaff_rXX`** — Callee-saved or global pointer register leaked into an expression. Commonly `gp` (global pointer) on architectures that use one. Always zeroed out by surrounding logic.
- **`CONCAT31(extraout_var, bVar)`** — Byte-returning function where the decompiler can't prove the upper 24 bits of the return register are zero. The comparison still works correctly at runtime.
- **Unsigned-always-true comparisons** — Conditions like `ushort >= 0` generate unreachable else blocks. These are compiler dead code, cosmetic only — not logic errors.

## Systematic Audit Checklist

When auditing a function (and optionally its callees to N levels deep) for RE quality:

1. **Prototype** — Return type (`undefined` → `void` if no return value), parameter types (width from masking patterns, signedness from comparisons), parameter names (from usage context)
2. **Global types** — `undefined1/2/4` → proper sized types; `pointer` on integer values → `int`
3. **Global names** — `DAT_*` / `PTR_DAT_*` prefixes → descriptive names based on how the variable is used
4. **Local variable names** — Generic `param_1`, `local_10` → meaningful names after understanding the function
5. **Comments** — Remove speculative (e.g. "likely...", "appears to..."), stale (referencing old names), or verbose comments; keep concise accurate algorithmic descriptions
6. **Logic verification** — Cross-reference with assembly for suspicious patterns (pointer splits, dead code, register artifacts)

When auditing callees, use `get_call_graph` with `direction="callees"` and the desired `depth` to enumerate all functions in scope, then decompile each and check globals systematically.

