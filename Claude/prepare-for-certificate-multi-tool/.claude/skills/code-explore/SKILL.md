---
name: code-explore
description: Research a topic thoroughly through local files
context: fork
agent: Explore
allowed-tools: Read Bash Grep Glob
---
Research $ARGUMENTS thoroughly:
1. Find relevant files using Glob and Grep
2. Read and analyze the code
3. Summarize findings with specific file references