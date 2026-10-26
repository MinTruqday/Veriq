import assert from "node:assert/strict";
import test from "node:test";
import { buildTestCaseDraftChanges } from "./testDesign.model.js";

test("draft editor sends typed classification and source trace changes", () => {
  const snapshot = {
    title: "Login case",
    type: "happy_path",
    priority: "high",
    risk: "medium",
    test_level: "SYSTEM",
    test_kind: "security",
    expected_impact: "high",
    assessment_reason: "Credential exposure is significant",
    objective: "Check login",
    preconditions: "",
    expected: "Authenticated",
    postconditions: "",
    steps: [{ id: "s1", action: "Submit", data: "{}", expected: "Success" }],
    testData: "{}",
    requiredSkills: "security testing",
    techniques: "boundary value",
    tags: "auth",
    ownerId: "user-1",
    automationStatus: "candidate",
    attachments: [],
    dataSetVersionIds: [],
    testConditionIds: [],
    requirementVersionIds: ["reqv-2"],
    acceptanceCriterionIds: ["ac-3"],
    customValues: {},
    bdd: null,
  };
  const draft = {
    title: "Login case",
    type: "happy_path",
    priority: "high",
    risk: "medium",
    steps: [
      {
        id: "s1",
        order: 1,
        action_doc: { type: "doc", content: [] },
        test_data: {},
        expected_doc: { type: "doc", content: [] },
      },
    ],
  };

  const changes = buildTestCaseDraftChanges(snapshot, draft);

  assert.equal(changes.test_level, "SYSTEM");
  assert.equal(changes.test_kind, "security");
  assert.equal(changes.expected_impact, "high");
  assert.equal(changes.assessment_reason, "Credential exposure is significant");
  assert.deepEqual(changes.requirement_version_ids, ["reqv-2"]);
  assert.deepEqual(changes.acceptance_criterion_ids, ["ac-3"]);
  assert.deepEqual(changes.required_skills, ["security testing"]);
});

test("draft editor clears optional classification using null, not an invalid empty enum", () => {
  const snapshot = {
    title: "Login case",
    type: "happy_path",
    priority: "medium",
    risk: "medium",
    test_level: "",
    test_kind: "",
    expected_impact: "unassessed",
    assessment_reason: "",
    objective: "",
    preconditions: "",
    expected: "",
    postconditions: "",
    steps: [],
    testData: "{}",
    requiredSkills: "",
    techniques: "",
    tags: "",
    ownerId: "",
    automationStatus: "manual",
    attachments: [],
    dataSetVersionIds: [],
    testConditionIds: [],
    requirementVersionIds: [],
    acceptanceCriterionIds: [],
    customValues: {},
    bdd: null,
  };
  const draft = { ...snapshot, test_level: "SYSTEM", test_kind: "security" };

  const changes = buildTestCaseDraftChanges(snapshot, draft);

  assert.equal(changes.test_level, null);
  assert.equal(changes.test_kind, null);
});

test("draft editor persists BDD edits while preserving step identity and keyword", () => {
  const existing = {
    feature: "Authentication",
    scenario: "Valid login",
    steps: [{ id: "bdd-step-1", keyword: "Given", text: "User is signed in" }],
  };
  const snapshot = {
    title: "Valid login",
    type: "happy_path",
    priority: "medium",
    risk: "medium",
    test_level: "SYSTEM",
    test_kind: "functional",
    expected_impact: "unassessed",
    assessment_reason: "",
    objective: "",
    preconditions: "",
    expected: "",
    postconditions: "",
    steps: [],
    testData: "{}",
    requiredSkills: "",
    techniques: "",
    tags: "",
    ownerId: "",
    automationStatus: "manual",
    attachments: [],
    dataSetVersionIds: [],
    testConditionIds: [],
    requirementVersionIds: [],
    acceptanceCriterionIds: [],
    customValues: {},
    bdd: { ...existing, steps: [{ ...existing.steps[0], text: "User has an active session" }] },
  };

  const changes = buildTestCaseDraftChanges(snapshot, { ...snapshot, bdd: existing });

  assert.deepEqual(changes.bdd, snapshot.bdd);
});

test("draft editor persists a repository folder change without clearing an existing folder accidentally", () => {
  const changes = buildTestCaseDraftChanges(
    {
      title: "Foldered case",
      type: "happy_path",
      priority: "medium",
      risk: "medium",
      objective: "",
      preconditions: "",
      expected: "",
      postconditions: "",
      steps: [],
      testData: "{}",
      requiredSkills: "",
      techniques: "",
      tags: "",
      ownerId: "",
      automationStatus: "manual",
      attachments: [],
      dataSetVersionIds: [],
      testConditionIds: [],
      requirementVersionIds: [],
      acceptanceCriterionIds: [],
      repositoryNodeId: "folder-new",
      customValues: {},
      bdd: null,
    },
    {
      title: "Foldered case",
      type: "happy_path",
      priority: "medium",
      risk: "medium",
      repository_node_id: "folder-old",
      steps: [],
    },
  );

  assert.equal(changes.repository_node_id, "folder-new");

  const unchanged = buildTestCaseDraftChanges(
    { ...changes, repositoryNodeId: "" },
    { ...changes, repository_node_id: "folder-old", steps: [] },
  );
  assert.equal(Object.hasOwn(unchanged, "repository_node_id"), false);
});
