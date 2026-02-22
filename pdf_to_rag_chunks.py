#!/usr/bin/env python3
"""
Convert V850E2M CPU Architecture PDF into JSONL chunks for RAG.

Parses the document's table of contents to determine semantic chunk boundaries,
then extracts cleaned text for each chunk with hierarchical metadata.

Usage:
    python3 pdf_to_rag_chunks.py [input.pdf] [output.jsonl]
"""

import subprocess
import json
import re
import sys

PDF_PATH = sys.argv[1] if len(sys.argv) > 1 else \
    '/Users/john/Library/CloudStorage/OneDrive-Personal/Documents/Honda Pilot 2019/REN_r01us0001ej0100_v850e2m_MAH_20121017.pdf'
OUTPUT_PATH = sys.argv[2] if len(sys.argv) > 2 else \
    '/Users/john/Code/ghidra-re-claude-code-plugin/v850e2m_rag_chunks.jsonl'

TOTAL_PAGES = 473

# Lines matching these patterns are page headers/footers, not content
BOILERPLATE_RE = [
    re.compile(r'^\s*Preliminary\s*(document)?\s*$'),
    re.compile(r'^\s*Under development\s*$'),
    re.compile(r'^\s*Specifications in this document are tentative.*$'),
    re.compile(r'^\s*R01US0001EJ0100.*$'),
    re.compile(r'^\s*Oct\s+17,?\s+2012\s*$'),
    re.compile(r'^\s*Rev\.1\.00\s*$'),
    re.compile(r'^\s*Page \d+ of \d+\s*$'),
    re.compile(r'^\s*V850E2M\s*$'),
    # Running header: "PART N CHAPTER N ..." on every page
    re.compile(r'^\s*PART \d+ CHAPTER \d+.*$'),
]


def clean_page(text):
    """Remove boilerplate headers/footers and collapse excessive blank lines."""
    lines = text.split('\n')
    cleaned = [l for l in lines if not any(p.match(l) for p in BOILERPLATE_RE)]
    text = '\n'.join(cleaned)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def parse_toc(toc_text):
    """Parse table of contents text into structured entries.

    Returns list of dicts: {title, page, level}
    """
    entries = []
    lines = toc_text.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            i += 1
            continue

        # Pattern 1: "Title.....page_number"
        m = re.match(r'^(.+?)\.{2,}\s*(\d+)\s*$', line)
        if m:
            title = m.group(1).strip().rstrip('.')
            page = int(m.group(2))
            if page >= 16:  # skip front matter references
                entries.append({'title': title, 'page': page, 'level': _level(title)})
            i += 1
            continue

        # Pattern 2: section number alone on a line (e.g. "2.3\n\nTitle...page")
        m = re.match(r'^(\d+\.\d+(?:\.\d+)?)\s*$', line.strip())
        if not m:
            m = re.match(r'^([A-Z]\.\d+(?:\.\d+)?)\s*$', line.strip())
        if m:
            sec_num = m.group(1)
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                m2 = re.match(r'^(.+?)\.{2,}\s*(\d+)\s*$', lines[j])
                if m2:
                    title = '{} {}'.format(sec_num, m2.group(1).strip().rstrip('.'))
                    page = int(m2.group(2))
                    entries.append({'title': title, 'page': page, 'level': _level(title)})
                    i = j + 1
                    continue
        i += 1

    return entries


def _level(title):
    """Determine nesting level from title format."""
    if re.match(r'^PART \d+', title):
        return 0
    if re.match(r'^CHAPTER \d+', title):
        return 1
    if re.match(r'^APPENDIX [A-Z]', title):
        return 1
    if re.match(r'^\d+\.\d+\.\d+', title):
        return 3
    if re.match(r'^\d+\.\d+', title):
        return 2
    if re.match(r'^[A-Z]\.\d+\.\d+', title):
        return 3
    if re.match(r'^[A-Z]\.\d+', title):
        return 2
    # Instruction mnemonics: mostly caps, possibly with dots (ABSF.D) or
    # mixed case (Bcond), short
    if re.match(r'^[A-Z][A-Za-z0-9\.]+$', title) and len(title) <= 12:
        return 4
    return 2


def add_hierarchy(entries):
    """Annotate each entry with its full hierarchy breadcrumb path."""
    stack = {}
    for e in entries:
        stack[e['level']] = e['title']
        for k in list(stack):
            if k > e['level']:
                del stack[k]
        e['hierarchy'] = [stack[k] for k in sorted(stack)]
    return entries


