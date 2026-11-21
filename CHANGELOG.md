# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Fixed

- JUnit attribute values are valid XML 1.0. Invalid UTF-8 (a stray 0xFF, a lone
  continuation byte, an overlong `C0` sequence, a UTF-16 surrogate half) and the
  BMP noncharacters U+FFFE/U+FFFF previously reached the file unchanged, so no
  XML parser could read the report and CI reported a parse error instead of the
  test result. One `?` replaces each offending byte; valid multi-byte characters
  are written unchanged.
- A null suite name, case label, or diagnostic no longer crashes the process.
  `printf` dereferenced it, which aborted the run and lost the remaining checks
  and the exit status. Null text is now read as empty text, matching what
  `xtest_check_eq_str` already documented.
- The package is importable as `xtest::fin` after `finn add`. `finc` resolves a
  package import to `<package-root>/xtest.fin`, which did not exist, so every
  consumer failed with `module not found: xtest`. A root `xtest.fin` now
  forwards the namespace to `src/xtest.fin`.
- `exports.fin` contains no `export * from ...` line. That is not Fin syntax and
  did not parse; finn detects the file by presence and never reads it.

### Changed

- CI installs `finc` from the published release (pinned in `FINC_VERSION`,
  SHA-256 verified against the release index) instead of building the compiler
  from source, and runs the harness on Linux, macOS and Windows, each on x86-64
  and ARM64. Every lane compiles and executes the self-tests and the example at
  `-O0` and `-O2`. The Linux x86-64 lane also proves `finn add` + `finn build` +
  run in a separate consumer project.
- Every source file carries the project header with an SPDX MIT line. The
  header script is committed at `scripts/fin_header.py`.
- The README states the verified compiler version (`finc 1.0.0`, contract 3),
  the supported platforms, the full public API, the ownership rules, the exact
  example output, and the parts of the Ant JUnit schema this report omits.

### Added

- Regression coverage for XML text validity: invalid UTF-8, U+FFFE/U+FFFF, C0
  controls, and a valid multi-byte character that must survive.
- Regression coverage for null suite, case, and message inputs.
- A `nulls.xml` report parsed by the external harness.
- `finn.toml` declares the test script the harness expects; `.gitignore` covers
  build products and generated reports.

### Removed

- The README's verification block, which cited a run in another repository and
  `finc 0.4.0`, and its unresolved badge.

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
