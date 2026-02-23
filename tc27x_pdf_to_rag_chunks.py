#!/usr/bin/env python3
"""
Convert TriCore TC1.6P/TC1.6E Instruction Set (Volume 2) PDF into JSONL chunks for RAG.

Detects instruction boundaries in Chapter 3 by scanning for mnemonic + long-name
patterns at the top of cleaned pages. Chapters 1-2 are chunked by section headings.

Usage:
    python3 tc27x_pdf_to_rag_chunks.py [input.pdf] [output.jsonl]
"""

import subprocess
import json
import re
import sys

PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else \
    '/Users/john/Downloads/infineon-tc2xx-architecture-vol2-usermanual-en.pdf'
OUTPUT_PATH = sys.argv[2] if len(sys.argv) > 2 else \
    '/Users/john/Code/ghidra-re-claude-code-plugin/tc27x_rag_chunks.jsonl'

TOTAL_PAGES = 484

# Running headers, footers, and page numbers
BOILERPLATE_RE = [
    re.compile(r'^\s*TriCore® TC1\.6P & TC1\.6E\s*$'),
    re.compile(r'^\s*32-bit Unified Processor Core\s*$'),
    re.compile(r'^\s*User Manual \(Volume 2\)\s*$'),
    re.compile(r'^\s*V1\.0 2013-07\s*$'),
    re.compile(r'^\s*\d+-\d+\s*$'),              # chapter-page (3-8)
    re.compile(r'^\s*[PL]-\d+\s*$'),              # preface/list page (P-1, L-3)
    re.compile(r'^\s*Instruction Set\s*$'),        # ch3 running header
    re.compile(r'^\s*Instruction Set Information\s*$'),
    re.compile(r'^\s*Instruction Set Overview\s*$'),
    re.compile(r'^\s*Preface\s*$'),
    re.compile(r'^\s*List of Instructions by Shortname\s*$'),
    re.compile(r'^\s*List of Instructions by Longname\s*$'),
    re.compile(r'^\s*TC\d+\s*$'),                 # figure reference labels (TC1066)
]

# Instruction category lookup by base mnemonic
CATEGORY_MAP = {
    # Move
    'MOV': 'Move', 'MOVH': 'Move', 'CMOV': 'Move', 'CMOVN': 'Move',
    # Absolute value
    'ABS': 'Absolute Value', 'ABSDIF': 'Absolute Value', 'ABSDIFS': 'Absolute Value',
    'ABSS': 'Absolute Value',
    # Min/Max
    'MIN': 'Min/Max', 'MAX': 'Min/Max', 'SAT': 'Min/Max',
    'IXMIN': 'Min/Max', 'IXMAX': 'Min/Max',
    # Conditional
    'CADD': 'Conditional', 'CADDN': 'Conditional', 'CSUB': 'Conditional',
    'CSUBN': 'Conditional', 'SEL': 'Conditional', 'SELN': 'Conditional',
    # Division
    'DIV': 'Division', 'DVADJ': 'Division', 'DVINIT': 'Division', 'DVSTEP': 'Division',
    # Shift
    'SHA': 'Shift', 'SHAS': 'Shift', 'SHUFFLE': 'Shift',
    # Bit field
    'EXTR': 'Bit Field', 'INSERT': 'Bit Field', 'IMASK': 'Bit Field',
    'DEXTR': 'Bit Field', 'BMERGE': 'Bit Field', 'BSPLIT': 'Bit Field',
    'PARITY': 'Bit Field', 'INS': 'Bit Field', 'INSN': 'Bit Field',
    'XPOSE': 'Bit Field',
    # Count leading
    'CLO': 'Count Leading', 'CLS': 'Count Leading', 'CLZ': 'Count Leading',
    # Compare
    'EQ': 'Compare', 'NE': 'Compare', 'LT': 'Compare', 'GE': 'Compare',
    'EQANY': 'Compare', 'NEZ': 'Compare',
    # Pack/unpack
    'PACK': 'Pack/Unpack', 'UNPACK': 'Pack/Unpack',
    # Context
    'SVLCX': 'Context', 'RSLCX': 'Context', 'BISR': 'Context', 'RESTORE': 'Context',
    # System
    'NOP': 'System', 'DEBUG': 'System', 'DISABLE': 'System', 'ENABLE': 'System',
    'DSYNC': 'System', 'ISYNC': 'System', 'SYSCALL': 'System',
    'MFCR': 'System', 'MTCR': 'System', 'RSTV': 'System',
    'TRAPV': 'System', 'TRAPSV': 'System', 'RFE': 'System', 'RFM': 'System',
    'WAIT': 'System', 'YIELD': 'System',
}


