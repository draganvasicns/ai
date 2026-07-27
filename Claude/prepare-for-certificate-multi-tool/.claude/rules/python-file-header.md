---
paths:
  - "**/*.py"
---

# Python file header

Every `.py` file must start with this exact top comment:

```python
''' Build for learing/testing purpose. Build by Dragan Vasic with great help from Claude '''
```

Exception: if the filename contains `test`, use the header defined in
`python-test-file-header.md` instead — that rule takes priority over this one.
