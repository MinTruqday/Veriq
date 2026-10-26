import assert from "node:assert/strict";
import test from "node:test";
import { testDesignAccess } from "./testDesignAccess.logic.mjs";

test("test design read routes render and load data only with matching permission", () => {
  const denied = testDesignAccess({
    workspaceView: "cases",
    caseTab: "cases",
    permissions: [],
  });

  assert.equal(denied.showCases, false);
  assert.equal(denied.canLoadDrafts, false);
  assert.equal(denied.canLoadTestCases, false);
  assert.equal(denied.canLoadRepository, false);
  assert.equal(denied.canRenderRepository, false);

  const allowed = testDesignAccess({
    workspaceView: "cases",
    caseTab: "cases",
    permissions: ["testcase.read"],
  });

  assert.equal(allowed.showCases, true);
  assert.equal(allowed.canLoadDrafts, true);
  assert.equal(allowed.canLoadTestCases, true);
  assert.equal(allowed.canLoadRepository, true);
  assert.equal(allowed.canRenderRepository, false);
});

test("import/export route stays hidden without read access and renders with read plus route permission", () => {
  const denied = testDesignAccess({
    workspaceView: "cases",
    caseTab: "import",
    permissions: ["testcase.import"],
  });

  assert.equal(denied.showImport, false);
  assert.equal(denied.canLoadDrafts, false);
  assert.equal(denied.canLoadTestCases, false);
  assert.equal(denied.canRenderImport, false);

  const allowed = testDesignAccess({
    workspaceView: "cases",
    caseTab: "import",
    permissions: ["testcase.read", "testcase.import"],
  });

  assert.equal(allowed.showImport, true);
  assert.equal(allowed.canLoadDrafts, true);
  assert.equal(allowed.canLoadTestCases, true);
  assert.equal(allowed.canRenderImport, true);
});

test("repository and Test Set routes do not expose data without their read permissions", () => {
  const repositoryDenied = testDesignAccess({
    workspaceView: "repository",
    permissions: [],
  });
  const testSetDenied = testDesignAccess({
    workspaceView: "test-sets",
    permissions: [],
  });

  assert.equal(repositoryDenied.canRenderRepository, false);
  assert.equal(testSetDenied.canReadTestSets, false);

  const testSetAllowed = testDesignAccess({
    workspaceView: "test-sets",
    permissions: ["testsuite.read"],
  });
  assert.equal(testSetAllowed.canReadTestSets, true);
});
