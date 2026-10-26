const hasPermission = (permissions, permission) => permissions.includes(permission);

export function testDesignAccess({ workspaceView = "", caseTab = "cases", permissions = [] }) {
  const isCaseWorkspace = workspaceView === "" || workspaceView === "cases";
  const canReadTestCases = hasPermission(permissions, "testcase.read");
  const showCases = isCaseWorkspace && caseTab === "cases" && canReadTestCases;
  const showImport =
    isCaseWorkspace &&
    caseTab === "import" &&
    canReadTestCases &&
    (hasPermission(permissions, "testcase.import") ||
      hasPermission(permissions, "testcase.export"));

  return {
    canReadTestCases,
    showCases,
    showImport,
    canLoadDrafts: (showCases || showImport) && canReadTestCases,
    canLoadTestCases:
      (showCases || (isCaseWorkspace && caseTab === "automation") || showImport) &&
      canReadTestCases,
    canLoadRepository: showCases,
    canRenderRepository:
      canReadTestCases &&
      (workspaceView === "" ||
        workspaceView === "repository" ||
        workspaceView === "reusable-steps"),
    canReadTestSets: hasPermission(permissions, "testsuite.read"),
    canRenderImport:
      canReadTestCases &&
      (hasPermission(permissions, "testcase.import") ||
        hasPermission(permissions, "testcase.export")),
  };
}
