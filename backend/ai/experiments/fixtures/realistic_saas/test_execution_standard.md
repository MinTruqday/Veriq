# Test Execution and Evidence Standard

Document owner: Quality Engineering
Version: 4.0
Status: Approved
Effective date: 2026-08-01

## 1. Test run setup

Before a run starts, QA selects the approved test case version, target build, environment, and execution scope. The run stores these selections as a snapshot. Changing the current test case later does not change the version already selected by an active or completed run.

## 2. Tester actions

An assigned Tester may start and complete an execution, record an actual result for each step, attach evidence, and report a defect. A Tester may add a comment proposing a correction to a test case, but cannot alter the approved title, preconditions, test data, steps, or expected results. QA reviews a proposed correction and publishes it as a new version if accepted.

## 3. Result states

Each step is recorded as Passed, Failed, Blocked, or Not Run. The overall result is Failed when at least one required step fails, Blocked when no required step fails but at least one is blocked, and Passed only when every required step passes. A run with an unexecuted required step cannot be marked Passed.

## 4. Evidence and defects

Evidence includes the test run identifier, selected case version, build, environment, step identifier, uploader, and capture time. A defect linked from a failed step retains these references. Correcting or closing a defect does not modify the original step result; a new execution records the retest outcome.

## 5. Reuse across releases

The same approved test case may be included in multiple test runs. Each run receives a separate execution record and fresh result. The previous execution outcome, evidence, and executor are never copied into a new run.
