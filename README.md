# xtest

A testing framework for [Fin](https://github.com/M1778/Fin): named cases, checks
that record a failure instead of aborting the run, and a JUnit XML report that
CI can parse.

`testing::std` gives you `assert_*` helpers built on `blame`. That is the right
tool when the first failure should stop everything. xtest is for the other case:
run every check, count what passed and failed, print a summary, and exit
nonzero if anything failed.

## What it does

- Registers cases by name; each registration is distinct, including duplicates.
- Records check results and keeps running after a failure.
- Prints `FAIL [case]: message` per failing check and a final totals line.
- Writes JUnit XML with per-case `<failure>` elements.
- Returns 0/1 from `xtest_summary` and `xtest_junit` so a program can set its
  exit status.

## What it does not do

- No test discovery and no runner executable. You write `main`, call the
  functions, and exit with the summary code. `finn test` compiles and runs every
  `.fin` under `tests/`, which is enough for discovery at that level. Because
  xtest is a library, `finn build` in its own checkout has nothing to build and
  fails with "this program has no main"; that is expected.
- No parallel execution, no fixtures with setup/teardown callbacks, no mocking,
  no benchmarking. Fin has no storage for closures that lowers through imports,
  so setup and teardown are plain functions you call yourself.
- No timing. Use `time::std` if you need elapsed time.
- No skipped/error/disabled test states: a case either passes or fails.

## Verified against

`finc 1.0.0` (contract 3), from the published release, on Linux x86_64. The
tests and the example are compiled and executed at `-O0` and `-O2` by
`tests/run_tests.py`. The CI workflow pins the same version in `FINC_VERSION`
and runs the harness on Linux, macOS and Windows, on x86-64 and ARM64.

## Install

```sh
finn add M1778/xtest
```

Then import from `xtest::fin`. `finn` puts the dependency root on the library
search path, and the root `xtest.fin` forwards the namespace to `src/xtest.fin`.

This is a library, so `finn build` in the xtest checkout itself fails with
"this program has no main" — `finn build` produces an executable, and xtest has
no entry point. Build a consumer, or run the in-repo harness directly.

To use the checkout directly, add its `src` directory:

```sh
finc -I /path/to/xtest/src my_tests.fin -o my_tests
```

## Complete example

```fin
import { TestStats, xtest_new, xtest_case, xtest_check, xtest_check_eq_int,
         xtest_summary, xtest_junit, xtest_free } from xtest::fin;

#[llvm_name="exit"]
@define ex_exit(code: int) <noret>;

fun main() <noret> {
    let stats <TestStats> = xtest_new("my suite");

    xtest_case(&stats, "addition");
    xtest_check_eq_int(&stats, 1 + 1, 2, "one plus one");
    xtest_check(&stats, true, "placeholder");

    let code <int> = xtest_summary(&stats);          // prints totals, returns 0/1
    let report <int> = xtest_junit(&stats, "junit.xml");
    xtest_free(&stats);
    if (code != 0 || report != 0) { ex_exit(1); }
}
```

```output
== my suite ==
  - addition
== my suite: 2 passed, 0 failed (1 cases) ==
```

The `junit.xml` written next to it:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="my suite" tests="1" failures="0">
  <testcase name="addition"/>
</testsuite>
```

A failing check prints its own diagnostic and the program exits 1:

```fin fragment
xtest_case(&stats, "addition");
xtest_check_eq_int(&stats, 1 + 2, 2, "one plus one");
```

```output
  - addition
    FAIL [addition]: one plus one -- expected 2, got 3
== my suite: 0 passed, 1 failed (1 cases) ==
Failed cases:
  x addition
```

## API

### Lifecycle

| Function | Description |
|---|---|
| `xtest_new(suite: string) <TestStats>` | Fresh stats; prints the suite header. |
| `xtest_case(&stats, name: string)` | Start a named case; tags later failures. |
| `xtest_param(base: string, i: int) <string>` | `"base[i]"` label for parameterized cases (caller frees). |
| `xtest_free(&stats)` | Release xtest-owned memory. Idempotent. |

### Checks

All take `&TestStats`. A check never aborts the process.

| Function | Description |
|---|---|
| `xtest_check(cond, msg)` | Record a boolean condition. |
| `xtest_check_true / xtest_check_false(cond, msg)` | Explicit polarity. |
| `xtest_check_eq_int(actual, expected, msg)` | Int equality; prints both values on failure. |
| `xtest_check_ne_int(actual, unexpected, msg)` | Int inequality. |
| `xtest_check_eq_bool(actual, expected, msg)` | Bool equality. |
| `xtest_check_eq_str(actual, expected, msg)` | Null-safe string equality, by content. |
| `xtest_check_approx(actual, expected, eps, msg)` | Double comparison within `eps`. |

### Results

| Function | Description |
|---|---|
| `xtest_passes(&stats) <int>` | Check pass count. |
| `xtest_failures(&stats) <int>` | Check failure count. |
| `xtest_case_count(&stats) <int>` | Registered case count. |
| `xtest_summary(&stats) <int>` | Print totals and the failed-case list; 0 if all passed, else 1. |
| `xtest_junit(&stats, path: string) <int>` | Write JUnit XML (overwrites); 0 on success, 1 on write failure. |

`TestStats` is public so it can live on your stack. Treat its fields as
implementation state; use the accessors. Do not copy a live `TestStats`: the
copy shares ownership of every array and string.

## Ownership rules

- `xtest_new` borrows the suite string; it must outlive `xtest_free`.
- `xtest_case` clones the name. You may change or free your label immediately,
  including before the failing checks that mention it.
- Failure messages are copied, so the caller's buffer is never retained.
- `xtest_free` releases every owned string and array, then resets the counters.
  Calling it twice is safe.
- The `xtest_param` result is owned by the caller; release it with `free_str`.

## Case identity

Each `xtest_case` call is one case, even if two calls use the same name. Checks
before the first registration create one implicit `(unnamed)` case, and a later
explicit case with that same label stays separate. A case with no checks is
reported as passing. A suite with no cases has zero tests and succeeds.

`xtest_passes` and `xtest_failures` count checks. The JUnit `failures` attribute
counts failing cases. A failed case keeps all of its check diagnostics,
newline-separated, in one `<failure message="..."/>`.

## JUnit output

- The file is overwritten. Write, flush and close results are checked; any
  failure returns 1 and may leave a partial file. Counters are not changed.
- Names and diagnostics must be XML 1.0 text. C0 controls other than tab,
  newline and carriage return become `?`. Invalid UTF-8 becomes one `?` per
  offending byte, and U+FFFE/U+FFFF are rejected the same way, so a reader can
  always decode the bytes. Valid multi-byte UTF-8 is written unchanged.
- Tab, newline and carriage return are written as numeric character references,
  so attribute readback is exact.
- NUL terminates a Fin string and cannot appear in the output.
- Repeated reports produce identical files and do not change suite state.
- The report is a single `<testsuite>` with `name`, `tests` and `failures`.
  It does not carry the Ant JUnit schema's required `timestamp`, `hostname`,
  `errors` and `time` attributes, and it does not include `<properties>` or the
  `<failure>` `type` attribute. Tools that require those will reject it; tools
  that read the common subset (ElementTree, junitparser, most CI report
  viewers) accept it.

## Platform support

Linux, macOS and Windows, with the same behavior. The library calls only
standard C library functions that exist on all three (`snprintf`, `calloc`,
`free`, `fopen`, `fputs`, `fflush`, `fclose`), and Fin's `strings::std` for text.
There is no POSIX-only path, so no lane is skipped or marked unsupported.

The one platform-conditional check is the `/dev/full` flush-failure probe in
the harness, enabled only on Linux via `XTEST_LINUX_DEV_FULL=1`. Every other
check, including a report path that is a directory and one whose parent is a
regular file, runs everywhere.

Report paths are passed to `fopen` as narrow paths. UTF-8 names work on Linux
and macOS; on Windows a non-ASCII path depends on the system code page, so keep
report filenames ASCII.

## Validation

```sh
python3 tests/run_tests.py --finc /path/to/finc --fin-libs /path/to/lib/std
```

The harness uses only Python's standard library. It compiles and runs the
self-tests and the example at `-O0` and `-O2`, parses every XML report with
`ElementTree`, checks failing subprocess exit codes, and mutates one expectation
in a temporary copy to prove a wrong expectation cannot go green. Generated
files stay in a temporary directory.

`tests/test_xtest.fin` is itself a suite: the framework reports on its own
behavior, including deliberate failures whose diagnostics you will see in its
output. Those `FAIL` lines are the negative tests, not a broken run; the exit
status and the final totals are what matter.

## License

MIT. See [LICENSE](LICENSE).
