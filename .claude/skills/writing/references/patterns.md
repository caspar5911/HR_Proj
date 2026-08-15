---
name: writing-patterns
description: Concrete file-content patterns and common pitfalls.
---

# Concrete Writing Patterns

## Python File Templates

### Module with docstrings, regexes, and paths

```python
"""
Employee data processing module.

This module handles employee record transformation and validation.
Uses regex patterns for phone number and SSN formatting.
"""

import re
import os

# Regex patterns — backslashes must be preserved literally
PHONE_PATTERN = r"^(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})$"
SSN_PATTERN = r"^\d{3}-\d{2}-\d{4}$"
DATE_PATTERN = r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"

# Windows paths — backslashes are literal
CONFIG_DIR = os.path.join(r"C:\ProgramData\ArellaHR", "config")
DATA_DIR = r"D:\HRData\employees"

def validate_phone(phone: str) -> bool:
    """Check if phone number matches expected format.
    
    Accepts: 123-456-7890, (123) 456-7890, 123.456.7890
    Returns True if valid, False otherwise.
    """
    if re.match(PHONE_PATTERN, phone):
        return True
    # Common mistakes employees make:
    # 1. Forgetting area code: "456-7890"
    # 2. Using wrong separator: "456/7890"
    return False


def format_record(employee: dict) -> str:
    """Format an employee record as a display string.
    
    Uses f-strings with dollar amounts: $0.00 format.
    Contains curly braces in regex: {9,15}
    """
    name = employee["name"]  # Note: "name" uses double quotes inside the f-string
    dept = employee["department"]  # 'department' uses double quotes too
    salary = employee["salary"]
    
    # f-string with nested formatting
    output = f"""Employee: {name}
Department: {dept}
Annual Salary: ${salary:,.2f}
SSN: ***-**-{employee['ssn'][-4:]}"""  # single quotes inside the dict access
    
    # Multiline docstring test: 'This' and "that" and `backtick`
    # The pattern {9,15} means 9 to 15 repetitions
    # The $ sign is literal here, not a variable
    
    return output


def load_config() -> dict:
    """Load configuration from the Windows config directory.
    
    Path: C:\\ProgramData\\ArellaHR\\config\\settings.json
    Returns parsed JSON as a dictionary.
    """
    config_path = os.path.join(CONFIG_DIR, "settings.json")
    with open(config_path, "r", encoding="utf-8") as f:
        import json
        return json.load(f)
```

### Test file with complex strings

```python
"""Tests for employee data processing module."""

import unittest
from employee import (
    validate_phone,
    format_record,
    load_config,
    PHONE_PATTERN,
    SSN_PATTERN,
)


class TestValidatePhone(unittest.TestCase):
    def test_valid_phones(self):
        valid = [
            "123-456-7890",
            "(123) 456-7890",
            "123.456.7890",
            "1234567890",
            "+1 123-456-7890",
        ]
        for phone in valid:
            self.assertTrue(validate_phone(phone), f"Expected {phone!r} to be valid")

    def test_invalid_phones(self):
        invalid = [
            "123",           # Too short
            "123456789",      # Too short, no separator
            "abc-def-ghij",   # Letters
            "1234-567-890",   # Too many digits in area code
        ]
        for phone in invalid:
            self.assertFalse(validate_phone(phone), f"Expected {phone!r} to be invalid")


class TestFormatRecord(unittest.TestCase):
    def test_basic_format(self):
        emp = {
            "name": "John Smith",
            "department": "Engineering",
            "salary": 85000,
            "ssn": "123-45-6789",
        }
        result = format_record(emp)
        # Check that $ amounts are formatted
        self.assertIn("$85,000.00", result)
        # Check that SSN is masked
        self.assertIn("***-**-6789", result)
        # Check that department name is present
        self.assertIn("Engineering", result)

    def test_multiline_output(self):
        emp = {"name": "Jane Doe", "department": "Marketing", "salary": 62000, "ssn": "987-65-4321"}
        result = format_record(emp)
        lines = result.strip().split("\n")
        self.assertEqual(len(lines), 4)  # 4 lines of output


class TestPatterns(unittest.TestCase):
    def test_phone_regex(self):
        """The phone regex pattern contains special chars: ^, (, ), \\d, {3}, etc."""
        self.assertEqual(PHONE_PATTERN, r"^(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})$")
    
    def test_ssn_regex(self):
        self.assertEqual(SSN_PATTERN, r"^\d{3}-\d{2}-\d{4}$")
```

