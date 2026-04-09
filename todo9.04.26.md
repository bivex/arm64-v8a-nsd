# TODO 2026-04-09

## Control Flow Patterns — Implementation Tracker

### Priority 1 — Quick Wins
- [x] 1. Вызвать `detect_repeat_loops()` в `extract_steps()` — RepeatWhileFlowStep теперь работает
- [x] 2. Rich conditions: `cmp x2, x0` + `b.gt` → `x2 > x0`

### Priority 2 — Core Patterns
- [x] 3. `CallFlowStep` для `bl`/`blr` — orange-accented call steps
- [x] 4. `ReturnStep` для `ret` внутри функций (guard clauses)
- [x] 5. `BreakStep` / `ContinueStep` — domain types + rendering (detection deferred)

### Priority 3 — Context Recovery
- [x] 6. `cbz`/`cbnz` → `x0 == 0` / `x0 != 0`
- [x] 7. `tbz`/`tbnz` → `x0[#3] == 0` / `x0[#3] != 0`
- [ ] 8. Tail call detection — отличать `b _func` от internal jump

### Priority 4 — Advanced
- [x] 9. Бесконечные циклы → `InfiniteLoopStep`
- [ ] 10. Conditional select (`csel`, `cset`) → inline conditional step
- [ ] 11. Jump tables / computed gotos (`adr + add + br`)
- [ ] 12. `fcmp`/`fcmpe` — FP условия в if/while

### Tour
- [x] Updated tour generator with 10 examples (sequence, if, if/else, while, repeat, switch, nested, call, early-return, infinite)
