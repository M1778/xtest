# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [0.1.0] - 2026-10-20

### Added
- Initial release: enhanced testing framework for Fin.
- `TestStats` runner state (explicit struct, no globals — Fin 0.4.0 has no
  mutable module-level state).
- Named cases (`xtest_case`), parameterized labels (`xtest_param`).
- Recording checks that never abort: `xtest_check`, `xtest_check_true/false`,
  `xtest_check_eq_int/ne_int/eq_bool/eq_str` (null-safe), `xtest_check_approx`
  (double epsilon, no float→int cast).
- `xtest_summary` returning a 0/1 exit code; `xtest_junit` writing JUnit XML
  for CI (XML-escaped names, per-case `<failure/>` markers).
- Self-tests (`tests/test_xtest.fin`): counters, param labels, failure
  accounting (failures recorded without aborting), JUnit write + readback —
  the framework dogfoods itself.
- Example (`examples/basic.fin`), GitHub Actions CI (builds finc from source,
  type-checks, runs self-tests, runs example, verifies JUnit output),
  `finn.toml`, MIT license.

### Verification
- VERIFIED 2026-10-20: compiled with finc 0.4.0 (day-1 sandbox build;
  `libllvm22` installed via apt.llvm.org for the `libLLVM.so.22.1` link).
  Self-tests pass with exit 0 (4 top-level cases; sub-suites cover counters,
  parameterized labels, failure accounting without aborting, and JUnit
  write+readback). Example runs; JUnit XML validated (suite/case names,
  failure markers, XML escaping). One real bug caught and fixed during
  verification: `xtest_case` stored the caller's label pointer, so freeing a
  `xtest_param` label before `xtest_junit` produced garbage case names —
  `xtest_case` now clones the name (API footgun removed).
