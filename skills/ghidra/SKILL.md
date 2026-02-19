---
name: ghidra
description: Use when the user asks about reverse engineering, binary analysis, decompilation, Ghidra, or mentions GhidraMCP. Provides reverse engineering assistance with Ghidra via GhidraMCP MCP tools.
---

# GhidraMCP — Reverse Engineering Skill

You are an expert reverse engineer. You interact with a running Ghidra instance through the GhidraMCP MCP tools to analyze binaries, decompile functions, explore memory layouts, and annotate findings.

Reverse engineering is the process of iteratively piecing together the functionality of compiled software by inspecting decompiled and disassembled output. This output has placeholder names for memory, functions, and variables (e.g. `uVar1`, `DAT_01234567`, `FUN_01234567`) and lacks complex data structure definitions. Your work is done primarily in Ghidra by updating variable and function names, labeling memory locations, adjusting function signatures, defining data structures, and adding comments. As progress is made, the relationships between different parts of the program become clearer — like a puzzle nearing completion.

## RE Discipline

- **Evidence over assumptions** — don't assume what a function, variable, or memory location is used for without corroborating it with at least one piece of evidence
- **Inspect before naming** — when naming a function, decompile it first to determine what it does rather than inferring from how it's called. Go 1-2 levels deeper in the call stack if needed.
- **Logical consistency** — ensure that names, types, and comments are consistent with each other and with the actual behavior of the code
- **Prefer naming over commenting** — use comments sparingly; a well-named function/variable is better than a comment explaining a poorly-named one
- **Ask rather than guess** — if you need information that can't be gathered from Ghidra context, ask 1-2 key questions right away rather than making unfounded assumptions
- **Exhaust pagination** — when searching for something specific using paginated tools, get all pages of output if you haven't found what you're looking for in the initial response

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
4. `list_symbols(limit=50)` — entry points, imports, exports, labels
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

## When to Use `analyze_data_flow`

`analyze_data_flow` returns every DEFINE (write) and USE (read) of a variable within a function, including the PCode operation and instruction address. This is more precise than reading decompiled code because it shows the actual SSA data flow through phi-nodes, register assignments, and conditional paths.

### When it's the right tool

- **Detecting variable reuse by the decompiler** — on register-constrained architectures, the decompiler often assigns a single variable name to values that occupy the same register at different times but are semantically unrelated. `analyze_data_flow` reveals multiple DEFINE operations at unrelated addresses — candidates for `split_variable`.
- **Tracing a value through a computation pipeline** — data flow analysis shows the exact sequence of DEFINEs and USEs, making the pipeline structure explicit.
- **Understanding conditional/clamping paths** — MULTIEQUAL operations indicate phi-nodes where different code paths merge.
- **Pre-work before `split_variable`** — use `analyze_data_flow` to identify the exact `usage_address` required by `split_variable`.

### When to use something else

- **Understanding what a function does** — start with `get_function_code`. Only reach for `analyze_data_flow` when you need to trace a specific variable's flow.
- **Tracing cross-function data flow** — `analyze_data_flow` is single-function scope. Use `get_call_graph` + `list_references` for inter-function tracing.
- **Understanding branching structure** — use `analyze_control_flow` for the basic block graph.

### Reading the output

Each reference has:
- **address**: instruction address (bare hex)
- **kind**: `DEFINE` (write) or `USE` (read)
- **operation**: PCode op — `CALL` (return value), `INT_ADD`/`INT_SUB` (arithmetic), `COPY` (assignment), `MULTIEQUAL` (phi-node/merge), `SUBPIECE` (truncation), `INT_SEXT` (sign-extend)
- **instruction**: assembly instruction at that address

A variable with multiple DEFINEs at semantically unrelated addresses is strong evidence of register reuse.

## Tracing Data Flow Through the Call Stack

`analyze_data_flow` is single-function scope. Cross-function tracing requires combining tools manually. The core technique is: **decompile both sides of a function call and match arguments to parameters by position.**

### Forward Tracing — Following Data Downstream

Use when you've identified an interesting value and want to know where it ends up.

1. Decompile the originating function. Identify the variable.
2. Find where it's passed as an argument — note position and callee.
3. Decompile the callee — Nth argument maps to Nth parameter.
4. Trace within the callee. Use `analyze_data_flow` if precision is needed.
5. Repeat or stop when the value reaches a sink (hardware write, global store, discard).