def clean_page(text):
    """Remove boilerplate headers/footers and collapse excessive blank lines."""
    lines = text.split('\n')
    cleaned = [l for l in lines if not any(p.match(l) for p in BOILERPLATE_RE)]
    text = '\n'.join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_chapter(raw_text):
    """Determine which chapter/section a raw page belongs to from its running header.

    Running headers appear alone on a line at the top of each page.
    Uses line-level regex matching to avoid false matches from TOC/index entries.
    """
    top = '\n'.join(raw_text.split('\n')[:10])
    if re.search(r'^\s*List of Instructions by Shortname\s*$', top, re.MULTILINE):
        return 'index'
    if re.search(r'^\s*List of Instructions by Longname\s*$', top, re.MULTILINE):
        return 'index'
    if re.search(r'^\s*Instruction Set Information\s*$', top, re.MULTILINE):
        return 'ch1'
    if re.search(r'^\s*Instruction Set Overview\s*$', top, re.MULTILINE):
        return 'ch2'
    if re.search(r'^\s*Instruction Set\s*$', top, re.MULTILINE):
        return 'ch3'
    if re.search(r'^\s*Preface\s*$', top, re.MULTILINE):
        return 'preface'
    return None


def detect_instruction_start(cleaned_text):
    """Check if a cleaned page starts with instruction mnemonic(s) + long name(s).

    Returns list of (mnemonic, long_name) tuples, or empty list.
    """
    lines = [l.strip() for l in cleaned_text.split('\n') if l.strip()]
    if len(lines) < 2:
        return []

    results = []
    i = 0
    while i < len(lines) - 1:
        mnemonic = lines[i]
        long_name = lines[i + 1]

        # Mnemonic: short ALL-CAPS with optional dots/digits
        if not re.match(r'^[A-Z][A-Z0-9.]*$', mnemonic):
            break
        if len(mnemonic) > 20:
            break
        # Skip section numbers like "3", "3.1", "3.2"
        if re.match(r'^\d+(\.\d+)*$', mnemonic):
            break

        # Long name: starts uppercase+lowercase (title case), descriptive
        if not re.match(r'^[A-Z][a-z]', long_name):
            break
        # Reject sentences (end with period) and code-like text
        if long_name.endswith('.') or any(c in long_name for c in '(=;'):
            break
        if len(long_name) > 80:
            break

        results.append((mnemonic, long_name))
        i += 2

    return results


def detect_section_heading(cleaned_text):
    """Check if cleaned page starts with a numbered section heading.

    Handles both "N.N Title" on one line and "N.N" alone with title on the next line
    (the latter is how pdftotext renders this PDF's headings).

    Returns (heading_text, level) or (None, None).
    """
    lines = [l.strip() for l in cleaned_text.split('\n') if l.strip()]
    if not lines:
        return None, None

    # Section numbers are single-digit chapter (1-9) with optional sub-sections (1-2 digits)
    # This avoids matching stray numbers like "32" in instruction descriptions

    # Pattern 1: "N.N Title" on one line
    m = re.match(r'^([1-9](?:\.\d{1,2})*)\s+(.+)$', lines[0])
    if m:
        number = m.group(1)
        title = m.group(2).strip()
        level = number.count('.') + 1
        return '{} {}'.format(number, title), level

    # Pattern 2: "N.N" alone on a line (number split from title by pdftotext)
    m = re.match(r'^([1-9](?:\.\d{1,2})*)$', lines[0])
    if m:
        number = m.group(1)
        level = number.count('.') + 1

        # For chapter-level numbers (no dots), the title was stripped as boilerplate
        if '.' not in number:
            chapter_titles = {
                '1': 'Instruction Set Information',
                '2': 'Instruction Set Overview',
                '3': 'Instruction Set',
            }
            title = chapter_titles.get(number, '')
            if title:
                return '{} {}'.format(number, title), level

        # For sub-section numbers, title is on the next non-blank line
        if len(lines) >= 2:
            next_line = lines[1]
            if re.match(r'^[A-Z]', next_line) and len(next_line) < 100:
                return '{} {}'.format(number, next_line), level

    return None, None


