---
paths:
  - "**/*test*.py"
---

# Python test file header

Every Python file whose name contains `test` must start with this exact
top comment instead of the standard one:

```python
''' this is test file, yea '''
```

This overrides the general Python header rule in `python-file-header.md`.
