#!/usr/bin/env python
"""Check for any remaining emoji characters in Python files."""

import os
import re

emoji_pattern = re.compile(r'[\U0001F300-\U0001F9FF]|[\u2600-\u27BF]|[\u2700-\u27BF]')

def check_file(filepath):
    """Check a file for emoji characters."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                if emoji_pattern.search(line):
                    return [(i, line.strip())]
    except:
        pass
    return []

# Check all Python files
root_dir = os.path.dirname(os.path.abspath(__file__))
issues = {}

for dirpath, dirnames, filenames in os.walk(root_dir):
    # Skip __pycache__ and .git
    dirnames[:] = [d for d in dirnames if d not in ['__pycache__', '.git', '__MACOSX']]
    
    for filename in filenames:
        if filename.endswith('.py'):
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, root_dir)
            
            emoji_lines = check_file(filepath)
            if emoji_lines:
                issues[rel_path] = emoji_lines

if issues:
    print("[WARNING] Found emoji characters in the following files:")
    for filepath, lines in issues.items():
        print(f"\n{filepath}:")
        for line_no, content in lines:
            print(f"  Line {line_no}: {content}")
else:
    print("[OK] No emoji characters found in Python files!")
