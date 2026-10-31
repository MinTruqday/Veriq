# Requirements and Quality Workflow

Document owner: Product Quality
Version: 5.1
Status: Approved
Effective date: 2026-07-20

## 1. Requirement lifecycle

### 1.1 Drafting

A Business Analyst may create and edit a draft requirement, attach source evidence, and submit a revision for review. Editing a draft does not change a previously approved revision. The submitter and revision identifier are retained in the audit history.

### 1.2 Quality review

A Quality Assurance member checks that the requirement is testable, that acceptance criteria are unambiguous, and that cited source material supports the statements. QA may approve the submitted revision or return it with a reason. Approval applies only to the reviewed revision. A later edit creates a new draft revision and requires another review.

### 1.3 Separation of duties

One person may hold both Business Analyst and Quality Assurance memberships. The system does not require two different people when a project has a single qualified member. A user with only the Tester membership may read approved requirements but cannot approve a requirement revision.

## 2. Test case definition

### 2.1 Generation and editing

After a requirement revision is approved, an authorized user may request a proposed test case. The proposal includes a purpose, preconditions, ordered actions, test data, expected result for each action, risk, and links to the exact requirement revision and source evidence. A proposal remains a draft until QA reviews it.

### 2.2 Comparison and approval

When an existing test case is present, the review view compares the current approved version with the proposal by field and step. QA may keep the existing value, use the proposed value, or edit a combined draft. The review record preserves both inputs and the final decision. Approval publishes a new immutable test case version; it does not overwrite a version referenced by an execution.

### 2.3 Tester permissions

A Tester can execute assigned test cases and record actual results and evidence. A Tester cannot edit the approved test case definition. The Tester may submit a change suggestion linked to a case and step; QA reviews and applies any accepted change in a new version.

## 3. Execution records

Each test run freezes the selected test case version, build, environment, executor, start time, step outcomes, actual result, and evidence. Reusing a test case in a later run creates a new execution record. A prior pass or fail result is never copied as the result of the new run.

## 4. Defect linkage

A failed step may create or link a defect. The defect retains the execution, test case version, requirement revision, build, and evidence references. Closing a defect does not rewrite the historical execution outcome.