### Config file with mixed content

```json
{
  "application": {
    "name": "Arella HR",
    "version": "2.1.0",
    "description": "HR management system with employee tracking"
  },
  "paths": {
    "dataDir": "D:\\HRData\\employees",
    "configDir": "C:\\ProgramData\\ArellaHR\\config",
    "logsDir": "C:\\ProgramData\\ArellaHR\\logs"
  },
  "patterns": {
    "email": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
    "phone": "^\\\\(?\\\\d{3}\\\\)?[-.\\\\s]?\\\\d{3}[-.\\\\s]?\\\\d{4}$",
    "ssn": "^\\\\d{3}-\\\\d{2}-\\\\d{4}$"
  },
  "features": {
    "emailNotifications": true,
    "smsNotifications": false,
    "maxUploadSize": "50MB",
    "allowedTypes": ["pdf", "docx", "xlsx"]
  }
}
```

## JSX File Templates

### Component with event handlers and template literals

```jsx
/**
 * EmployeeSearch.jsx
 * Search component for employee directory with regex filtering.
 * Supports searching by name, email, SSN, and phone number.
 */

import React, { useState, useMemo } from "react";

// Regex patterns for validation — backslashes are literal
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const PHONE_REGEX = /^[\d\s\-\(\)\.]{10,}$/;
const SSN_REGEX = /^\d{3}-\d{2}-\d{4}$/;

// Unicode in UI labels
const LABELS = {
  searchPlaceholder: "Search employees by name, email, or department…",
  noResults: "No employees found matching your search.",
  loading: "Loading employee directory…",
  clearFilters: "Clear all filters",
};

/**
 * Search box component.
 * Handles keyboard navigation with arrow keys and Enter.
 * Uses template literals for dynamic content.
 */
export default function EmployeeSearch({ employees }) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);

  // Filter employees based on search query
  const filtered = useMemo(() => {
    if (!query) return employees;
    const lowerQuery = query.toLowerCase();
    return employees.filter((emp) => {
      return (
        emp.name.toLowerCase().includes(lowerQuery) ||
        emp.email.toLowerCase().includes(lowerQuery) ||
        emp.department.toLowerCase().includes(lowerQuery)
      );
    });
  }, [employees, query]);

  // Handle keyboard events
  const handleKeyDown = (e) => {
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActiveIndex((prev) => Math.min(prev + 1, filtered.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setActiveIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        if (activeIndex >= 0) {
          navigateToEmployee(filtered[activeIndex]);
        }
        break;
      case "Escape":
        setQuery("");
        setActiveIndex(-1);
        break;
      default:
        break;
    }
  };

  return (
    <div className="employee-search">
      <input
        type="text"
        placeholder={LABELS.searchPlaceholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyDown}
        aria-label="Search employees"
      />
      <span className="result-count">
        {filtered.length} of {employees.length} employees
      </span>
      {query && (
        <button onClick={() => setQuery("")} className="clear-btn">
          {LABELS.clearFilters}
        </button>
      )}
      <ul className="employee-list" role="listbox">
        {filtered.length === 0 ? (
          <li className="no-results">{LABELS.noResults}</li>
        ) : (
          filtered.map((emp, index) => (
            <EmployeeCard
              key={emp.id}
              employee={emp}
              isActive={index === activeIndex}
            />
          ))
        )}
      </ul>
    </div>
  );
}

/**
 * Individual employee card component.
 * Displays employee info with inline SVG icons.
 */
function EmployeeCard({ employee, isActive }) {
  // Template literal with dynamic content — includes $ for salary display
  const statusLabel = employee.active
    ? "Active"
    : "Inactive";

  return (
    <li
      className={`employee-card ${isActive ? "active" : ""}`}
      role="option"
      aria-selected={isActive}
    >
      <div className="employee-avatar">
        {employee.name.charAt(0)}
      </div>
      <div className="employee-info">
        <h3>{employee.name}</h3>
        <p>{employee.department}</p>
        <p className="employee-status">
          {statusLabel}
        </p>
      </div>
      <span className="salary">${employee.salary.toLocaleString("en-US")}</span>
    </li>
  );
}
```

