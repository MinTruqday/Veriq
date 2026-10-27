"use client";

import { useEffect, useRef, useState } from "react";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";

const emptySkill = () => ({
  name: "",
  level: "NOT_ASSESSED",
  evidence: "",
  source_block_id: null,
  source_page_no: null,
  source_sha256: null,
  confirmed: false,
});
const emptyExperience = () => ({
  title: "",
  period: "",
  domain: "",
  technologies: [],
  responsibilities: "",
  evidence: "",
  source_block_id: null,
  source_page_no: null,
  source_sha256: null,
  confirmed: false,
});

const cvWarningMessage = (warning) => {
  if (warning === "CV_HAS_UNPROCESSED_SOURCE_BLOCKS") {
    return "Một số phần của CV chưa đọc được; hãy kiểm tra lại trang và trích dẫn trước khi lưu.";
  }
  if (warning === "CV_EXTRACTION_INPUT_LIMIT_REACHED") {
    return "CV vượt giới hạn phân tích; kết quả chỉ bao phủ một phần tài liệu.";
  }
  return "Có thông tin trong CV chưa thể xác minh; hãy đối chiếu từng trích dẫn trước khi lưu.";
};

export default function MemberSkillProfilePanel({ projectId }) {
  const [profile, setProfile] = useState(null);
  const [skills, setSkills] = useState([]);
  const [experiences, setExperiences] = useState([]);
  const [availability, setAvailability] = useState("AVAILABLE");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [cvFile, setCvFile] = useState(null);
  const [cvPreview, setCvPreview] = useState(null);
  const [extractingCv, setExtractingCv] = useState(false);
  const cvInputRef = useRef(null);
  const currentProjectId = useRef(projectId);
  const cvExtractionGeneration = useRef(0);
  currentProjectId.current = projectId;

  useEffect(() => {
    let active = true;
    cvExtractionGeneration.current += 1;
    setProfile(null);
    setSkills([]);
    setExperiences([]);
    setAvailability("AVAILABLE");
    setError("");
    setSaved(false);
    setSaving(false);
    setCvFile(null);
    setCvPreview(null);
    setExtractingCv(false);
    if (cvInputRef.current) cvInputRef.current.value = "";
    setLoading(true);
    testingApi
      .getMySkillProfile(projectId)
      .then((value) => {
        if (!active) return;
        setProfile(value);
        setSkills(value.skills || []);
        setExperiences(value.experiences || []);
        setAvailability(value.availability || "AVAILABLE");
      })
      .catch((reason) => active && setError(messageOf(reason)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [projectId]);

  const patchAt = (setter, index, patch) =>
    setter((items) =>
      items.map((item, itemIndex) => (itemIndex === index ? { ...item, ...patch } : item)),
    );

  const patchEvidenceAt = (setter, index, patch) =>
    patchAt(setter, index, {
      ...patch,
      source_block_id: null,
      source_page_no: null,
      source_sha256: null,
    });

  const save = async (event) => {
    event.preventDefault();
    const saveProjectId = projectId;
    setSaving(true);
    setError("");
    setSaved(false);
    try {
      const value = await testingApi.saveMySkillProfile(saveProjectId, {
        expected_revision: profile?.revision ?? 0,
        skills: skills.filter((item) => item.name.trim()),
        experiences: experiences.filter((item) => item.title.trim()),
        availability,
      });
      if (currentProjectId.current !== saveProjectId) return;
      setProfile(value);
      setSkills(value.skills || []);
      setExperiences(value.experiences || []);
      setSaved(true);
    } catch (reason) {
      if (currentProjectId.current === saveProjectId) setError(messageOf(reason));
    } finally {
      if (currentProjectId.current === saveProjectId) setSaving(false);
    }
  };

  const extractCv = async () => {
    if (!cvFile) return;
    const extractionProjectId = projectId;
    const extractionGeneration = ++cvExtractionGeneration.current;
    setExtractingCv(true);
    setError("");
    setCvPreview(null);
    try {
      const preview = await testingApi.extractMySkillProfileFromCV(extractionProjectId, cvFile);
      if (
        currentProjectId.current === extractionProjectId &&
        cvExtractionGeneration.current === extractionGeneration
      ) {
        setCvPreview(preview);
      }
    } catch (reason) {
      if (
        currentProjectId.current === extractionProjectId &&
        cvExtractionGeneration.current === extractionGeneration
      ) {
        setError(messageOf(reason));
      }
    } finally {
      if (
        currentProjectId.current === extractionProjectId &&
        cvExtractionGeneration.current === extractionGeneration
      ) {
        setExtractingCv(false);
      }
    }
  };

  const addCvPreviewToDraft = () => {
    if (!cvPreview) return;
    const candidateSkills = (cvPreview.skills || []).map((item) => ({
      name: item.name,
      level: "NOT_ASSESSED",
      evidence: item.evidence_quote,
      source_block_id: item.source_block_id,
      source_page_no: item.page_no,
      source_sha256: cvPreview.source_sha256,
      confirmed: false,
    }));
    const candidateExperiences = (cvPreview.experiences || []).map((item) => ({
      title: item.title,
      period: item.period || "",
      domain: item.domain,
      technologies: item.technologies || [],
      responsibilities: item.responsibilities || "",
      evidence: item.evidence_quote,
      source_block_id: item.source_block_id,
      source_page_no: item.page_no,
      source_sha256: cvPreview.source_sha256,
      confirmed: false,
    }));
    setSkills((current) => {
      const names = new Set(current.map((item) => item.name.trim().toLocaleLowerCase()));
      const additions = candidateSkills.filter((item) => {
        const name = item.name.trim().toLocaleLowerCase();
        if (names.has(name)) return false;
        names.add(name);
        return true;
      });
      return [...current, ...additions];
    });
    setExperiences((current) => {
      const keys = new Set(
        current.map((item) => `${item.title.trim().toLocaleLowerCase()}|${item.evidence || ""}`),
      );
      const additions = candidateExperiences.filter((item) => {
        const key = `${item.title.trim().toLocaleLowerCase()}|${item.evidence}`;
        if (keys.has(key)) return false;
        keys.add(key);
        return true;
      });
      return [...current, ...additions];
    });
    setCvPreview(null);
    setCvFile(null);
    if (cvInputRef.current) cvInputRef.current.value = "";
  };

  if (loading) return <LoadingState label="Đang tải hồ sơ năng lực của bạn" />;

  return (
    <Panel title="Hồ sơ năng lực của tôi">
      {error && <ErrorState message={error} />}
      <form className="space-y-5 p-5" onSubmit={save}>
        <p className="text-sm text-muted-foreground">
          CV chỉ được đọc tạm để trích xuất ứng viên có dẫn chứng; tệp gốc không được lưu vào hồ sơ
          hay kho tri thức. Kết quả chỉ vào bản nháp sau khi bạn chọn, luôn chưa xác nhận cho đến
          khi bạn tự rà soát.
        </p>
        <section className="space-y-3 rounded-xl border border-border p-4">
          <h3 className="font-semibold">Trích xuất từ CV để rà soát</h3>
          <div className="flex min-w-0 flex-wrap items-center gap-3">
            <input
              aria-label="Chọn CV PDF DOCX hoặc TXT"
              ref={cvInputRef}
              className="apple-input min-w-0 flex-1"
              type="file"
              accept=".pdf,.docx,.txt"
              onChange={(event) => {
                cvExtractionGeneration.current += 1;
                setCvPreview(null);
                setExtractingCv(false);
                setCvFile(event.target.files?.[0] || null);
              }}
            />
            <button
              className="secondary-button"
              type="button"
              disabled={!cvFile || extractingCv}
              onClick={extractCv}
            >
              {extractingCv ? "Đang trích xuất…" : "Trích xuất để xem trước"}
            </button>
          </div>
          {cvPreview && (
            <div className="space-y-3 rounded-lg bg-surface-raised p-3">
              <ContentOriginBadge origin="ai_generated" aiLabel="AI trích xuất · cần rà soát" />
              <p className="text-sm">
                Xem trước: {cvPreview.skills?.length || 0} kỹ năng,{" "}
                {cvPreview.experiences?.length || 0} kinh nghiệm. Tệp chưa được lưu; các ứng viên
                thêm vào bản nháp vẫn ở trạng thái chưa xác nhận.
              </p>
              {cvPreview.source_sha256 && (
                <p className="break-all text-xs text-ink-muted">
                  Dấu nhận dạng tệp CV (SHA-256): {cvPreview.source_sha256}
                </p>
              )}
              {!!cvPreview.warnings?.length && (
                <ul role="status" className="list-disc space-y-1 pl-5 text-sm text-amber-800">
                  {[...new Set(cvPreview.warnings)].map((warning, index) => (
                    <li key={`${warning}-${index}`}>{cvWarningMessage(warning)}</li>
                  ))}
                </ul>
              )}
              <ul className="space-y-2 text-sm">
                {[...(cvPreview.skills || []), ...(cvPreview.experiences || [])].map(
                  (item, index) => (
                    <li className="break-words" key={`${item.source_block_id}-${index}`}>
                      <span className="font-medium">{item.name || item.title}</span>
                      {item.period ? ` · ${item.period}` : ""}
                      {" — “"}
                      {item.evidence_quote}
                      {"” · "}
                      {item.source_block_id}
                      {item.page_no ? ` · trang ${item.page_no}` : ""}
                    </li>
                  ),
                )}
              </ul>
              <button className="secondary-button" type="button" onClick={addCvPreviewToDraft}>
                Đưa ứng viên vào bản nháp để rà soát
              </button>
            </div>
          )}
        </section>
        <label className="field-label block max-w-sm">
          Khả dụng trong dự án
          <select
            className="apple-input mt-2"
            value={availability}
            onChange={(event) => setAvailability(event.target.value)}
          >
            <option value="AVAILABLE">Có thể nhận việc</option>
            <option value="LIMITED">Khả dụng hạn chế</option>
            <option value="UNAVAILABLE">Tạm thời không khả dụng</option>
          </select>
        </label>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">Kỹ năng</h3>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setSkills((items) => [...items, emptySkill()])}
            >
              Thêm kỹ năng
            </button>
          </div>
          {skills.length === 0 && (
            <p className="text-sm text-muted-foreground">Chưa khai báo kỹ năng.</p>
          )}
          {skills.map((skill, index) => (
            <div
              className="grid min-w-0 gap-3 rounded-xl border border-border p-4 md:grid-cols-2"
              key={`skill-${index}`}
            >
              <div className="flex flex-wrap items-center gap-2 md:col-span-2">
                <ContentOriginBadge
                  origin={skill.source_block_id ? "ai_generated" : "manual"}
                  aiLabel="AI trích từ CV"
                  humanLabel="Người dùng nhập"
                />
                <span className="text-xs text-ink-muted">
                  {skill.confirmed ? "Đã xác nhận" : "Chưa xác nhận"}
                </span>
              </div>
              <label className="field-label">
                Kỹ năng
                <input
                  className="apple-input mt-2"
                  value={skill.name}
                  onChange={(event) =>
                    patchEvidenceAt(setSkills, index, { name: event.target.value })
                  }
                  maxLength={120}
                />
              </label>
              <label className="field-label">
                Mức độ tự đánh giá
                <select
                  className="apple-input mt-2"
                  value={skill.level}
                  onChange={(event) => patchAt(setSkills, index, { level: event.target.value })}
                >
                  <option value="NOT_ASSESSED">Chưa đánh giá</option>
                  <option value="BEGINNER">Cơ bản</option>
                  <option value="INTERMEDIATE">Trung bình</option>
                  <option value="ADVANCED">Nâng cao</option>
                </select>
              </label>
              <label className="field-label md:col-span-2">
                Minh chứng hoặc kinh nghiệm liên quan
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={skill.evidence}
                  onChange={(event) =>
                    patchEvidenceAt(setSkills, index, { evidence: event.target.value })
                  }
                  maxLength={1000}
                />
                {(skill.source_block_id || skill.source_page_no) && (
                  <span className="mt-1 block text-xs text-muted-foreground">
                    Nguồn CV: {skill.source_block_id || "Không có mã khối"}
                    {skill.source_page_no ? ` · trang ${skill.source_page_no}` : ""}
                    {skill.source_sha256
                      ? ` · CV SHA-256 ${skill.source_sha256.slice(0, 12)}…`
                      : " · CV nguồn chưa lưu dấu nhận dạng"}
                  </span>
                )}
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={skill.confirmed}
                  onChange={(event) =>
                    patchAt(setSkills, index, { confirmed: event.target.checked })
                  }
                />
                Tôi xác nhận kỹ năng này
              </label>
              <button
                className="secondary-button justify-self-start"
                type="button"
                onClick={() =>
                  setSkills((items) => items.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                Xóa kỹ năng
              </button>
            </div>
          ))}
        </section>

        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold">Kinh nghiệm liên quan</h3>
            <button
              className="secondary-button"
              type="button"
              onClick={() => setExperiences((items) => [...items, emptyExperience()])}
            >
              Thêm kinh nghiệm
            </button>
          </div>
          {experiences.length === 0 && (
            <p className="text-sm text-muted-foreground">Chưa khai báo kinh nghiệm.</p>
          )}
          {experiences.map((experience, index) => (
            <div
              className="grid min-w-0 gap-3 rounded-xl border border-border p-4 md:grid-cols-2"
              key={`experience-${index}`}
            >
              <div className="flex flex-wrap items-center gap-2 md:col-span-2">
                <ContentOriginBadge
                  origin={experience.source_block_id ? "ai_generated" : "manual"}
                  aiLabel="AI trích từ CV"
                  humanLabel="Người dùng nhập"
                />
                <span className="text-xs text-ink-muted">
                  {experience.confirmed ? "Đã xác nhận" : "Chưa xác nhận"}
                </span>
              </div>
              <label className="field-label">
                Vai trò hoặc dự án
                <input
                  className="apple-input mt-2"
                  value={experience.title}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, { title: event.target.value })
                  }
                  maxLength={160}
                />
              </label>
              <label className="field-label">
                Lĩnh vực
                <input
                  className="apple-input mt-2"
                  value={experience.domain}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, { domain: event.target.value })
                  }
                  maxLength={120}
                />
              </label>
              <label className="field-label">
                Thời gian theo CV
                <input
                  className="apple-input mt-2"
                  value={experience.period || ""}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, { period: event.target.value })
                  }
                  maxLength={120}
                  placeholder="Ví dụ: 2022–2024 (nếu CV ghi rõ)"
                />
              </label>
              <label className="field-label md:col-span-2">
                Công nghệ đã dùng, phân cách bằng dấu phẩy
                <input
                  className="apple-input mt-2"
                  value={(experience.technologies || []).join(", ")}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, {
                      technologies: event.target.value
                        .split(",")
                        .map((value) => value.trim())
                        .filter(Boolean),
                    })
                  }
                />
              </label>
              <label className="field-label md:col-span-2">
                Trách nhiệm và minh chứng
                <textarea
                  className="apple-input mt-2 min-h-20"
                  value={experience.responsibilities}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, {
                      responsibilities: event.target.value,
                    })
                  }
                  maxLength={2000}
                />
              </label>
              <label className="field-label md:col-span-2">
                Trích dẫn hoặc ghi chú dẫn chứng
                <textarea
                  className="apple-input mt-2 min-h-16"
                  value={experience.evidence}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, { evidence: event.target.value })
                  }
                  maxLength={1000}
                />
                {(experience.source_block_id || experience.source_page_no) && (
                  <span className="mt-1 block text-xs text-muted-foreground">
                    Nguồn CV: {experience.source_block_id || "Không có mã khối"}
                    {experience.source_page_no ? ` · trang ${experience.source_page_no}` : ""}
                    {experience.source_sha256
                      ? ` · CV SHA-256 ${experience.source_sha256.slice(0, 12)}…`
                      : " · CV nguồn chưa lưu dấu nhận dạng"}
                  </span>
                )}
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={experience.confirmed}
                  onChange={(event) =>
                    patchAt(setExperiences, index, { confirmed: event.target.checked })
                  }
                />
                Tôi xác nhận kinh nghiệm này
              </label>
              <button
                className="secondary-button justify-self-start"
                type="button"
                onClick={() =>
                  setExperiences((items) => items.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                Xóa kinh nghiệm
              </button>
            </div>
          ))}
        </section>

        <div className="flex flex-wrap items-center gap-3">
          <button className="primary-button" type="submit" disabled={saving}>
            {saving ? "Đang lưu…" : "Lưu hồ sơ"}
          </button>
          {saved && (
            <p role="status" className="text-sm text-emerald-700">
              Đã lưu hồ sơ năng lực.
            </p>
          )}
          {profile?.revision > 0 && (
            <p className="text-sm text-muted-foreground">Phiên bản hồ sơ {profile.revision}</p>
          )}
        </div>
      </form>
    </Panel>
  );
}
