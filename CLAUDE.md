# ArellaTestProject — File Writing Instructions

## Core Rule: Use the Write Tool

**Never use bash to write file content.** Always use the Write tool (or Edit for targeted changes). The Write tool handles all escaping correctly through the Claude Code SDK's native file system API.

### Why bash is dangerous for writing files

| Problem | Example |
|---|---|
| Backslashes eaten | `\d` becomes `d` in `echo "regex: \d{4}"` |
| Quote conflicts | Python triple-quotes break bash heredocs |
| Unicode corruption | cp1252 chars may not survive bash → file |
| Special chars | `$`, `` ` ``, `!`, `{}` interpreted by bash |

### Write tool usage

1. **New file**: Use the Write tool with `file_path` and `content`
2. **Edit existing**: Use the Edit tool with exact string matching
3. **Verify**: Read back after writing complex files

### Critical content types handled correctly by the Write tool

- **Backslashes** (`\n`, `\t`, `\d`, `\uXXXX`) — preserved as literal characters
- **Unicode** (em-dashes `—`, CJK, emojis) — written as UTF-8
- **Quotes** (single, double, triple) — no escaping needed
- **Regexes** (curly braces `{9,15}`, dollar `$`) — not interpreted as JSON templates
- **Windows paths** (`C:\Users\...`) — backslashes preserved
- **Multiline strings** — newlines and indentation preserved exactly

### Edit tool for targeted changes

1. **Always Read first** — see the exact content before editing
2. **Match exactly** — `old_string` must be byte-for-byte identical including whitespace
3. **Use `replace_all`** for repeated patterns
4. **One change at a time** — separate Edit calls for unrelated changes

### See also: `.claude/skills/writing/SKILL.md`

For comprehensive patterns, templates, and reference material, see the writing skill.