def classify_instruction(mnemonic, section_type):
    """Classify an instruction into (type, category)."""
    # Section-based type
    if section_type == 'fpu':
        return 'fpu', 'Floating-Point'
    if section_type == 'mmu':
        return 'mmu', 'MMU'
    if section_type == 'multithread':
        return 'multithread', 'Multithread'
    if section_type == 'pseudo':
        return 'pseudo', 'Pseudo'

    # CPU instruction — determine category
    base = mnemonic.split('.')[0]

    # Check exact base in lookup
    if base in CATEGORY_MAP:
        return 'instruction', CATEGORY_MAP[base]

    # Pattern-based categorization
    # Branch: J*, CALL*, FCALL*, LOOP*, RET, FRET
    if base.startswith(('J', 'FCALL')) or base in ('CALL', 'CALLA', 'CALLI',
            'RET', 'FRET', 'LOOP', 'LOOPU'):
        return 'instruction', 'Branch'

    # Load/Store
    if base.startswith(('LD', 'ST', 'SWAP', 'CACHE', 'CMPSWAP', 'LEA')):
        return 'instruction', 'Load/Store'

    # Multiply/MAC
    if base.startswith(('MUL', 'MADD', 'MSUB')):
        return 'instruction', 'Multiply/MAC'

    # Arithmetic (ADD, SUB, RSUB) — check address variants
    if base.startswith(('ADD', 'SUB', 'RSUB')):
        if mnemonic.endswith('.A') or mnemonic.endswith('.AT'):
            return 'instruction', 'Address Arithmetic'
        return 'instruction', 'Arithmetic'

    # SH — distinguish shift from accumulating shift-bit ops
    if base == 'SH':
        if '.T' in mnemonic:
            return 'instruction', 'Bit Operations'
        return 'instruction', 'Shift'

    # Logical with .T suffix → Bit Operations
    if base in ('AND', 'OR', 'XOR', 'XNOR', 'NAND', 'NOR', 'ANDN', 'ORN', 'NOT'):
        if '.T' in mnemonic:
            return 'instruction', 'Bit Operations'
        # Accumulating compare: AND.EQ, OR.NE, etc.
        parts = mnemonic.split('.')
        if len(parts) >= 2 and parts[1] in ('EQ', 'NE', 'LT', 'GE'):
            return 'instruction', 'Compare'
        return 'instruction', 'Logical'

    # Address arithmetic (.A suffix)
    if mnemonic.endswith('.A') or mnemonic.endswith('.AA'):
        return 'instruction', 'Address Arithmetic'

    # System instructions that use MFTR/MTFR
    if base in ('MFTR', 'MTFR'):
        return 'instruction', 'System'

    return 'instruction', ''


def format_pages(page_indices):
    """Format a list of 0-based page indices as a human-readable page range string."""
    if not page_indices:
        return ''
    first = page_indices[0] + 1
    last = page_indices[-1] + 1
    if first == last:
        return str(first)
    return '{}-{}'.format(first, last)