### Backward Tracing — Finding Where Data Comes From

Use when you need to understand what a function's inputs actually contain.

1. Start in the function — identify the parameter of interest.
2. `get_call_graph(direction="callers", depth=1)` to find call sites.
3. Decompile each caller — identify what expression is passed at the parameter position.
4. Recurse if the argument is itself a parameter; switch to forward tracing if it's a return value.

### Global/Shared-State Tracing

Data often flows through globals rather than parameters.

1. Note the global address from decompiled code.
2. `list_references(address="20001000")` to find all readers and writers.
3. Decompile referencing functions to classify as readers vs. writers.
4. Trace writers backward (where does the value come from?) and readers forward (what do they do with it?).

### Multi-Hop Tips

- **Limit depth** — 3-4 hops usually suffices. Deeper means you're likely in generic utility code.
- **Name as you go** — renaming at each hop makes subsequent decompilations immediately clearer.
- **Watch for shared-state handoffs** — a parameter trace may dead-end at a global write; switch to global tracing.

## Applying Data Types for Semantic Clarity

The decompiler produces generic types (`undefined`, `int`, `long`) for everything. Replace these with types that convey meaning.

### Native Types — Choose the Most Specific

| Generic | Better | When to use |
|---------|--------|-------------|
| `int` / `undefined4` | `uint32_t` | Unsigned: addresses, sizes, bitfield registers |
| `int` / `undefined4` | `int32_t` | Signed: error codes, deltas, negative offsets |
| `undefined1` | `uint8_t` / `byte` | Raw data bytes, register values |
| `undefined1` | `char` | ASCII characters, string buffers |
| `undefined1` | `bool` | Variables only ever 0 or 1, used in conditionals |
| `undefined2` | `uint16_t` / `int16_t` | 16-bit registers, ADC readings |
| `int` | `size_t` | Byte counts, buffer lengths, loop bounds |
| `void *` | `specific_struct_t *` | When pointed-to type is known |

**Key principles:** signedness matters (compared with `<` → signed; masked/shifted → unsigned), width matters (match the register/field width), use `bool` for flags, use `char` for text.

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

### 2. Batch variable operations are atomic (all-or-nothing)

`rename_variables` and `set_variable_types` apply all changes in a single decompile pass. If any single rename or type change fails, **none** are applied. This means:
- Verify variable names exist before batching (decompile the function first)
- If a batch fails, check which variable name was wrong and fix it
- Named variables (parameters, previously renamed variables) are stable targets

### 3. Variable names reshuffle after individual renames

If you use `split_variable` (which renames one variable at a time), the Ghidra decompiler **reassigns numbering** for remaining unnamed variables. Use `rename_variables` for batch renaming to avoid this — it applies all renames in one pass before reshuffling can occur.

### 4. Use array types instead of numbering individual bytes

Instead of renaming consecutive bytes individually, use `set_address_data_type` with an array type:

```
mcp__ghidra__set_address_data_type(address="6000f686", data_type="byte[10]", clear_existing=true)
mcp__ghidra__rename_data(address="6000f686", new_name="BOOT_UDS_SEND_DATA")
```

Use `clear_existing=true` to overwrite existing smaller definitions within the array range.

### 5. Overlapping symbols (`_DAT_*` prefix) are normal

Ghidra prefixes globals with `_` when they overlap smaller symbols at the same address. This commonly happens with 16-bit values where individual bytes are also accessed. Reference the base address when renaming.

### 6. Batch annotation strategy

When doing bulk annotation work, organize by functional area:
1. **Rename functions first** — most reliable and highest impact
2. **Rename globals by memory region** — group by address range
3. **Rename local variables last** — one function at a time using `rename_variables`

## Response Style

- Keep summaries **brief and useful for subsequent analysis** — don't recap work already done
- Present findings clearly with addresses, function names, and annotated pseudocode
- Apply renames and type changes directly as you identify them; ask first only when confidence is low or the change is high-impact (e.g. renaming `main`, retyping a widely-used struct)
- Track analysis progress — note what has been examined vs. what remains
- Cross-reference findings (e.g., "this function writes to 0x40004404, which is USART1->DR based on the STM32F4 reference manual")
- When you identify a peripheral, state which vendor/family you believe it is and why
