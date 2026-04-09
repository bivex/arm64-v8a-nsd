# TODO - Issues found from HelloSilicon testing

## ✅ Completed

### 1. `_start:` label not recognized as function ✅ FIXED
- **Fix:** Added `svc` as function terminator in `_find_function_end()`

### 2. Darwin/macOS system call patterns ✅ FIXED
- **Fix:** Added `SystemCallStep` domain type with pink/red styling

### 3. ARM64 macro support ✅ FIXED
- **Added:** `MacroExpander` class in `macro_expander.py`
- **Features:**
  - `.macro name param1, param2, ...` / `.endm` definitions
  - `.include "filename"` directive processing
  - Parameter substitution with `\paramname`
  - Inline macro expansion
- **Integration:** Wired into `Arm64AsmControlFlowExtractor` before tokenization

## Priority Issues

(All resolved)

## Priority Issues

### 1. `_start:` label not recognized as function ✅ FIXED
- **File:** Chapter 03/HelloWorld.s, Chapter 04/case.s, etc.
- **Issue:** `_start:` is treated as `<module>` instead of a function
- **Expected:** Should be recognized as a valid function entry point
- **Location:** `control_flow_extractor.py` - function extraction logic
- **Fix:** Added `svc` as a function terminator in `_find_function_end()`

### 2. Darwin/macOS system call patterns ✅ FIXED
- **Pattern:** `SVC #0x80` - Darwin kernel system call
- **Issue:** Not specifically handled (falls through to ActionFlowStep)
- **Fix:** Added `SystemCallStep` domain type with pink/red styling and "syscall" badge

## Nice to Have

### 3. Better function name detection
- Current: `[a-zA-Z_][a-zA-Z0-9_]*:` pattern
- Issue: Some common patterns missed:
  - `_start:` (entry point)
  - Local labels like `Lfoo:` (GCC internal)
  - Double-underscore labels `__foo:`

### 4. `.equ` directive support
- **Pattern:** `.equ N, 3` - constant definitions
- **Current:** Treated as generic ActionFlowStep
- **Better:** Could be extracted and used in expressions

### 5. `ADRP` + `ADD` pattern for PC-relative addresses
- **Pattern:**
  ```
  ADRP X1, mesg@PAGE
  ADD  X1, X1, mesg@PAGEOFF
  ```
- **Issue:** Two separate ActionFlowSteps
- **Better:** Could be grouped as "Load address" pattern

### 6. Nested loop depth visualization
- **Current:** Nested loops shown as separate blocks
- **Consider:** Add depth indicators/badges for loops (similar to if-depth)

## Files Affected

- `src/arm64nsd/infrastructure/arm64/control_flow_extractor.py` - function extraction
- `src/arm64nsd/domain/control_flow.py` - maybe add SystemCallStep
- `src/arm64nsd/infrastructure/rendering/nassi_html_renderer.py` - rendering