def main():
    # --- 1. Extract all pages via pdftotext ---
    print('Extracting full PDF text...')
    result = subprocess.run(
        ['pdftotext', PDF_PATH, '-'],
        capture_output=True, text=True
    )
    all_pages = result.stdout.split('\f')
    if all_pages and not all_pages[-1].strip():
        all_pages = all_pages[:-1]
    print('  {} pages extracted'.format(len(all_pages)))

    # --- 2. Classify each page by chapter ---
    page_chapters = [get_chapter(p) for p in all_pages]

    # --- 3. Build chunks ---
    chunks = []
    chunk_id = 0

    # -- 3a. Preface --
    preface_pages = [i for i, ch in enumerate(page_chapters) if ch == 'preface']
    if preface_pages:
        content = '\n\n'.join(clean_page(all_pages[i]) for i in preface_pages)
        content = re.sub(r'\n{3,}', '\n\n', content).strip()
        if content:
            chunk_id += 1
            chunks.append({
                'id': 'tc27x_{:04d}'.format(chunk_id),
                'title': 'Preface',
                'long_name': 'Preface',
                'hierarchy': ['Preface'],
                'type': 'section',
                'category': '',
                'pages': format_pages(preface_pages),
                'content': content,
            })

    # -- 3b. Chapters 1-2: combine all text and split by level-2 section headings --
    ch_titles = {
        'ch1': 'Instruction Set Information',
        'ch2': 'Instruction Set Overview',
    }
    for ch_name in ('ch1', 'ch2'):
        ch_pages = [i for i, ch in enumerate(page_chapters) if ch == ch_name]
        if not ch_pages:
            continue

        # Combine all cleaned chapter text
        full_text = '\n\n'.join(clean_page(all_pages[i]) for i in ch_pages)
        full_text = re.sub(r'\n{3,}', '\n\n', full_text).strip()

        # Find section boundaries: standalone "N.N" lines (level 2) followed by title
        # Pattern: line is exactly "N.N" (single-digit chapter, 1-2 digit section),
        # next non-blank line starts with uppercase (the section title)
        section_re = re.compile(
            r'^([1-9]\.\d{1,2})\n+([A-Z][A-Za-z][^\n]{0,97})',
            re.MULTILINE
        )
        splits = list(section_re.finditer(full_text))

        if not splits:
            # No sub-sections found; emit the whole chapter as one chunk
            chunk_id += 1
            chunks.append({
                'id': 'tc27x_{:04d}'.format(chunk_id),
                'title': ch_titles[ch_name],
                'long_name': ch_titles[ch_name],
                'hierarchy': [ch_titles[ch_name]],
                'type': 'section',
                'category': '',
                'pages': format_pages(ch_pages),
                'content': full_text,
            })
            continue

        # Content before the first section heading (chapter intro)
        intro = full_text[:splits[0].start()].strip()
        if len(intro) > 50:
            chunk_id += 1
            chunks.append({
                'id': 'tc27x_{:04d}'.format(chunk_id),
                'title': ch_titles[ch_name],
                'long_name': ch_titles[ch_name],
                'hierarchy': [ch_titles[ch_name]],
                'type': 'section',
                'category': '',
                'pages': format_pages(ch_pages),
                'content': intro,
            })

        # Each section heading to the next
        for idx, match in enumerate(splits):
            start = match.start()
            end = splits[idx + 1].start() if idx + 1 < len(splits) else len(full_text)
            content = full_text[start:end].strip()
            if len(content) < 50:
                continue

            number = match.group(1)
            title_line = match.group(2).strip()
            heading = '{} {}'.format(number, title_line)

            chunk_id += 1
            chunks.append({
                'id': 'tc27x_{:04d}'.format(chunk_id),
                'title': heading,
                'long_name': heading,
                'hierarchy': [ch_titles[ch_name], heading],
                'type': 'section',
                'category': '',
                'pages': format_pages(ch_pages),
                'content': content,
            })

    # -- 3c. Chapter 3: detect instruction boundaries --
    ch3_pages = [i for i, ch in enumerate(page_chapters) if ch == 'ch3']

    # Track which instruction section we're in (for type classification)
    section_type = 'cpu'  # 'cpu', 'fpu', 'mmu', 'multithread', 'pseudo'

    # Current instruction being accumulated
    cur_mnemonics = []
    cur_long_names = []
    cur_pages = []

    def flush_instruction():
        nonlocal chunk_id
        if not cur_mnemonics or not cur_pages:
            return
        content = '\n\n'.join(clean_page(all_pages[i]) for i in cur_pages)
        content = re.sub(r'\n{3,}', '\n\n', content).strip()
        if len(content) < 30:
            return
        chunk_id += 1
        title = ' / '.join(cur_mnemonics)
        long_name = ' / '.join(cur_long_names)
        itype, category = classify_instruction(cur_mnemonics[0], section_type)
        section_label = {
            'cpu': 'CPU Instructions',
            'fpu': 'FPU Instructions',
            'mmu': 'MMU Instructions',
            'multithread': 'MULTITHREAD Instructions',
            'pseudo': 'PSEUDO Instructions',
        }.get(section_type, 'Instructions')
        chunks.append({
            'id': 'tc27x_{:04d}'.format(chunk_id),
            'title': title,
            'long_name': long_name,
            'hierarchy': ['Instruction Set', section_label, title],
            'type': itype,
            'category': category,
            'pages': format_pages(cur_pages),
            'content': content,
        })

    stop_processing = False
    for pi in ch3_pages:
        if stop_processing:
            continue

        cleaned = clean_page(all_pages[pi])
        if not cleaned:
            continue

        # Check for summary list pages — stop instruction processing
        if 'LS and IP Instruction Summary Lists' in cleaned:
            flush_instruction()
            cur_mnemonics, cur_long_names, cur_pages = [], [], []
            stop_processing = True
            continue

        # Check for section headers within ch3
        heading, level = detect_section_heading(cleaned)
        if heading:
            # Update section type based on heading content
            heading_upper = heading.upper()
            if 'FPU' in heading_upper:
                flush_instruction()
                cur_mnemonics, cur_long_names, cur_pages = [], [], []
                section_type = 'fpu'
                # Create a section chunk for the FPU intro page
                chunk_id += 1
                chunks.append({
                    'id': 'tc27x_{:04d}'.format(chunk_id),
                    'title': heading,
                    'long_name': heading,
                    'hierarchy': ['Instruction Set', heading],
                    'type': 'section',
                    'category': '',
                    'pages': str(pi + 1),
                    'content': cleaned,
                })
                continue
            elif 'MMU' in heading_upper:
                flush_instruction()
                cur_mnemonics, cur_long_names, cur_pages = [], [], []
                section_type = 'mmu'
                continue
            elif 'MULTITHREAD' in heading_upper:
                flush_instruction()
                cur_mnemonics, cur_long_names, cur_pages = [], [], []
                section_type = 'multithread'
                continue
            elif 'PSEUDO' in heading_upper:
                flush_instruction()
                cur_mnemonics, cur_long_names, cur_pages = [], [], []
                section_type = 'pseudo'
                continue
            else:
                # Generic section header (e.g., "3 Instruction Set", "3.1 CPU Instructions")
                flush_instruction()
                cur_mnemonics, cur_long_names, cur_pages = [], [], []
                if len(cleaned) > 100:
                    chunk_id += 1
                    chunks.append({
                        'id': 'tc27x_{:04d}'.format(chunk_id),
                        'title': heading,
                        'long_name': heading,
                        'hierarchy': ['Instruction Set', heading],
                        'type': 'section',
                        'category': '',
                        'pages': str(pi + 1),
                        'content': cleaned,
                    })
                continue

        # Check for instruction start
        instrs = detect_instruction_start(cleaned)
        if instrs:
            flush_instruction()
            cur_mnemonics = [m for m, _ in instrs]
            cur_long_names = [ln for _, ln in instrs]
            cur_pages = [pi]
        elif cur_mnemonics:
            # Continuation of current instruction
            cur_pages.append(pi)
        # else: orphan page (no current instruction, no heading) — skip

    # Flush final instruction
    flush_instruction()

    # --- 4. Write JSONL ---
    print('Writing {} chunks to {}'.format(len(chunks), OUTPUT_PATH))
    with open(OUTPUT_PATH, 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    # --- 5. Summary ---
    types = {}
    categories = {}
    for c in chunks:
        types[c['type']] = types.get(c['type'], 0) + 1
        if c['category']:
            categories[c['category']] = categories.get(c['category'], 0) + 1

    total_chars = sum(len(c['content']) for c in chunks)
    avg_chars = total_chars // len(chunks) if chunks else 0

    print('\nDone!')
    print('  Total chunks: {}'.format(len(chunks)))
    print('  By type: {}'.format(types))
    print('  Total content: {:,} chars (~{:,} tokens)'.format(
        total_chars, total_chars // 4))
    print('  Average chunk: {:,} chars (~{:,} tokens)'.format(
        avg_chars, avg_chars // 4))

    print('\nCategories:')
    for cat, count in sorted(categories.items()):
        print('  {}: {}'.format(cat, count))

    print('\nSample chunks:')
    shown = set()
    for c in chunks:
        if c['type'] not in shown:
            shown.add(c['type'])
            print('  [{}] {} (pp {}) - {:,} chars'.format(
                c['type'], c['title'], c['pages'], len(c['content'])))
            print('    hierarchy: {}'.format(' > '.join(c['hierarchy'])))
            if c['category']:
                print('    category: {}'.format(c['category']))


if __name__ == '__main__':
    main()
