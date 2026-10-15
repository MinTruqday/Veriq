"use client";

import { useCallback, useEffect, useState } from "react";
import DataTable from "../../../components/DataTable";
import { Panel } from "../../../components/WorkspacePrimitives";
import { testingApi } from "../../../services/testing.service";
import { messageOf, textDoc } from "../../../lib/testing";

export default function TestRepositoryPanel({ project, can, onError }) {
  const [nodes, setNodes] = useState([]);
  const [steps, setSteps] = useState([]);
  const [nodeName, setNodeName] = useState("");
  const [parentId, setParentId] = useState("");
  const [stepName, setStepName] = useState("");
  const [stepAction, setStepAction] = useState("");
  const load = useCallback(async () => {
    try {
      const [repository, reusable] = await Promise.all([
        testingApi.listTestRepository(project._id),
        testingApi.listReusableTestSteps(project._id),
      ]);
      setNodes(repository);
      setSteps(reusable);
    } catch (reason) {
      onError(messageOf(reason));
    }
  }, [onError, project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  const createNode = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createTestRepositoryNode(project._id, {
        name: nodeName,
        parent_id: parentId || null,
      });
      setNodeName("");
      setParentId("");
      await load();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  const createStep = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createReusableTestStep(project._id, {
        name: stepName,
        action_doc: textDoc(stepAction),
        expected_doc: textDoc(""),
      });
      setStepName("");
      setStepAction("");
      await load();
    } catch (reason) {
      onError(messageOf(reason));
    }
  };
  return (
    <div className="grid gap-5 xl:grid-cols-2">
      <Panel title="Kho ca kiểm thử">
        {can("testcase.create") && (
          <form className="mb-4 grid gap-2 md:grid-cols-3" onSubmit={createNode}>
            <input
              className="apple-input"
              value={nodeName}
              onChange={(event) => setNodeName(event.target.value)}
              placeholder="Tên thư mục"
              required
            />
            <select
              className="apple-input"
              value={parentId}
              onChange={(event) => setParentId(event.target.value)}
            >
              <option value="">Thư mục gốc</option>
              {nodes.map((node) => (
                <option key={node._id} value={node._id}>
                  {node.name}
                </option>
              ))}
            </select>
            <button className="primary-button" type="submit">
              Tạo thư mục
            </button>
          </form>
        )}
        <DataTable
          items={nodes}
          empty="Chưa có thư mục kiểm thử"
          columns={[
            { key: "name", label: "Thư mục" },
            {
              key: "parent_id",
              label: "Thuộc thư mục",
              render: (item) => nodes.find((node) => node._id === item.parent_id)?.name || "Gốc",
            },
            { key: "updated_at", label: "Cập nhật" },
          ]}
        />
      </Panel>
      <Panel title="Bước dùng lại">
        {can("testcase.create") && (
          <form className="mb-4 grid gap-2" onSubmit={createStep}>
            <input
              className="apple-input"
              value={stepName}
              onChange={(event) => setStepName(event.target.value)}
              placeholder="Tên bước"
              required
            />
            <input
              className="apple-input"
              value={stepAction}
              onChange={(event) => setStepAction(event.target.value)}
              placeholder="Hành động"
              required
            />
            <button className="primary-button w-fit" type="submit">
              Tạo bước dùng lại
            </button>
          </form>
        )}
        <DataTable
          items={steps}
          empty="Chưa có bước dùng lại"
          columns={[
            { key: "name", label: "Tên bước" },
            { key: "version", label: "Phiên bản" },
            { key: "updated_at", label: "Cập nhật" },
          ]}
        />
      </Panel>
    </div>
  );
}
