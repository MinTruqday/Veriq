import { docText, emptyDoc, textDoc } from "../../../lib/testing.logic.mjs";

export const UNASSESSED_VALUE = "unassessed";

export function createTestCaseForm() {
  const emptyDataEntries = () => [{ id: crypto.randomUUID(), name: "", value: "" }];
  return {
    title: "",
    moduleName: "",
    type: "",
    priority: "",
    durationMinutes: "",
    testLevel: "",
    testKind: "",
    ownerId: "",
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
    postconditions: emptyDoc(),
    mainFlow: emptyDoc(),
    alternateFlows: emptyDoc(),
    exceptionFlows: emptyDoc(),
    tags: "",
    techniques: "",
    automationStatus: "manual",
    testConditionIds: [],
    testStyle: "MANUAL",
    feature: "",
    scenario: "",
    given: "",
    when: "",
    then: "",
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

export function normalizeTestCaseVersionForDisplay(version) {
  if (!version || typeof version !== "object") return version;
  const steps = (version.steps || []).map((step) => ({ ...step }));
  if (!version.bdd && steps.length) {
    const legacyData = version.test_data || {};
    const legacyExpected = version.expected_result_doc;
    if (
      Object.keys(legacyData).length &&
      !steps.some((step) => Object.keys(step.test_data || {}).length)
    ) {
      steps[0].test_data = legacyData;
    }
    if (legacyExpected && !steps.some((step) => docText(step.expected_doc).trim())) {
      steps[0].expected_doc = legacyExpected;
    }
  }
  return { ...version, steps };
}

export function buildTestCaseDraftChanges(snapshot, draft) {
  const structuredValue = (value) =>
    typeof value === "string" ? JSON.parse(value || "{}") : value || {};
  const steps = snapshot.steps?.map((step, index) => {
    const previous = (draft.steps || []).find((item) => item.id === step.id);
    return {
      id: step.id || crypto.randomUUID(),
      order: index + 1,
      action_doc:
        previous && docText(previous.action_doc) === step.action
          ? previous.action_doc
          : textDoc(step.action),
      test_data: structuredValue(step.data),
      expected_doc:
        previous && docText(previous.expected_doc) === step.expected
          ? previous.expected_doc
          : textDoc(step.expected),
    };
  });
  const changes = {};
  if (
    snapshot.durationMinutes !== undefined &&
    Number(snapshot.durationMinutes || 0) !== Number(draft.duration_minutes || 0)
  ) {
    changes.duration_minutes = snapshot.durationMinutes ? Number(snapshot.durationMinutes) : null;
  }
  for (const field of [
    "title",
    "type",
    "priority",
    "risk",
    "test_level",
    "test_kind",
    "module_name",
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
    ["main_flow_doc", "mainFlow"],
    ["alternate_flows_doc", "alternateFlows"],
    ["exception_flows_doc", "exceptionFlows"],
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
    test_condition_ids: snapshot.testConditionIds,
    requirement_version_ids: snapshot.requirementVersionIds,
    acceptance_criterion_ids: snapshot.acceptanceCriterionIds,
    coverage_item_ids: snapshot.coverageItemIds,
    bdd: snapshot.bdd,
  };
  for (const [field, value] of Object.entries(otherValues)) {
    if (value === undefined) continue;
    let previous = draft[field];
    if (previous === undefined) {
      previous = Array.isArray(value)
        ? []
        : field === "test_data"
          ? {}
          : field === "owner_id" || field === "bdd"
            ? ""
            : "manual";
    }
    if (field === "owner_id") previous = previous || "";
    if (field === "bdd") previous = previous || null;
    if (JSON.stringify(value) !== JSON.stringify(previous)) changes[field] = value;
  }
  return changes;
}
