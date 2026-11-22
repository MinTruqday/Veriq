"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Folder, Pencil } from "lucide-react";
import SearchField from "@/shared/components/ui/SearchField";
import { LoadingState, Panel } from "../../../components/WorkspacePrimitives";
import { testingApi } from "../../../services/testing.service";
import { messageOf } from "../../../lib/testing";
import { Modal, ModalFooter, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";

function RepositoryBranch({
  node,
  childrenByParent,
  expanded,
  onToggle,
  onRename,
  canRename,
  matches,
  searching,
  depth = 0,
}) {
  const allChildren = childrenByParent.get(node._id) || [];
  const children = searching ? allChildren.filter((child) => matches.has(child._id)) : allChildren;
  const isExpanded = expanded.has(node._id) || (searching && matches.has(node._id));
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
              matches={matches}
              searching={searching}
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
  const [nodeName, setNodeName] = useState("");
  const [parentId, setParentId] = useState("");
  const [nodeModalOpen, setNodeModalOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [savingNode, setSavingNode] = useState(false);
  const [expandedNodeIds, setExpandedNodeIds] = useState(() => new Set());
  const [repositoryQuery, setRepositoryQuery] = useState("");
  const loadGeneration = useRef(0);
  const load = useCallback(async () => {
    const requestGeneration = ++loadGeneration.current;
    setLoading(true);
    setLoadFailed(false);
    setLoadError("");
    try {
      const repository = await testingApi.listTestRepository(project._id);
      if (requestGeneration !== loadGeneration.current) return;
      setNodes(repository);
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
  const childrenByParent = new Map();
  const normalizedRepositoryQuery = repositoryQuery.trim().toLocaleLowerCase();
  const matchingNodeIds = new Set();
  for (const node of nodes) {
    if (
      !normalizedRepositoryQuery ||
      `${node.name} ${node._id}`.toLocaleLowerCase().includes(normalizedRepositoryQuery)
    ) {
      let match = node;
      while (match) {
        matchingNodeIds.add(match._id);
        match = nodes.find((item) => item._id === match.parent_id);
      }
    }
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
    <div>
        <Panel title="Thư mục kiểm thử" className="!shadow-none">
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
            <div className="space-y-4 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-sm text-ink-muted">{nodes.length} thư mục</p>
                <div className="flex min-w-0 flex-1 flex-wrap items-center justify-end gap-2">
                  <SearchField
                    ariaLabel="Tìm thư mục kiểm thử"
                    className="min-w-[15rem] flex-1 xl:max-w-sm"
                    onChange={(event) => setRepositoryQuery(event.target.value)}
                    placeholder="Tìm thư mục"
                    value={repositoryQuery}
                  />
                  {can("testcase.create") && (
                    <button
                      className="primary-button shrink-0"
                      type="button"
                      onClick={() => setNodeModalOpen(true)}
                    >
                      Tạo thư mục
                    </button>
                  )}
                </div>
              </div>
              <ul aria-label="Cấu trúc kho kiểm thử" className="space-y-1">
                {(childrenByParent.get("") || [])
                  .filter((node) => matchingNodeIds.has(node._id))
                  .map((node) => (
                    <RepositoryBranch
                      key={node._id}
                      node={node}
                      childrenByParent={childrenByParent}
                      expanded={expandedNodeIds}
                      onToggle={toggleNode}
                      onRename={renameNode}
                      canRename={can("testcase.update")}
                      matches={matchingNodeIds}
                      searching={Boolean(normalizedRepositoryQuery)}
                    />
                  ))}
              </ul>
              {normalizedRepositoryQuery && matchingNodeIds.size === 0 && (
                <p className="px-3 py-2 text-sm text-ink-muted">Không tìm thấy thư mục phù hợp.</p>
              )}
            </div>
          ) : (
            <div className="space-y-3 p-5">
              <p className="font-medium text-ink">Kho kiểm thử chưa có thư mục</p>
              <p className="text-sm text-ink-muted">
                Tạo thư mục để nhóm các ca theo tính năng, phân hệ hoặc phạm vi kiểm thử.
              </p>
              {can("testcase.create") && !loadFailed && (
                <button
                  className="primary-button w-fit"
                  type="button"
                  onClick={() => setNodeModalOpen(true)}
                >
                  Tạo thư mục
                </button>
              )}
            </div>
          )}
        </Panel>
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
    </div>
  );
}
