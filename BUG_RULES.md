# Visual Bug Hunter Rules

## Core Workflow (Must Follow)

1. **Screenshot Confirmation**: Always capture a screenshot BEFORE any fix to establish baseline.
2. **Locate Code**: Use visual analysis + static code scanning to find the exact file and line.
3. **Minimal Diff Fix**: Apply the smallest possible change. Never rewrite entire files.
4. **Screenshot Verification**: Capture a screenshot AFTER the fix to prove it worked.

## Anti-Patterns (Never Do)

- ❌ Claiming "fixed" without visual evidence (screenshot).
- ❌ Rewriting large portions of UI code when a one-line change suffices.
- ❌ Ignoring disabled widgets (`setEnabled(False)`, `state=DISABLED`).
- ❌ Ignoring duplicate renders (calling `.pack()` or `.grid()` twice on the same widget).

## Specialized Checks

### 1. Disabled Widgets
Scan for:
- `setEnabled(False)` / `setEnabled(0)`
- `state="disabled"` / `state=DISABLED`
- `.disabled = True`
- `userInteractionEnabled = false`

### 2. Duplicate Renders
Scan for:
- Same widget calling `.pack()`, `.grid()`, or `.place()` multiple times.
- Multiple `add_widget()` calls for the same component.

## Token Saving Principles

1. **Load Only Relevant Files**: Don't read the whole project. Search by keywords from the bug description.
2. **Output Minimal Diffs**: Show only the changed lines, not the full file.
3. **One Bug at a Time**: Fix and verify one issue before moving to the next.
