# xtest

An enhanced testing framework for [Fin](https://github.com/M1778/Fin).

`testing::std` gives you blame-based `assert_*` helpers — one failure aborts
everything. xtest builds the runner on top: named cases, pass/fail counting
that survives failures, parameterized case labels, and JUnit XML output for
CI.

> **Verification status:** VERIFIED 2026-10-20 against finc 0.4.0 (built from
> source 2026-10-19; `libllvm22` installed via apt.llvm.org to satisfy the
> `libLLVM.so.22.1` link). Self-tests pass (exit 0), example runs, JUnit XML
> validated. Written against the Fin v0.4.0
> [agent guide](https://github.com/M1778/Fin/blob/master/docs/agent-guide.md)
> and the 8 measured finc backend limits documented in the repo.

## Install

Requires the `finn` package manager (https://github.com/M1778/finn):

```sh
finn add M1778/xtest
```

## Quick Example

```fin
import { TestStats, xtest_new, xtest_case, xtest_check_eq_int,
         xtest_summary, xtest_junit, xtest_free } from xtest::fin;

#[llvm_name="exit"]
@define ex_exit(code: int) <noret>;

fun main() <noret> {
    let stats <TestStats> = xtest_new("my suite");

    xtest_case(&stats, "addition");
    xtest_check_eq_int(&stats, 1 + 1, 2, "one plus one");

    xtest_case(&stats, "strings");
    xtest_check(&stats, true, "placeholder");

    let code <int> = xtest_summary(&stats);   // prints totals, returns 0/1
    xtest_junit(&stats, "junit.xml");         // CI report
    xtest_free(&stats);
    if (code != 0) { ex_exit(1); }
}
```

> Import spelling: `xtest::fin` means module `xtest` (the file
> `src/xtest.fin`), namespace `fin`. Import the names you need **by name** —
> qualified calls (`xtest.xtest_check(...)`) are refused by the backend; see
> `docs/guide/10-modules-and-imports.md` in the Fin repo.

## Design notes

- **No globals.** Fin 0.4.0 has no mutable module-level state, so runner
  state lives in an explicit `TestStats` struct you own and pass by `&` to
  every check. This gives per-suite isolation (and nested suites) for free.
- **Checks record, never abort.** A failing check prints `FAIL [case]: msg`
  and increments the failure counter; the suite keeps running. Use
  `testing::std`'s `assert_*` when you want abort-on-failure semantics.
- **Ownership:** `xtest_new` keeps (never frees) your `suite` string —
  string literals are the normal choice. `xtest_case` **clones** the name,
  so `xtest_param` labels can be freed with `strings::std.free_str`
  immediately after the case's checks. `xtest_free` releases all
  xtest-owned memory (cloned case names).
- **Fixtures:** Fin 0.4.0 has no closures/fn-pointer storage that lowers
  through imports, so setup/teardown is plain functions you call yourself:

```fin
fun db_setup() <string> { return "/tmp/test.db"; }
fun db_teardown(path: string) <noret> { /* ... */ }

xtest_case(&stats, "db round-trip");
let db <string> = db_setup();
xtest_check(&stats, db_write(db, "k", "v"), "write ok");
db_teardown(db);
```

- **Timing:** wrap a case with `time::std.now()` / `diff_sec` for elapsed
  seconds; xtest deliberately stays out of the clock business.

## API Reference

### Lifecycle

| Function | Description |
|---|---|
| `xtest_new(suite: string) <TestStats>` | Fresh stats; prints the suite header. |
| `xtest_case(&stats, name: string)` | Start a named case; tags later failures. |
| `xtest_param(base: string, i: int) <string>` | `"base[i]"` label for parameterized cases (caller frees). |
| `xtest_free(&stats)` | Release xtest-owned memory. |

### Checks (all take `&TestStats` first)

| Function | Description |
|---|---|
| `xtest_check(cond, msg)` | Record a boolean condition. |
| `xtest_check_true / xtest_check_false(cond, msg)` | Explicit polarity. |
| `xtest_check_eq_int(actual, expected, msg)` | Int equality; prints both values on failure. |
| `xtest_check_ne_int(actual, unexpected, msg)` | Int inequality. |
| `xtest_check_eq_bool(actual, expected, msg)` | Bool equality. |
| `xtest_check_eq_str(actual, expected, msg)` | Null-safe string equality; prints both on failure. |
| `xtest_check_approx(actual, expected, eps, msg)` | Double comparison within `eps` (stays in doubles — `cast<int>(double)` is not lowered). |

### Results

| Function | Description |
|---|---|
| `xtest_passes(&stats) <int>` | Pass count. |
| `xtest_failures(&stats) <int>` | Failure count. |
| `xtest_case_count(&stats) <int>` | Registered case count. |
| `xtest_summary(&stats) <int>` | Print totals + failed-case list; returns 0 if all passed, 1 otherwise. |
| `xtest_junit(&stats, path: string) <int>` | Write JUnit XML (overwrites); 0 on success, 1 on write failure. |

## Dependencies

None beyond the Fin standard library (`collection`, `strings`, `fs`) and
libc (`snprintf`, `calloc`, `free` — vendored `@define`s, no link flags
needed). Zero third-party packages.

## License

MIT
