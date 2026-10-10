import json
import sys
import pytest

_outcomes = {}
_failure_messages = {}


def pytest_configure(config):
    reporter = config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        config.pluginmanager.unregister(reporter)


def pytest_sessionstart(session):
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is not None:
        session.config.pluginmanager.unregister(reporter)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    outcome = yield
    exception = outcome.excinfo
    if exception is not None:
        _failure_messages[item.nodeid] = str(exception[1]) or exception[0].__name__


def pytest_runtest_logreport(report):
    if report.when != "call":
        return
    name = report.nodeid.rsplit("::", 1)[-1].split("[", 1)[0]
    elapsed = max(1, round(report.duration * 1000))
    result = {"Status": "passed" if report.passed else "failed", "Execution time": f"{elapsed}ms"}
    if report.failed:
        test_id = report.nodeid
        longrepr = getattr(report, "longrepr", None)
        crash = getattr(longrepr, "reprcrash", None)
        detail = getattr(crash, "message", "Test failed")
        if detail.startswith("AssertionError:"):
            detail = detail.split("AssertionError:", 1)[1].strip()
        if detail == "AssertionError":
            traceback = getattr(longrepr, "reprtraceback", None)
            for entry in getattr(traceback, "reprentries", []):
                location = getattr(entry, "reprfileloc", None)
                message = getattr(location, "message", "")
                if "AssertionError:" in message:
                    detail = message.split("AssertionError:", 1)[1].strip()
                    break
        long_text = getattr(report, "longreprtext", "") or str(getattr(report, "longrepr", ""))
        for line in long_text.splitlines():
            marker = "AssertionError:"
            if detail == "Test failed" and marker in line:
                detail = line.split(marker, 1)[1].strip()
                break
        detail = _failure_messages.get(test_id, detail)
        result["Error"] = detail[:160]
    _outcomes[name] = (result, elapsed)


def pytest_sessionfinish(session, exitstatus):
    passed = sum(result["Status"] == "passed" for result, _ in _outcomes.values())
    failed = sum(result["Status"] == "failed" for result, _ in _outcomes.values())
    total_time = sum(elapsed for _, elapsed in _outcomes.values())
    telemetry = {name: result for name, (result, _) in _outcomes.items()}
    telemetry.update({
        "Passed": passed,
        "Failed": failed,
        "Total bugs": 6,
        "Total Execution time": f"{total_time}ms",
    })
    sys.__stdout__.write(json.dumps(telemetry, separators=(",", ":")) + "\n")
