import os
import re
from pathlib import Path

RULES_DIR = Path('.cursor/rules')
DOCS_DIR = Path('docs')
REQUIRED_SECTIONS = [
    'Overview',
    'Guidelines',
    'Examples',
    'References',
]

SECTION_TEMPLATE = """{section}
----------------
(Add content for this section.)\n\n"""

MERMAID_HEADER = '```mermaid\ngraph TD\n'
MERMAID_FOOTER = '```\n'

RULE_LINK_RE = re.compile(r'\[([^\]]+)\]\(mdc:([^\)]+)\)')
SECTION_HEADER_RE = re.compile(r'^(#+)\s*(.+)$', re.MULTILINE)
YAML_FRONTMATTER_RE = re.compile(r'^---[\s\S]+?---', re.MULTILINE)


def ensure_docs_dir():
    if not DOCS_DIR.exists():
        DOCS_DIR.mkdir()
        print(f"Created docs/ directory.")

def get_rule_files():
    return sorted(RULES_DIR.glob('*.mdc'))

def parse_sections(content):
    headers = {m.group(2).strip(): m.start() for m in SECTION_HEADER_RE.finditer(content)}
    return headers

def add_missing_sections(content):
    # Find where to insert missing sections (after YAML frontmatter if present)
    yaml_match = YAML_FRONTMATTER_RE.match(content)
    insert_pos = yaml_match.end() if yaml_match else 0
    present_sections = set(parse_sections(content).keys())
    missing = [s for s in REQUIRED_SECTIONS if s not in present_sections]
    if not missing:
        return content, False
    to_insert = '\n'.join(SECTION_TEMPLATE.replace('{{section}}', s) for s in missing)
    new_content = content[:insert_pos] + '\n' + to_insert + content[insert_pos:]
    return new_content, True

def check_links(content, rule_file):
    broken = []
    for _, path in RULE_LINK_RE.findall(content):
        target = (RULES_DIR / Path(path)).resolve()
        if not target.exists():
            broken.append(path)
    if broken:
        print(f"{rule_file.name}: Broken links: {broken}")
    return broken

def extract_rule_relationships(rule_files):
    edges = set()
    for rule_file in rule_files:
        content = rule_file.read_text(encoding='utf-8')
        for _, path in RULE_LINK_RE.findall(content):
            target = Path(path).with_suffix('').name
            source = rule_file.stem
            edges.add((source, target))
    return edges

def generate_mermaid(edges):
    lines = [MERMAID_HEADER]
    for src, tgt in sorted(edges):
        lines.append(f'  {src} --> {tgt}')
    lines.append(MERMAID_FOOTER)
    return '\n'.join(lines)

def extract_rule_index(rule_files):
    index = []
    for rule_file in rule_files:
        content = rule_file.read_text(encoding='utf-8')
        # Try to extract YAML frontmatter description
        desc = ''
        yaml_match = YAML_FRONTMATTER_RE.match(content)
        if yaml_match:
            desc_match = re.search(r'description:\s*(.+)', yaml_match.group(0))
            if desc_match:
                desc = desc_match.group(1).strip()
        # Get first heading
        headings = list(SECTION_HEADER_RE.finditer(content))
        first_heading = headings[0].group(2).strip() if headings else rule_file.stem
        index.append((rule_file.name, first_heading, desc))
    return index

def generate_index_md(index):
    lines = ['# Rules Index\n']
    lines.append('| File | Title | Description |')
    lines.append('|------|-------|-------------|')
    for fname, title, desc in index:
        lines.append(f'| [{fname}](../.cursor/rules/{fname}) | {title} | {desc} |')
    return '\n'.join(lines)

def main():
    ensure_docs_dir()
    rule_files = get_rule_files()
    all_broken = []
    for rule_file in rule_files:
        content = rule_file.read_text(encoding='utf-8')
        # Auto-fix missing sections
        new_content, changed = add_missing_sections(content)
        if changed:
            rule_file.write_text(new_content, encoding='utf-8')
            print(f"Added missing sections to {rule_file.name}")
        # Check links
        broken = check_links(content, rule_file)
        all_broken.extend((rule_file.name, b) for b in broken)
    # Mermaid diagram
    edges = extract_rule_relationships(rule_files)
    mermaid = generate_mermaid(edges)
    (DOCS_DIR / 'rules_relationships.md').write_text(mermaid, encoding='utf-8')
    print("Generated docs/rules_relationships.md (Mermaid diagram)")
    # Rules index
    index = extract_rule_index(rule_files)
    index_md = generate_index_md(index)
    (DOCS_DIR / 'rules_index.md').write_text(index_md, encoding='utf-8')
    print("Generated docs/rules_index.md (rules summary)")
    # Summary
    if all_broken:
        print("\nBroken links detected:")
        for fname, b in all_broken:
            print(f"  {fname}: {b}")
    else:
        print("All rule links are valid.")
    print("\nRule maintenance complete.")

if __name__ == '__main__':
    main() 