def classify_chunk(entry, content):
    """Determine chunk type and extract instruction category if applicable."""
    title = entry['title']
    hier = ' > '.join(entry['hierarchy']).upper()

    # Instruction entries are level 4 under an INSTRUCTIONS chapter
    if entry['level'] == 4 and 'INSTRUCTION' in hier:
        cat_match = re.search(r'<([^>]+)>', content)
        category = cat_match.group(1).strip() if cat_match else ''
        return 'instruction', category

    # Classify by title OR by hierarchy context
    if re.search(r'register', title, re.I) or 'REGISTER SET' in hier:
        return 'register', ''
    if re.search(r'exception', title, re.I):
        return 'exception', ''
    if re.search(r'protection', title, re.I):
        return 'protection', ''

    return 'section', ''


def main():
    # --- 1. Extract all pages via pdftotext (form-feed separated) ---
    print('Extracting full PDF text...')
    result = subprocess.run(
        ['pdftotext', PDF_PATH, '-'],
        capture_output=True, text=True
    )
    all_pages = result.stdout.split('\f')
    # Last element after final \f is usually empty
    if all_pages and not all_pages[-1].strip():
        all_pages = all_pages[:-1]
    print('  {} pages extracted'.format(len(all_pages)))

    # --- 2. Parse TOC (pages 5-15, indices 4-14) ---
    print('Parsing table of contents...')
    toc_text = '\n'.join(all_pages[4:15])
    entries = parse_toc(toc_text)
    entries = add_hierarchy(entries)
    print('  {} TOC entries found'.format(len(entries)))

    # --- 3. Compute page ranges ---
    for i in range(len(entries)):
        start = entries[i]['page']
        end = entries[i + 1]['page'] - 1 if i + 1 < len(entries) else TOTAL_PAGES
        entries[i]['start_page'] = start
        entries[i]['end_page'] = max(end, start)

    # --- 4. Build chunks ---
    print('Building chunks...')
    chunks = []
    for i, entry in enumerate(entries):
        si = entry['start_page'] - 1          # 0-based index
        ei = entry['end_page']                 # exclusive for slice
        if si >= len(all_pages):
            continue
        ei = min(ei, len(all_pages))

        content = '\n\n'.join(clean_page(p) for p in all_pages[si:ei])
        content = re.sub(r'\n{3,}', '\n\n', content).strip()

        # Skip near-empty container headings (PART title pages etc.)
        if len(content) < 100 and entry['level'] <= 1:
            continue
        if len(content) < 30:
            continue

        chunk_type, category = classify_chunk(entry, content)

        chunk = {
            'id': 'v850e2m_{:04d}'.format(i),
            'title': entry['title'],
            'hierarchy': entry['hierarchy'],
            'type': chunk_type,
            'category': category,
            'pages': '{}-{}'.format(entry['start_page'], entry['end_page'])
                     if entry['start_page'] != entry['end_page']
                     else str(entry['start_page']),
            'content': content,
        }
        chunks.append(chunk)

    # --- 5. Write JSONL ---
    print('Writing {} chunks to {}'.format(len(chunks), OUTPUT_PATH))
    with open(OUTPUT_PATH, 'w') as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + '\n')

    # --- Summary ---
    types = {}
    for c in chunks:
        types[c['type']] = types.get(c['type'], 0) + 1

    total_chars = sum(len(c['content']) for c in chunks)
    avg_chars = total_chars // len(chunks) if chunks else 0

    print('\nDone!')
    print('  Total chunks: {}'.format(len(chunks)))
    print('  By type: {}'.format(types))
    print('  Total content: {:,} chars (~{:,} tokens)'.format(
        total_chars, total_chars // 4))
    print('  Average chunk: {:,} chars (~{:,} tokens)'.format(
        avg_chars, avg_chars // 4))

    # Show a few examples
    print('\nSample chunks:')
    shown = set()
    for c in chunks:
        if c['type'] not in shown:
            shown.add(c['type'])
            print('  [{}] {} (pp {}) - {:,} chars'.format(
                c['type'], c['title'], c['pages'], len(c['content'])))
            print('    path: {}'.format(' > '.join(c['hierarchy'])))
            if c['category']:
                print('    category: {}'.format(c['category']))


if __name__ == '__main__':
    main()
