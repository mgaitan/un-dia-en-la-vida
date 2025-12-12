# AGENTS

- Modern and idiomatic Python practices that emphasize clarity, strong typing, and predictable behavior:
e.g: pathlib for file operations, Pattern matching, walrus operator, enums subclasses (StrEnum, IntEnum, IntFlag)
- Dependency changes use `uv add` or `uv remove`
- Docstrings in Markdown ("myst") format, expressing intentions rather than implementation details.
  Make references to other code if appropriate. Eg: "See also `{py:func}`other_module.helper_function`.".
- Explicit and robust type annotations using built-in generics (`list`, `dict`, etc.) , union types with `|`, etc.
- Prefer flat code: use early returns, guard clauses, fixtures over context managers on tests, etc.
- Never hallucinate APIs or behaviours. If uncertain, inspect the code and/or check online documentation (ensure it's the correct version declared by uv.lock) or ask the developer
