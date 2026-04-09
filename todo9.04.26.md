# TODO 2026-04-09

## Control Flow Patterns — Implementation Tracker

### Priority 1 — Quick Wins
- [x] 1. Repeat-While loops → `RepeatWhileFlowStep`
- [x] 2. Rich conditions → `cmp x2, x0` + `b.gt` → `x2 > x0`

### Priority 2 — Core Patterns
- [x] 3. `CallFlowStep` для `bl`/`blr`
- [x] 4. `ReturnStep` для `ret` внутри функций
- [x] 5. `BreakStep` / `ContinueStep` — domain + rendering (detection deferred)

### Priority 3 — Context Recovery
- [x] 6. `cbz`/`cbnz` → `x0 == 0` / `x0 != 0`
- [x] 7. `tbz`/`tbnz` → `x0[#3] == 0` / `x0[#3] != 0`
- [x] 8. Tail call → `TailCallStep` (b to external label)

### Priority 4 — Advanced
- [x] 9. Infinite loops → `InfiniteLoopStep`
- [x] 10. Conditional select → `InlineIfStep` (csel, cset, cinc, etc.)
- [x] 11. Indirect branch → `IndirectBranchStep` (br xN, jump tables)
- [x] 12. `fcmp`/`fcmpe` — FP conditions supported

### Tour
- [x] 13 examples: sequence, if, if/else, while, repeat, switch, nested, call, early-return, infinite, tailcall, cond-select, indirect-branch