## SQL File Templates

### Complex query with string literals

```sql
-- Employee directory query with Unicode support
-- Retrieves all active employees with their department info.
-- Uses em-dashes in computed column names for readability.

SELECT
    e.id,
    e.name,
    e.email,
    e.department,
    e.salary,
    e.status,
    -- Status label: 'Active' or 'Inactive' (with em-dash for status change)
    CASE
        WHEN e.status = 'active' THEN 'Active — currently employed'
        WHEN e.status = 'inactive' THEN 'Inactive — left the company'
        ELSE 'Unknown — contact HR'
    END AS status_detail,
    -- SSN masked: ***-**-{last4}
    CONCAT('***-**-', RIGHT(e.ssn, 4)) AS masked_ssn,
    -- Salary formatted: ${salary}
    CONCAT('$', FORMAT(e.salary, 2)) AS formatted_salary,
    -- Department hierarchy: Parent > Child > Grandchild
    CASE
        WHEN e.department LIKE '%—%' THEN CONCAT(LEFT(e.department, INSTR(e.department, '—') - 1), ' > ', SUBSTRING(e.department, INSTR(e.department, '—') + 1))
        ELSE e.department
    END AS department_path
FROM employees e
WHERE e.status = 'active'
    AND e.email NOT LIKE '%@test.%'  -- Exclude test accounts
    AND e.name LIKE CONCAT('%', :search_term, '%')  -- Partial match on name
ORDER BY
    e.department ASC,
    e.name ASC;
```

## Bash Command Templates

### Using Python to VERIFY files (not write them)

```bash
# CORRECT — reading and verifying, not writing
python3 -c "print(open('test.py', 'rb').read())"
python3 -c "print(len(open('test.py', 'rb').read()))"
python3 -c "
import sys
content = open(sys.argv[1], 'rb').read()
print(f'File size: {len(content)} bytes')
print(f'Has backslashes: {b\"\\\\\" in content}')
print(f'Has Unicode: {any(b > 127 for b in content)}')
" test.py

# CORRECT — writing via Python only when bash heredocs fail (rare)
python3 -c "
content = '''
def greet(name):
    return f'Hello, {name}!'
'''
with open('output.py', 'w', encoding='utf-8') as f:
    f.write(content)
"
```

### When bash heredocs work (and when they don't)

```bash
# WORKS on Git Bash — single-quoted delimiter prevents interpretation
cat <<'EOF' > test.py
import re
pattern = r"\d{4}-\d{2}-\d{2}"
path = r"C:\Users\Caspar\Documents"
# This works because 'EOF' (quoted) prevents bash from interpreting backslashes
EOF

# DOES NOT WORK — unquoted delimiter allows bash to interpret backslashes
cat <<EOF > test.py
pattern = r"\d{4}"  # \d gets eaten by bash!
EOF

# WORKS on Git Bash — but prefer the Write tool anyway
python3 <<'PYEOF'
with open("test.py", "w") as f:
    f.write('import re\npattern = r"\\d{4}"\n')
PYEOF
```

## Common Pitfall Patterns

### When the AI model generates incorrect content (not the Write tool)

Sometimes the issue is the AI model generating content with incorrect escaping, not the Write tool corrupting it. Watch for:

1. **Model generates `\\\\d` instead of `\\d`** — The model double-escaped when telling you what content to write.
   - Fix: Tell the model "the content should have single backslashes, not double."

2. **Model generates a mix of `"` and `'` inconsistently** — The model is unsure about quote handling.
   - Fix: Rewrite the content yourself in the Write tool call with correct quotes.

3. **Model generates content that looks like it has correct backslashes but actually doesn't** — Some models lose track of escaping layers.
   - Fix: After writing, always Read the file back and verify.

### Unicode in different encodings

```python
# If you have content in cp1252 or other encoding, convert to UTF-8 first:
# em-dash in UTF-8: \xe2\x80\x94 (3 bytes)
# em-dash in cp1252: \x96 (1 byte)
# Always write UTF-8. If reading cp1252 files, decode first:
content = open("file.txt", "r", encoding="cp1252").read()
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(content)
```