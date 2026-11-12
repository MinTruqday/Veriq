export const TEST_LEVEL_VALUES = ["UNIT", "INTEGRATION", "SYSTEM", "ACCEPTANCE"];

export const TEST_TYPE_VALUES = [
  "functional",
  "non_functional",
  "regression",
  "smoke",
  "sanity",
  "performance",
  "security",
  "usability",
  "compatibility",
  "reliability",
  "accessibility",
];

export function mergeTestDesignValues(configured = [], current = []) {
  return [
    ...new Set(
      [...configured, ...current].map((item) => String(item || "").trim()).filter(Boolean),
    ),
  ];
}

export function testDesignValues(configured = [], current = [], defaults = []) {
  return mergeTestDesignValues([...defaults, ...configured], current);
}
