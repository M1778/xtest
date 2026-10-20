# xtest

An enhanced testing framework for [Fin](https://github.com/M1778/Fin).

`testing::std` gives you blame-based `assert_*` helpers — one failure aborts
everything. xtest builds the runner on top: named cases, pass/fail counting
that survives failures, parameterized case labels, and JUnit XML output for
CI.

> **Verification status:** VERIFIED 2026-10-21 with finc 0.4.0 (contract 3),
> at `-O0` and `-O2`. The Fin self-tests use independent verification stats;
> an external subprocess harness checks intentional failure exits, a mutated
> expectation, JUnit structure, the example, and repeated reporting/cleanup.
> The optimized suite also passes LeakSanitizer.

## Install

Requires the `finn` package manager (https://github.com/M1778/finn):

```sh
finn add M1778/xtest
```

## Quick Example

```fin
import { TestStats, xtest_new, xtest_case, xtest_check, xtest_check_eq_int,
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
    let report_code <int> = xtest_junit(&stats, "junit.xml");
    xtest_free(&stats);
    if (code != 0 || report_code != 0) { ex_exit(1); }
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
- **Ownership:** `xtest_new` borrows your `suite` string until cleanup.
  `xtest_case` **clones** the name and points `current_case` at that owned clone;
  caller labels may be changed or freed immediately, even before failing checks.
  Failure messages are copied. `xtest_free` releases every owned string and array,
  resets counters, and is safe to repeat. Do not copy a live `TestStats` value:
  copies would share ownership. Create independent suites with `xtest_new`.
- **Case identity:** each registration is a distinct case, including duplicate
  names. Checks before the first registration create one implicit `(unnamed)`
  case; a later explicit case with that name remains distinct. Zero-check cases
  are reported as passing. An empty suite has zero cases and succeeds.
- **State layout change:** public function signatures are unchanged. The old
  `Collection`-backed `cases` and `failed_cases` fields have been replaced by owned
  `cases: [string]`, `case_failures: [int]`, and `case_messages: [string]` arrays,
  with `case_count`, `capacity`, `current_id`, and `failed_case_count` bookkeeping.
  Treat these fields as implementation state; prefer the public accessors.
  `passes`/`failures` count checks, while JUnit `failures` counts failing cases.
  Each failed testcase retains all check diagnostics, newline-separated, in its
  `<failure message="..."/>` attribute. Summaries list each failed registration once.
- **JUnit writes:** reports overwrite their destination and check write, flush,
  and close results. A failed write returns 1 and may leave a partial file; it
  does not change check counters. Names and diagnostics must be valid UTF-8 XML
  text; ASCII controls forbidden by XML 1.0 are replaced with `?`. Tab, newline,
  and carriage return are preserved with numeric entities. NUL terminates a Fin
  string and cannot be represented. Repeated reports do not modify suite state.
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

## Validation

```sh
python3 tests/run_tests.py --finc /path/to/finc --fin-libs /path/to/lib/std
```

The harness uses only Python's standard library and keeps the framework and
behavior checks in Fin. It compiles/runs self-tests and the example at `-O0` and
`-O2`, parses the actual XML externally, checks failing subprocess exit codes,
and mutates one expectation in a temporary source copy to prove verification
failures cannot go green. All generated files live in a temporary directory.
Use `--opt O2` to run one optimization level; `FIN_CC` is forwarded for optional
sanitizer linking. The `/dev/full` check requires Linux.

## Dependencies

None beyond the Fin standard library (`strings`) and libc (`snprintf`, `calloc`,
`free`, `fopen`, `fputs`, `fflush`, `fclose` — local ABI declarations, no extra link
flags needed). Python is needed only for the external validation harness.
Zero third-party packages.

## License

MIT
