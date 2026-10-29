"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ErrorState, Panel, StatusPill, useActionDialog } from "./WorkspacePrimitives";
import { messageOf } from "../lib/testing";
import { testingApi } from "../services/testing.service";
import { Modal, ModalHeader, ModalTitle } from "@/shared/components/ui/Modal";
import MultiSelect from "@/shared/components/ui/MultiSelect";

const EMPTY_FORM = {
  name: "",
  description: "",
  profileKey: "",
  profileName: "",
  deviceType: "desktop",
  operatingSystem: "",
  browser: "",
  viewportWidth: "",
  viewportHeight: "",
};

export default function DeviceMatricesPanel({ project, plans, runs, onChanged }) {
  const { ask, dialog } = useActionDialog();
  const [matrices, setMatrices] = useState([]);
  const [form, setForm] = useState(EMPTY_FORM);
  const [selectedMatrixId, setSelectedMatrixId] = useState("");
  const [targetType, setTargetType] = useState("test_plan");
  const [targetId, setTargetId] = useState("");
  const [profileKeys, setProfileKeys] = useState([]);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const can = (permission) => project.current_permissions?.includes(permission);
  const targets = useMemo(
    () => (targetType === "test_plan" ? plans : runs).filter((item) => item.status === "DRAFT"),
    [plans, runs, targetType],
  );
  const selectedMatrix = matrices.find((item) => item._id === selectedMatrixId);
  const load = useCallback(async () => {
    try {
      const values = await testingApi.listDeviceMatrices(project._id);
      setMatrices(values);
      setSelectedMatrixId((current) => current || values[0]?._id || "");
    } catch (reason) {
      setError(messageOf(reason));
    }
  }, [project._id]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    setTargetId("");
  }, [targetType]);
  useEffect(() => {
    setProfileKeys(
      selectedMatrix?.profiles?.filter((item) => item.enabled !== false).map((item) => item.key) ||
        [],
    );
  }, [selectedMatrix]);
  const createMatrix = async (event) => {
    event.preventDefault();
    try {
      await testingApi.createDeviceMatrix(project._id, {
        name: form.name,
        description: form.description,
        profiles: [
          {
            key: form.profileKey,
            name: form.profileName,
            device_type: form.deviceType,
            operating_system: form.operatingSystem,
            browser: form.browser,
            viewport_width: form.viewportWidth ? Number(form.viewportWidth) : null,
            viewport_height: form.viewportHeight ? Number(form.viewportHeight) : null,
          },
        ],
      });
      setForm(EMPTY_FORM);
      setCreating(false);
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const renameMatrix = async (matrix) => {
    const answer = await ask({
      title: "Sửa ma trận thiết bị",
      description: matrix.name,
      confirmLabel: "Lưu thay đổi",
      fields: [
        { name: "name", label: "Tên ma trận", defaultValue: matrix.name, required: true },
        {
          name: "description",
          label: "Mô tả",
          defaultValue: matrix.description || "",
          multiline: true,
        },
      ],
    });
    if (!answer) return;
    try {
      await testingApi.updateDeviceMatrix(matrix._id, {
        expected_revision: matrix.revision,
        name: answer.name,
        description: answer.description,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const archiveMatrix = async (matrix) => {
    const answer = await ask({
      title: "Lưu trữ ma trận thiết bị",
      description: matrix.name,
      confirmLabel: "Lưu trữ",
      fields: [{ name: "reason", label: "Lý do", required: true, multiline: true }],
    });
    if (!answer) return;
    try {
      await testingApi.archiveDeviceMatrix(matrix._id, {
        expected_revision: matrix.revision,
        reason: answer.reason,
      });
      await load();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  const assignMatrix = async (event) => {
    event.preventDefault();
    const target = targets.find((item) => item._id === targetId);
    if (!selectedMatrix || !target) return;
    try {
      await testingApi.assignDeviceMatrix(selectedMatrix._id, {
        target_type: targetType,
        target_id: target._id,
        expected_target_revision: target.revision,
        profile_keys: profileKeys,
      });
      await onChanged?.();
    } catch (reason) {
      setError(messageOf(reason));
    }
  };
  return (
    <Panel
      title="Ma trận thiết bị"
      actions={
        can("device_matrix.manage") ? (
          <button className="secondary-button" type="button" onClick={() => setCreating(true)}>
            Tạo ma trận
          </button>
        ) : null
      }
    >
      {error && <ErrorState message={error} />}
      {can("device_matrix.manage") && (
        <Modal
          isOpen={creating}
          onClose={() => setCreating(false)}
          ariaLabel="Tạo ma trận thiết bị"
          className="max-w-2xl max-h-[90dvh] overflow-y-auto"
        >
          <ModalHeader>
            <ModalTitle>Tạo ma trận thiết bị</ModalTitle>
          </ModalHeader>
          <form className="grid min-w-0 gap-3 p-5 sm:grid-cols-2" onSubmit={createMatrix}>
            <input
              aria-label="Tên ma trận thiết bị"
              className="apple-input w-full min-w-0"
              required
              placeholder="Tên ma trận"
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
            />
            <input
              aria-label="Mã hồ sơ thiết bị"
              className="apple-input w-full min-w-0"
              required
              placeholder="Mã hồ sơ"
              value={form.profileKey}
              onChange={(event) => setForm({ ...form, profileKey: event.target.value })}
            />
            <input
              aria-label="Tên hồ sơ thiết bị"
              className="apple-input w-full min-w-0"
              required
              placeholder="Tên hồ sơ"
              value={form.profileName}
              onChange={(event) => setForm({ ...form, profileName: event.target.value })}
            />
            <select
              aria-label="Loại thiết bị"
              className="apple-input w-full min-w-0"
              value={form.deviceType}
              onChange={(event) => setForm({ ...form, deviceType: event.target.value })}
            >
              <option value="desktop">Máy tính để bàn</option>
              <option value="laptop">Máy tính xách tay</option>
              <option value="tablet">Máy tính bảng</option>
              <option value="mobile">Điện thoại</option>
              <option value="other">Khác</option>
            </select>
            <input
              aria-label="Hệ điều hành"
              className="apple-input w-full min-w-0"
              required
              placeholder="Hệ điều hành"
              value={form.operatingSystem}
              onChange={(event) => setForm({ ...form, operatingSystem: event.target.value })}
            />
            <input
              aria-label="Trình duyệt"
              className="apple-input w-full min-w-0"
              placeholder="Trình duyệt"
              value={form.browser}
              onChange={(event) => setForm({ ...form, browser: event.target.value })}
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                aria-label="Chiều rộng khung nhìn"
                className="apple-input"
                min="1"
                type="number"
                placeholder="Rộng"
                value={form.viewportWidth}
                onChange={(event) => setForm({ ...form, viewportWidth: event.target.value })}
              />
              <input
                aria-label="Chiều cao khung nhìn"
                className="apple-input"
                min="1"
                type="number"
                placeholder="Cao"
                value={form.viewportHeight}
                onChange={(event) => setForm({ ...form, viewportHeight: event.target.value })}
              />
            </div>
            <div className="action-dialog-footer flex justify-end gap-3 sm:col-span-2">
              <button className="secondary-button" type="button" onClick={() => setCreating(false)}>
                Hủy
              </button>
              <button className="apple-button" type="submit">
                Tạo ma trận
              </button>
            </div>
          </form>
        </Modal>
      )}
      <div className="grid gap-4 p-4 lg:grid-cols-2">
        <div className="space-y-2">
          {matrices.length === 0 && (
            <p className="text-sm text-ink-muted">Chưa có ma trận thiết bị</p>
          )}
          {matrices.map((matrix) => (
            <div className="min-w-0 rounded-xl border border-border p-3" key={matrix._id}>
              <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="break-words font-medium text-ink">{matrix.name}</p>
                  <p className="text-xs text-ink-muted">
                    {matrix.profiles?.length || 0} hồ sơ thiết bị
                  </p>
                </div>
                <StatusPill value={matrix.status} />
              </div>
              {can("device_matrix.manage") && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => renameMatrix(matrix)}
                  >
                    Sửa
                  </button>
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => archiveMatrix(matrix)}
                  >
                    Lưu trữ
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
        {can("device_matrix.assign") && matrices.length > 0 && (
          <form className="min-w-0 space-y-3" onSubmit={assignMatrix}>
            <select
              aria-label="Ma trận thiết bị cần gán"
              className="apple-input w-full min-w-0"
              value={selectedMatrixId}
              onChange={(event) => setSelectedMatrixId(event.target.value)}
            >
              {matrices.map((matrix) => (
                <option key={matrix._id} value={matrix._id}>
                  {matrix.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Loại phạm vi được gán"
              className="apple-input w-full min-w-0"
              value={targetType}
              onChange={(event) => setTargetType(event.target.value)}
            >
              <option value="test_plan">Kế hoạch kiểm thử</option>
              <option value="test_run">Lần chạy kiểm thử</option>
            </select>
            <select
              aria-label="Phạm vi được gán"
              className="apple-input w-full min-w-0"
              required
              value={targetId}
              onChange={(event) => setTargetId(event.target.value)}
            >
              <option value="">Chọn phạm vi bản nháp</option>
              {targets.map((item) => (
                <option key={item._id} value={item._id}>
                  {item.name}
                </option>
              ))}
            </select>
            <MultiSelect
              label="Hồ sơ thiết bị"
              options={
                selectedMatrix?.profiles
                  ?.filter((item) => item.enabled !== false)
                  .map((profile) => ({ value: profile.key, label: profile.name })) || []
              }
              searchPlaceholder="Tìm hồ sơ thiết bị"
              value={profileKeys}
              onChange={setProfileKeys}
            />
            <button className="apple-button" type="submit">
              Gán ma trận thiết bị
            </button>
          </form>
        )}
      </div>
      {dialog}
    </Panel>
  );
}
