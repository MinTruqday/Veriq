"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Folder, Pencil } from "lucide-react";
import DataTable from "../../../components/DataTable";
import { LoadingState, Panel } from "../../../components/WorkspacePrimitives";
import { testingApi } from "../../../services/testing.service";
import { messageOf, textDoc } from "../../../lib/testing";
import { Modal, ModalFooter, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";

function RepositoryBranch({
  node,
  childrenByParent,
  expanded,
  onToggle,
  onRename,
  canRename,
  depth = 0,
}) {
  const children = childrenByParent.get(node._id) || [];
  const isExpanded = expanded.has(node._id);
  return (
    <li>
      <div
        className="flex min-h-11 min-w-0 items-center gap-2 rounded-control px-2 hover:bg-surface-quiet"
        style={{ paddingInlineStart: `${Math.min(depth * 16, 96) + 8}px` }}
      >
        {children.length ? (
          <button
            aria-expanded={isExpanded}
            aria-label={`${isExpanded ? "Thu gọn" : "Mở"} thư mục ${node.name}`}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet"
            type="button"
            onClick={() => onToggle(node._id)}
          >
            {isExpanded ? (
              <ChevronDown size={16} aria-hidden="true" />
            ) : (
              <ChevronRight size={16} aria-hidden="true" />
            )}
          </button>
        ) : (
          <span aria-hidden="true" className="w-8 shrink-0" />
        )}
        <Folder size={17} aria-hidden="true" className="shrink-0 text-brand" />
        <span className="min-w-0 break-words text-sm font-medium text-ink">{node.name}</span>
        {canRename && (
          <button
            className="ml-auto flex h-8 w-8 shrink-0 items-center justify-center rounded-control text-ink-muted hover:bg-surface-quiet hover:text-ink"
            type="button"
            aria-label={`Đổi tên thư mục ${node.name}`}
            onClick={() => onRename(node)}
          >
            <Pencil size={15} aria-hidden="true" />
          </button>
        )}
      </div>
      {children.length > 0 && isExpanded && (
        <ul className="space-y-1">
          {children.map((child) => (
            <RepositoryBranch
              key={child._id}
              node={child}
              childrenByParent={childrenByParent}
              expanded={expanded}
              onToggle={onToggle}
              onRename={onRename}
              canRename={canRename}
              depth={depth + 1}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function TestRepositoryPanel({ project, can, ask, onError, focus = "" }) {
  const [nodes, setNodes] = useState([]);
  const [steps, setSteps] = useState([]);
  const [nodeName, setNodeName] = useState("");
  const [parentId, setParentId] = useState("");
  const [nodeModalOpen, setNodeModalOpen] = useState(false);
  const [stepName, setStepName] = useState("");
  const [stepAction, setStepAction] = useState("");
  const [stepModalOpen, setStepModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [savingNode, setSavingNode] = useState(false);
  const [savingStep, setSavingStep] = useState(false);
  const [expandedNodeIds, setExpandedNodeIds] = useState(() => new Set());
  const loadGeneration = useRef(0);
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    setLoading(true);
    setLoadFailed(false);
    setLoadError("");
    try {
      const [repository, reusable] = await Promise.all([
        testingApi.listTestRepository(project._id),
        testingApi.listReusableTestSteps(project._id),
      ]);
      if (requestGeneration !== loadGeneration.current) return;
      setNodes(repository);
      setSteps(reusable);
    } catch (reason) {
      if (requestGeneration !== loadGeneration.current) return;
      setLoadFailed(true);
      setLoadError(messageOf(reason));
    } finally {
      if (requestGeneration === loadGeneration.current) setLoading(false);
    }
  }, [loadGeneration, project._id]);
  useEffect(() => {
    void load();
    return () => {
      loadGeneration.current += 1;
    };
  }, [load, loadGeneration]);
  useEffect(() => {
    setExpandedNodeIds(new Set(nodes.filter((node) => !node.parent_id).map((node) => node._id)));
  }, [nodes]);
  const createNode = async (event) => {
    event.preventDefault();
    setSavingNode(true);
    try {
      await testingApi.createTestRepositoryNode(project._id, {
        name: nodeName,
        parent_id: parentId || null,
      });
      setNodeName("");
      setParentId("");
      setNodeModalOpen(false);
      await load();
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setSavingNode(false);
    }
  };
  const createStep = async (event) => {
    event.preventDefault();
    setSavingStep(true);
    try {
      await testingApi.createReusableTestStep(project._id, {
        name: stepName,
        action_doc: textDoc(stepAction),
        expected_doc: textDoc(""),
      });
      setStepName("");
      setStepAction("");
      setStepModalOpen(false);
      await load();
    } catch (reason) {
      onError(messageOf(reason));
    } finally {
      setSavingStep(false);
    }
  };
  const renameNode = async (node) => {
    await ask({
      title: "Đổi tên thư mục kiểm thử",
      description: node.name,
      confirmLabel: "Lưu tên mới",
      fields: [{ name: "name", label: "Tên thư mục", initialValue: node.name, required: true }],
      onConfirm: async ({ name }) => {
        try {
          await testingApi.updateTestRepositoryNode(node._id, {
            expected_revision: node.revision,
            name: name.trim(),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const editStep = async (step) => {
    await ask({
      title: "Tạo phiên bản bước dùng lại",
      description: `Phiên bản hiện tại v${step.version} sẽ được giữ nguyên. Ca kiểm thử đã duyệt tiếp tục dùng phiên bản đã ghim.`,
      confirmLabel: "Tạo phiên bản mới",
      fields: [
        { name: "name", label: "Tên bước", initialValue: step.name, required: true },
        {
          name: "action",
          label: "Hành động",
          initialValue: docText(step.action_doc),
          required: true,
          multiline: true,
        },
        {
          name: "expected",
          label: "Kết quả mong đợi",
          initialValue: docText(step.expected_doc),
          multiline: true,
        },
      ],
      onConfirm: async ({ name, action, expected }) => {
        try {
          await testingApi.updateReusableTestStep(step._id, {
            expected_revision: step.revision,
            name: name.trim(),
            action_doc: textDoc(action),
            expected_doc: textDoc(expected || ""),
          });
          await load();
        } catch (reason) {
          throw new Error(messageOf(reason));
        }
      },
    });
  };
  const childrenByParent = new Map();
  for (const node of nodes) {
    const parentId =
      node.parent_id && nodes.some((item) => item._id === node.parent_id) ? node.parent_id : "";
    const children = childrenByParent.get(parentId) || [];
    children.push(node);
    childrenByParent.set(parentId, children);
  }
  const toggleNode = (nodeId) =>
    setExpandedNodeIds((current) => {
      const next = new Set(current);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  return (
    <div className={`grid gap-5 ${focus ? "" : "xl:grid-cols-2"}`}>
      {focus !== "reusable-steps" && (
        <Panel
          title="Kho ca kiểm thử"
          actions={
            can("testcase.create") && !loading && !loadFailed ? (
              <button
                className="primary-button w-fit"
                type="button"
                onClick={() => setNodeModalOpen(true)}
              >
                Tạo thư mục
              </button>
            ) : null
          }
          className="!shadow-none"
        >
          {loading ? (
            <div className="p-5">
              <LoadingState />
            </div>
          ) : loadFailed ? (
            <div className="space-y-3 p-5">
              <p role="alert" className="text-sm text-danger">
                Không thể tải kho ca kiểm thử{loadError ? `: ${loadError}` : ""}
              </p>
              <button
                className="secondary-button"
                disabled={loading}
                type="button"
                onClick={() => void load()}
              >
                Thử tải lại
              </button>
            </div>
          ) : nodes.length ? (
            <ul aria-label="Cấu trúc kho kiểm thử" className="space-y-1 p-4">
              {(childrenByParent.get("") || []).map((node) => (
                <RepositoryBranch
                  key={node._id}
                  node={node}
                  childrenByParent={childrenByParent}
                  expanded={expandedNodeIds}
                  onToggle={toggleNode}
                  onRename={renameNode}
                  canRename={can("testcase.update")}
                />
              ))}
            </ul>
          ) : (
            <div className="p-4">
              <DataTable items={[]} empty="Chưa có thư mục kiểm thử" columns={[]} />
            </div>
          )}
        </Panel>
      )}
      {focus !== "repository" && (
        <Panel
          title="Danh sách bước dùng lại"
          actions={
            can("testcase.create") && !loading && !loadFailed ? (
              <button
                className="primary-button w-fit"
                type="button"
                onClick={() => setStepModalOpen(true)}
              >
                Tạo bước dùng lại
              </button>
            ) : null
          }
          className="!shadow-none"
        >
          {loading ? (
            <div className="p-5">
              <LoadingState />
            </div>
          ) : loadFailed ? (
            <div className="space-y-3 p-5">
              <p role="alert" className="text-sm text-danger">
                Không thể tải bước dùng lại{loadError ? `: ${loadError}` : ""}
              </p>
              <button
                className="secondary-button"
                disabled={loading}
                type="button"
                onClick={() => void load()}
              >
                Thử tải lại
              </button>
            </div>
          ) : (
            <DataTable
              items={steps}
              empty="Chưa có bước dùng lại"
              columns={[
                { key: "name", label: "Tên bước" },
                { key: "version", label: "Phiên bản" },
                { key: "updated_at", label: "Cập nhật" },
                {
                  key: "actions",
                  label: "Thao tác",
                  hideWhenEmpty: true,
                  render: (item) =>
                    can("testcase.update") ? (
                      <button
                        className="secondary-button"
                        type="button"
                        onClick={() => void editStep(item)}
                      >
                        Tạo phiên bản mới
                      </button>
                    ) : null,
                },
              ]}
            />
          )}
        </Panel>
      )}
      <Modal
        isOpen={nodeModalOpen}
        onClose={() => {
          if (!savingNode) setNodeModalOpen(false);
        }}
        ariaLabel="Tạo thư mục kiểm thử"
      >
        <ModalHeader>
          <ModalTitle>Tạo thư mục kiểm thử</ModalTitle>
        </ModalHeader>
        <form className="space-y-4 p-5" onSubmit={createNode}>
          <label className="field-label" htmlFor="test-repository-node-name">
            Tên thư mục
            <input
              id="test-repository-node-name"
              className="apple-input mt-2 w-full"
              value={nodeName}
              onChange={(event) => setNodeName(event.target.value)}
              required
            />
          </label>
          <label className="field-label" htmlFor="test-repository-node-parent">
            Thư mục cha
            <select
              id="test-repository-node-parent"
              className="apple-input mt-2 w-full"
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
          </label>
          <ModalFooter className="-mx-5 -mb-5">
            <button
              className="secondary-button"
              disabled={savingNode}
              onClick={() => setNodeModalOpen(false)}
              type="button"
            >
              Hủy
            </button>
            <button className="primary-button" disabled={savingNode} type="submit">
              {savingNode ? "Đang tạo thư mục" : "Tạo thư mục"}
            </button>
          </ModalFooter>
        </form>
      </Modal>
      <Modal
        isOpen={stepModalOpen}
        onClose={() => {
          if (!savingStep) setStepModalOpen(false);
        }}
        ariaLabel="Tạo bước dùng lại"
      >
        <ModalHeader>
          <ModalTitle>Tạo bước dùng lại</ModalTitle>
        </ModalHeader>
        <form className="space-y-4 p-5" onSubmit={createStep}>
          <label className="field-label" htmlFor="reusable-step-name">
            Tên bước
            <input
              id="reusable-step-name"
              className="apple-input mt-2 w-full"
              value={stepName}
              onChange={(event) => setStepName(event.target.value)}
              required
            />
          </label>
          <label className="field-label" htmlFor="reusable-step-action">
            Hành động
            <textarea
              id="reusable-step-action"
              className="apple-input mt-2 min-h-24 w-full min-w-0"
              value={stepAction}
              onChange={(event) => setStepAction(event.target.value)}
              required
            />
          </label>
          <ModalFooter className="-mx-5 -mb-5">
            <button
              className="secondary-button"
              disabled={savingStep}
              onClick={() => setStepModalOpen(false)}
              type="button"
            >
              Hủy
            </button>
            <button className="primary-button" disabled={savingStep} type="submit">
              {savingStep ? "Đang tạo bước" : "Tạo bước dùng lại"}
            </button>
          </ModalFooter>
        </form>
      </Modal>
    </div>
  );
}
