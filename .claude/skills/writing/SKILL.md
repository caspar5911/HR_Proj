---
name: writing
description: Write files correctly, handling all content types without corruption.
allowed-tools: Write, Read, Bash
---

# Correct File Writing

This skill ensures files are written with byte-for-byte fidelity, handling all edge cases: backslashes, Unicode, quotes, regexes, Windows paths, multiline strings, triple quotes, and mixed encodings.

## The Golden Rule

**Always use the Write tool. Never use bash to write file content.**

The Write tool uses the Claude Code SDK's native file system API, which handles JSON encoding/decoding correctly. Bash-based approaches (`echo`, heredocs, `printf`) are fragile on Windows and prone to corruption.

## Write Tool Usage

### Basic file creation

```
Write tool: create a new file at <path> with <content>
```

The Write tool takes a `file_path` (absolute path) and `content` (string). The content is passed through the Claude API as a JSON string parameter, which handles all escaping correctly.

### Overwriting existing files

```
Write tool: update file at <path> with new <content>
```

The Write tool overwrites the entire file. To modify only part of a file, use the Edit tool instead (see below).

### When to use Write vs Edit

| Situation | Tool | Why |
|---|---|---|
| New file | Write | Nothing to diff |
| Large rewrite | Write | Overwrite is simpler |
| Small change (line or two) | Edit | Preserves surrounding content exactly |
| Renaming a function everywhere | Edit (with `replace_all`) | Targeted changes |

## Critical Content Patterns

These patterns have historically caused file corruption when handled incorrectly. The Write tool handles all of them correctly, but be aware of them:

### Backslashes (literal, not escape)

```python
# Regex pattern with backslashes — these must stay as literal \
pattern = r"\d{4}-\d{2}-\d{2}"
# Windows path — backslashes must not be eaten
path = r"C:\Users\Caspar\Documents\file.txt"
# Escape sequences that should be literal text, not interpreted
template = "The newline is: \\n and tab is: \\t"
```

The Write tool preserves literal backslashes. Do NOT double-escape them or use base64.

### Unicode

```python
# Em-dash, en-dash, bullets — UTF-8 natively supported
text = "The value is — not – or •"
# CJK characters
text = "こんにちは 你好 こんにちは"
# Special symbols
text = "© ® ™ € £ ¥ § ¶ ∞ ≈ ≠ ≤ ≥"
# Box-drawing characters
border = "┌────────┐\n│ content │\n└────────┘"
```

The Write tool writes files as UTF-8. All Unicode characters pass through correctly.

### Quotes and triple quotes

```python
# Single quotes inside single-quoted strings
code = "str.replace('old', 'new')"
# Double quotes inside double-quoted strings
code = 'print("hello world")'
# Triple quotes for multiline strings
code = '''
def func():
    '''This is a docstring'''
    return True
'''
# Mixed quotes
code = """He said "don't do that" and she said 'I won't'" """
```

The Write tool's JSON encoding handles all quote types. Do NOT try to escape quotes manually.

### Regex patterns with special characters

```python
# Curly braces (could look like JSON templates)
regex = r"\d{9,15}"
# Dollar signs (could look like f-string placeholders)
regex = r"\$\d+\.\d{2}"
# Brackets and parentheses
regex = r"\[(?:[^\]]+)\]"
# Complex patterns
regex = r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"
```

All special regex characters are preserved correctly in file content.

### Multiline content

```python
# Multiline SQL
sql = """
SELECT e.name, d.department
FROM employees e
JOIN departments d ON e.dept_id = d.id
WHERE e.status = 'active'
ORDER BY e.name;
"""

# Multiline template with f-strings
template = f"""
Hello {name},
Your order #{order_id} has been processed.
Total: ${total:.2f}
"""
```

The Write tool preserves newlines, indentation, and all whitespace exactly as provided.

### Windows-specific content

```python
# Windows file paths with backslashes
import os
path = r"C:\Program Files\App\data"
paths = [r"C:\Users\Caspar\Documents", r"D:\Projects\code"]
# Windows line endings (rarely needed, but preserve if present)
# \r\n vs \n — the Write tool preserves what you give it
```

The Write tool does NOT interpret Windows paths specially. Backslashes stay backslashes.

## Verification Patterns

### After writing a critical file, verify its content

Read the file back immediately after writing to confirm correctness:

```
Read tool: read <file_path>
```

Quick checks after reading back:

1. **No content missing** — Does the file look complete?
2. **Backslashes intact** — Are there `\\` where there should be single `\`? (No double-escaping happened)
3. **Unicode preserved** — Are em-dashes, CJK, and special symbols readable?
4. **Quotes balanced** — Do single and double quotes match?
5. **Indentation preserved** — Is the code block structure intact?

### If a file contains extremely complex content

For files with especially dense combinations of all problematic patterns:

1. Write the file
2. Read it back
3. If anything looks wrong, rewrite the file with corrections

The Write tool is reliable — issues typically come from the AI model generating incorrect content, not from the tool itself.

## What NOT To Do

### Do NOT use bash to write file content

```bash
# WRONG — bash interprets backslashes, quotes, and special characters
echo 'content with \n and "quotes"' > file.py
cat <<'EOF' > file.py
content here
EOF

# WRONG — Python inline is fragile with quoting conflicts
python3 -c "open('file.py','w').write('content')"

# WRONG — base64 is a workaround, not a fix
echo 'Y29udGVudA==' | base64 -d > file.py
```

The Write tool handles all of this correctly without workarounds.

### Do NOT double-escape content

When writing content that contains backslashes:

```python
# WRONG — content = "\\n" produces \\n (two chars) instead of \n (two chars but wrong interpretation)
# The Write tool already handles the JSON escaping. Give it the content as-is.
```

Pass content to the Write tool exactly as it should appear in the file. Do not add extra escaping layers.

### Do NOT use `--dangerously-skip-permissions`

This flag bypasses permission checks and has no effect on file-writing correctness. Using it reduces security without solving any file-writing problem.

## Edit Tool for Targeted Changes

When you need to modify specific parts of an existing file, use the Edit tool:

```
Edit tool: modify <file_path>: replace <old_string> with <new_string>
```

The Edit tool does exact string matching. The `old_string` must match the file content exactly, including indentation and whitespace.

### Using Edit correctly

1. **Read the file first** — Always Read before Edit to see the exact content.
2. **Match exactly** — The `old_string` must be an exact byte-for-byte match.
3. **Use `replace_all` for repeated patterns** — Set `replace_all: true` to replace all occurrences.
4. **One change at a time** — If making multiple unrelated changes, use separate Edit calls.

### Common Edit pitfalls

| Pitfall | Fix |
|---|---|
| `old_string` doesn't match | Read the file first, copy the exact text |
| Missing whitespace difference | Check for tabs vs spaces, trailing spaces |
| Partial match fails | Make the `old_string` more specific |
| Accidentally changing something else | Use a longer, more specific `old_string` |

## Reference: Character Escaping Through Layers

Understanding why the Write tool works correctly:

```
Source code (what you want in the file):
  pattern = r"\d{4}"

What you tell the Write tool (the content parameter):
  content = 'pattern = r"\\d{4}"'
  (This is what should appear in the file)

Layer 1 — JSON encoding (handled by Claude API):
  JSON string: "pattern = r\"\\\\d{4}\""
  (JSON escapes " as \" and \ as \\)

Layer 2 — Python file write (handled by Claude Code SDK):
  Writes decoded string to file as-is

Result in file:
  pattern = r"\d{4}"
  (Correct — the content you asked for)
```

The key insight: **you only ever deal with layer 0 (what you want in the file). The JSON and file-writing layers are handled automatically and correctly by the Claude Code SDK.**

## Quick Reference Card

| Content Type | Write Tool Handles It? | Notes |
|---|---|---|
| Backslashes (`\n`, `\t`, `\d`, `\u`) | Yes | Preserved as literal characters |
| Unicode (em-dash, CJK, emoji) | Yes | Written as UTF-8 |
| Single/double quotes | Yes | No escaping needed |
| Triple quotes | Yes | Preserved exactly |
| Regex curly braces `{9,15}` | Yes | Not interpreted as JSON templates |
| F-string `$` signs | Yes | Not interpreted as variables |
| Windows paths | Yes | Backslashes preserved |
| Multiline strings | Yes | Newlines and indentation preserved |
| Mixed content | Yes | All layers handled correctly |
| cp1252 characters | Yes | Convert to UTF-8 Unicode before writing |

## Workflow Summary

1. **Determine** what content the file should contain
2. **Write** using the Write tool with the exact content
3. **Verify** by reading the file back (especially for complex files)
4. **Edit** targeted changes using the Edit tool when needed
5. **Verify** again if the edits were complex

That's it. No workarounds, no base64, no bash heredocs. The Write tool works correctly.