import { docText, emptyDoc, textDoc } from "../../../lib/testing.logic.mjs";

export const TEST_LEVELS = ["critical", "high", "medium", "low"];
export const TEST_CASE_ASSESSMENT_LEVELS = ["unassessed", ...TEST_LEVELS];
export const EXPECTED_IMPACTS = ["unassessed", "low", "medium", "high", "critical"];

export function createTestCaseForm() {
  const emptyDataEntries = () => [{ id: crypto.randomUUID(), name: "", value: "" }];
  return {
    title: "",
    type: "",
    priority: "unassessed",
    risk: "unassessed",
    testLevel: "",
    testKind: "",
    expectedImpact: "unassessed",
    assessmentReason: "",
    requiredSkills: "",
    ownerId: "",
    scenarioId: "",
    requirementVersionIds: [],
    acceptanceCriterionIds: [],
    coverageItemIds: [],
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
    category: "",
    testConditionIds: [],
    requirementVersionIds: [],
    acceptanceCriterionIds: [],
    risk: "medium",
    priority: "medium",
    description: "",
    actors: "",
    preconditions: "",
    business_flow: "",
    expected_outcome: "",
    test_data_notes: "",
    test_level: "",
    test_kind: "",
    owner_id: "",
    tags: "",
  };
}

export function scenarioPayload(form) {
  return {
    ...Object.fromEntries(
      [
        "title",
        "objective",
        "category",
        "risk",
        "priority",
        "description",
        "preconditions",
        "business_flow",
        "expected_outcome",
        "test_data_notes",
        "test_kind",
      ].map((key) => [key, form[key]]),
    ),
    actors: form.actors
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    tags: form.tags
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    test_level: form.test_level || "",
    owner_id: form.owner_id || "",
    requirement_version_ids: form.requirementVersionIds,
    acceptance_criterion_ids: form.acceptanceCriterionIds,
    test_condition_ids: form.testConditionIds,
  };
}

export function scenarioFormFromRecord(item) {
  return {
    ...createScenarioForm(),
    ...item,
    actors: (item.actors || []).join("\n"),
    tags: (item.tags || []).join(", "),
    requirementVersionIds: item.requirement_version_ids || [],
    acceptanceCriterionIds: item.acceptance_criterion_ids || [],
    testConditionIds: item.test_condition_ids || [],
    test_level: item.test_level || "",
    owner_id: item.owner_id || "",
  };
}

export function createDataSetForm() {
  return {
    name: "",
    variables: {},
    secretRefs: {},
    generationSource: "USER",
    sourceRequirementVersionIds: [],
  };
}

export function buildTestCaseDraftChanges(snapshot, draft) {
  const structuredValue = (value) =>
    typeof value === "string" ? JSON.parse(value || "{}") : value || {};
  const steps = snapshot.steps?.map((step, index) => ({
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
    if (snapshot[field] !== undefined && snapshot[field] !== draft[field]) {
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
    if (snapshot[input] !== undefined && snapshot[input] !== docText(draft[field]))
      changes[field] = textDoc(snapshot[input]);
  }
  const existingStepContent = (draft.steps || []).map((step) => ({
    id: step.id,
    order: step.order,
    action: docText(step.action_doc),
    test_data: step.test_data || {},
    expected: docText(step.expected_doc),
  }));
  const changedStepContent = snapshot.steps?.map((step, index) => ({
    id: steps[index].id,
    order: index + 1,
    action: step.action,
    test_data: steps[index].test_data,
    expected: step.expected,
  }));
  if (steps && JSON.stringify(changedStepContent) !== JSON.stringify(existingStepContent)) {
    changes.steps = steps;
  }
  const otherValues = {
    test_data: snapshot.testData === undefined ? undefined : structuredValue(snapshot.testData),
    required_skills: snapshot.requiredSkills
      ?.split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    techniques: snapshot.techniques
      ?.split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    tags: snapshot.tags
      ?.split(",")
      .map((value) => value.trim())
      .filter(Boolean),
    owner_id: snapshot.ownerId?.trim(),
    automation_status: snapshot.automationStatus,
    attachments: snapshot.attachments,
    data_set_version_ids: snapshot.dataSetVersionIds,
    test_condition_ids: snapshot.testConditionIds,
    requirement_version_ids: snapshot.requirementVersionIds,
    acceptance_criterion_ids: snapshot.acceptanceCriterionIds,
    coverage_item_ids: snapshot.coverageItemIds,
    repository_node_id: snapshot.repositoryNodeId,
    bdd: snapshot.bdd,
    custom_values: snapshot.customValues,
  };
  for (const [field, value] of Object.entries(otherValues)) {
    if (value === undefined) continue;
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
