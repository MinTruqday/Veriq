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
export const TEST_CASE_ASSESSMENT_LEVELS = ["unassessed", ...TEST_LEVELS];
export const TESTING_LEVELS = ["UNIT", "INTEGRATION", "SYSTEM", "ACCEPTANCE"];
export const TEST_KINDS = [
  "functional",
  "performance",
  "security",
  "usability",
  "compatibility",
  "reliability",
  "accessibility",
];
export const EXPECTED_IMPACTS = ["unassessed", "low", "medium", "high", "critical"];

export const AI_TEST_GENERATION_CATEGORIES = ["happy_path", "negative", "boundary", "validation"];

export function createTestCaseForm() {
  const emptyDataEntries = () => [{ id: crypto.randomUUID(), name: "", value: "" }];
  return {
    title: "",
    type: "happy_path",
    priority: "unassessed",
    risk: "unassessed",
    testLevel: "",
    testKind: "",
    expectedImpact: "unassessed",
    assessmentReason: "",
    requiredSkills: "",
    ownerId: "",
    requirementVersionIds: [],
    acceptanceCriterionIds: [],
    objective: emptyDoc(),
    preconditions: emptyDoc(),
    steps: [
      {
        id: crypto.randomUUID(),
        action: emptyDoc(),
        data: emptyDataEntries(),
        expected: emptyDoc(),
      },
    ],
    testData: emptyDataEntries(),
    expectedResult: emptyDoc(),
    postconditions: emptyDoc(),
    tags: "",
    techniques: "",
    automationStatus: "manual",
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
    customValues: {},
  };
}

export function testDataEntriesToObject(entries) {
  const result = {};
  for (const entry of entries || []) {
    const name = String(entry.name || "").trim();
    const value = String(entry.value || "");
    if (!name && !value.trim()) continue;
    if (!name) throw new Error("Nhập tên cho mỗi dòng dữ liệu kiểm thử có giá trị");
    if (Object.hasOwn(result, name)) throw new Error(`Tên dữ liệu “${name}” đang bị trùng`);
    Object.defineProperty(result, name, {
      value,
      enumerable: true,
      configurable: true,
      writable: true,
    });
  }
  return result;
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
  return { name: "", variables: {}, secretRefs: {} };
}

export function selectedValues(event) {
  return Array.from(event.target.selectedOptions, (option) => option.value);
}

export function buildTestCaseDraftChanges(snapshot, draft) {
  const structuredValue = (value) =>
    typeof value === "string" ? JSON.parse(value || "{}") : value || {};
  const steps = snapshot.steps.map((step, index) => ({
    id: step.id || crypto.randomUUID(),
    order: index + 1,
    action_doc: textDoc(step.action),
    test_data: structuredValue(step.data),
    expected_doc: textDoc(step.expected),
  }));
  const changes = {};
  for (const field of [
    "title",
    "type",
    "priority",
    "risk",
    "test_level",
    "test_kind",
    "expected_impact",
    "assessment_reason",
  ]) {
    if (snapshot[field] !== draft[field]) {
      changes[field] =
        ["test_level", "test_kind"].includes(field) && !snapshot[field] ? null : snapshot[field];
    }
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
    test_data: structuredValue(snapshot.testData),
    required_skills: (snapshot.requiredSkills || "")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
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
    requirement_version_ids: snapshot.requirementVersionIds,
    acceptance_criterion_ids: snapshot.acceptanceCriterionIds,
    repository_node_id: snapshot.repositoryNodeId,
    bdd: snapshot.bdd || null,
    custom_values: snapshot.customValues || {},
  };
  for (const [field, value] of Object.entries(otherValues)) {
    let previous = draft[field];
    if (previous === undefined) {
      previous = Array.isArray(value)
        ? []
        : field === "test_data" || field === "custom_values"
          ? {}
          : field === "owner_id" || field === "bdd"
            ? ""
            : "manual";
    }
    if (field === "owner_id") previous = previous || "";
    if (field === "bdd") previous = previous || null;
    if (field === "repository_node_id" && !value) continue;
    if (JSON.stringify(value) !== JSON.stringify(previous)) changes[field] = value;
  }
  return changes;
}
