#!/usr/bin/env python3
# =============================================================================
# Fin Programming Language
#
# Made with ❤️ for someone special.
#
# This project is genuinely built on love and dedication, a way to express your love can be done through Fin.
# Fin is a semi-object-orientated programming language that specialized in control, giving so much control to the user while asking for the bare minimum.
# Fin is the name of the Angel from BlackNightmare-Stories not yet published.
# “Love is the reason this project exists”
# -----------------------------------------------------------------------------
# Author: M1778
# Repository: https://github.com/M1778/xtest
# Profile: https://github.com/M1778M/
# -----------------------------------------------------------------------------
# Copyright (C) 2027 M1778
#
# This file is part of xtest, a project for the Fin Programming Language.
#
# Licensed under the MIT License. See LICENSE in the repository root.
#
# SPDX-License-Identifier: MIT
# =============================================================================

"""Run the Fin framework tests, negative children, mutation, and XML assertions."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EXE_SUFFIX = ".exe" if os.name == "nt" else ""
CHECKS = 0


def check(condition, message):
    global CHECKS
    CHECKS += 1
    if not condition:
        raise AssertionError(message)


def run(command, cwd, expected=0, env=None):
    # Fin literals/output are UTF-8, independently of the Windows console locale.
    # Compiler diagnostics may use a native encoding; retain replacement characters
    # rather than masking the actual subprocess exit status with a decode error.
    result = subprocess.run(command, cwd=cwd, env=env, text=True,
                            encoding="utf-8", errors="replace",
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=120)
    check(result.returncode == expected,
          f"{command} returned {result.returncode}, expected {expected}\n"
          f"{result.stdout}\n{result.stderr}")
    check("LeakSanitizer" not in result.stderr and "AddressSanitizer" not in result.stderr,
          result.stderr)
    return result


def report(folder, name, tests, failures):
    root = ET.parse(folder / name).getroot()
    check(root.tag == "testsuite", name)
    check(int(root.attrib["tests"]) == tests, f"{name}: case total")
    check(int(root.attrib["failures"]) == failures, f"{name}: failure total")
    cases = root.findall("testcase")
    check(len(cases) == tests, f"{name}: testcase elements")
    check(sum(case.find("failure") is not None for case in cases) == failures,
          f"{name}: failed-case total must match elements")
    return root, cases


def validate_xml(folder):
    root, cases = report(folder, "junit.xml", 3, 1)
    check(root.attrib["name"] == 'junit & <report> "quoted"', "suite escapes")
    check([case.attrib["name"] for case in cases] ==
          ["duplicate", "duplicate", "empty case"], "registration order")
    check(cases[0].find("failure") is None, "passing duplicate must stay passing")
    message = cases[1].find("failure").attrib["message"]
    check(message.startswith('first & <failure> "quoted"\n'), "owned first message")
    check("second failure -- expected 2, got 1" in message, "second diagnostic")
    check(message.endswith("-- expected 4, got 3"), "long diagnostic untruncated")
    check(len(message.splitlines()) == 3, "all three check failures retained")
    for filename in ("junit-repeat.xml", "junit-after-error.xml"):
        report(folder, filename, 3, 1)
        check((folder / filename).read_bytes() == (folder / "junit.xml").read_bytes(),
              "repeated/error-recovery report must be identical")
    _, cases = report(folder, "params.xml", 12, 1)
    check([case.attrib["name"] for case in cases] == [f"case[{i}]" for i in range(12)],
          "owned parameter labels survive growth and freed caller memory")
    check(cases[7].find("failure") is not None, "correct parameter failed")
    _, cases = report(folder, "failures.xml", 1, 1)
    messages = cases[0].find("failure").attrib["message"].splitlines()
    check(len(messages) == 8, "all failing wrappers retained")
    for prefix, message in zip(("boolean failure", "true failure", "false failure",
                                "integer failure", "inequality failure",
                                "bool equality failure", "string failure", "approx failure"),
                               messages):
        check(message.startswith(prefix), f"missing wrapper diagnostic: {prefix}")
    _, cases = report(folder, "implicit.xml", 2, 1)
    check([case.attrib["name"] for case in cases] == ["(unnamed)", "(unnamed)"],
          "implicit and explicit labels")
    check(cases[0].find("failure") is not None and cases[1].find("failure") is None,
          "implicit case identity")
    report(folder, "empty.xml", 0, 0)
    _, cases = report(folder, "nulls.xml", 1, 1)
    check(cases[0].attrib["name"] == "" and cases[0].find("failure").attrib["message"] == "",
          "null text becomes empty text, not a crash")
    _, cases = report(folder, "controls.xml", 4, 4)
    expected = '?\t\n\r &<>"\' café'
    check(cases[0].attrib["name"] == expected, "control/whitespace/UTF-8 label")
    check(cases[0].find("failure").attrib["message"] == expected,
          "control/whitespace/UTF-8 diagnostic")
    controls = "".join(chr(i) if i in (9, 10, 13) else "?" for i in range(1, 32))
    check(cases[1].attrib["name"] == controls, "every XML 1.0 C0 control sanitized")
    check(cases[1].find("failure").attrib["message"] == controls,
          "every message control sanitized")
    check(cases[2].attrib["name"] == "" and cases[2].find("failure").attrib["message"] == "",
          "empty case and diagnostic retained")
    # Invalid UTF-8 and XML noncharacters must not reach the file: one '?' per
    # offending byte for the broken sequences, '€' surviving intact. A report a
    # CI consumer cannot decode is not a report.
    broken = "?" * 13 + "\u20ac"
    check(cases[3].attrib["name"] == broken, "invalid UTF-8 sanitized, valid UTF-8 kept")
    check(cases[3].find("failure").attrib["message"] == broken,
          "invalid message UTF-8 sanitized")
    report(folder, "lifecycle.xml", 9, 9)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # The CI installer unpacks into ./.finc; prefer it over PATH so a local run
    # after `python3 .github/scripts/install_finc.py` needs no arguments.
    installed_compiler = ROOT / ".finc/bin" / f"finc{EXE_SUFFIX}"
    installed_libraries = ROOT / ".finc/lib/std"
    parser.add_argument("--finc", default=os.environ.get(
        "FINC", str(installed_compiler) if installed_compiler.is_file() else "finc"))
    parser.add_argument("--fin-libs", default=os.environ.get(
        "FIN_LIBS", str(installed_libraries) if installed_libraries.is_dir() else None))
    parser.add_argument("--opt", action="append", choices=("O0", "O2"))
    args = parser.parse_args()
    source = ROOT / "tests/test_xtest.fin"
    base = [args.finc, "-I", str(ROOT / "src")]
    if args.fin_libs is not None:
        base += ["--fin-libs", args.fin_libs]
    # Generated sources/reports live in an isolated directory; the repo stays clean.
    with tempfile.TemporaryDirectory(prefix="xtest-") as temp:
        for opt in args.opt or ("O0", "O2"):
            folder = Path(temp) / opt
            folder.mkdir()
            env = dict(os.environ)
            env.pop("XTEST_FAIL_CHILD", None)
            env.pop("XTEST_LINUX_DEV_FULL", None)
            linux_full = sys.platform.startswith("linux")
            if linux_full:
                env["XTEST_LINUX_DEV_FULL"] = "1"
            binary = folder / f"selftest{EXE_SUFFIX}"
            run(base + [f"-{opt}", str(source), "-o", str(binary)], folder, env=env)
            result = run([str(binary)], folder, env=env)
            summary = next(line for line in result.stdout.splitlines()
                           if line.startswith("== xtest self-tests:"))
            expected_passes = 56 if linux_full else 55
            check(f"{expected_passes} passed, 0 failed (7 cases)" in summary, summary)
            validate_xml(folder)
            if linux_full:
                # Also exercise the Windows/macOS path locally without the device probe.
                portable_env = dict(env)
                portable_env.pop("XTEST_LINUX_DEV_FULL")
                portable = run([str(binary)], folder, env=portable_env)
                check("55 passed, 0 failed (7 cases)" in portable.stdout,
                      "portable failure checks must pass without /dev/full")
            child_env = dict(env, XTEST_FAIL_CHILD="1")
            child = run([str(binary)], folder, expected=1, env=child_env)
            check("CHILD CONTINUED" in child.stdout, "failed check must not abort")
            check("1 passed, 1 failed (1 cases)" in child.stdout, "child accounting")

            # Mutate only a temporary source copy: a wrong verification expectation
            # must propagate to the process exit status, not just print FAIL.
            old = 'xtest_check_eq_int(verify, xtest_passes(&s), 9, "nine passes recorded");'
            new = 'xtest_check_eq_int(verify, xtest_passes(&s), 900, "nine passes recorded");'
            text = source.read_text(encoding="utf-8")
            check(text.count(old) == 1, "mutation target is unique")
            mutated = folder / "mutated.fin"
            mutated.write_text(text.replace(old, new), encoding="utf-8")
            mutation_binary = folder / f"mutated{EXE_SUFFIX}"
            run(base + [f"-{opt}", str(mutated), "-o", str(mutation_binary)], folder, env=env)
            result = run([str(mutation_binary)], folder, expected=1, env=env)
            check("nine passes recorded -- expected 900, got 9" in result.stdout,
                  "wrong expectation must fail")
            check("SELF-TESTS FAILED" in result.stdout and "SELF-TESTS PASSED" not in result.stdout,
                  "mutation must not report success")

            example = folder / f"example{EXE_SUFFIX}"
            run(base + [f"-{opt}", str(ROOT / "examples/basic.fin"), "-o", str(example)],
                folder, env=env)
            run([str(example)], folder, env=env)
            report(folder, "junit-example.xml", 5, 0)
            (folder / "junit-example.xml").unlink()
            (folder / "junit-example.xml").mkdir()
            run([str(example)], folder, expected=1, env=env)
            print(f"{opt}: {summary}; negative child, mutation, and example write error exit 1; "
                  "10 XML reports verified")
    print(f"PASS: {CHECKS} external checks")


if __name__ == "__main__":
    main()
