import { docText, emptyDoc, textDoc } from "../../../lib/testing.logic.mjs";

export const TEST_CASE_TYPES = [
  "happy_path",
  "negative",
  "boundary",
  "validation",
  "permission",
  "state_transition",
  "integration",
  "error_handling",
  "data_persistence",
  "concurrency",
  "api",
  "ui",
  "custom",
];

export const TEST_SCENARIO_CATEGORIES = TEST_CASE_TYPES.filter(
  (value) => !["api", "ui", "custom"].includes(value),
);

export const TEST_LEVELS = ["critical", "high", "medium", "low"];

export const AI_TEST_GENERATION_CATEGORIES = ["happy_path", "negative", "boundary", "validation"];

export function createTestCaseForm() {
  return {
    title: "",
    type: "happy_path",
    priority: "medium",
    risk: "medium",
    action: emptyDoc(),
    expected: emptyDoc(),
    dataSetVersionIds: [],
    testConditionIds: [],
    repositoryNodeId: "",
    reusableStepVersionIds: [],
    testStyle: "MANUAL",
    feature: "",
    scenario: "",
    given: "",
    when: "",
    then: "",
  };
}

export function createScenarioForm() {
  return {
    title: "",
    objective: "",
    category: "happy_path",
    testConditionIds: [],
  };
}

export function createDataSetForm() {
  return { name: "", variables: "{}", secretRefs: "{}" };
}

export function selectedValues(event) {
  return Array.from(event.target.selectedOptions, (option) => option.value);
}

export function buildTestCaseDraftChanges(snapshot, draft) {
  const steps = snapshot.steps.map((step, index) => ({
    id: step.id || crypto.randomUUID(),
    order: index + 1,
    action_doc: textDoc(step.action),
    test_data: JSON.parse(step.data || "{}"),
    expected_doc: textDoc(step.expected),
  }));
  const changes = {};
  for (const field of ["title", "type", "priority", "risk"]) {
    if (snapshot[field] !== draft[field]) changes[field] = snapshot[field];
  }
  for (const [field, input] of [
    ["objective_doc", "objective"],
    ["preconditions_doc", "preconditions"],
    ["expected_result_doc", "expected"],
    ["postconditions_doc", "postconditions"],
  ]) {
    if (snapshot[input] !== docText(draft[field])) changes[field] = textDoc(snapshot[input]);
  }
  const existingStepContent = (draft.steps || []).map((step) => ({
    id: step.id,
    order: step.order,
    action: docText(step.action_doc),
    test_data: step.test_data || {},
    expected: docText(step.expected_doc),
  }));
  const changedStepContent = snapshot.steps.map((step, index) => ({
    id: steps[index].id,
    order: index + 1,
    action: step.action,
    test_data: steps[index].test_data,
    expected: step.expected,
  }));
  if (JSON.stringify(changedStepContent) !== JSON.stringify(existingStepContent)) {
    changes.steps = steps;
  }
  const otherValues = {
    test_data: JSON.parse(snapshot.testData || "{}"),
    techniques: snapshot.techniques
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    tags: snapshot.tags
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    owner_id: snapshot.ownerId.trim(),
    automation_status: snapshot.automationStatus,
    attachments: snapshot.attachments,
    data_set_version_ids: snapshot.dataSetVersionIds,
    test_condition_ids: snapshot.testConditionIds,
  };
  for (const [field, value] of Object.entries(otherValues)) {
    let previous = draft[field];
    if (previous === undefined) {
      previous = Array.isArray(value)
        ? []
        : field === "test_data"
          ? {}
          : field === "owner_id"
            ? ""
            : "manual";
    }
    if (field === "owner_id") previous = previous || "";
    if (JSON.stringify(value) !== JSON.stringify(previous)) changes[field] = value;
  }
  return changes;
}
