"use client";

import { useEffect, useRef, useState } from "react";
import { Trash2 } from "lucide-react";
import { ErrorState, LoadingState, Panel } from "./WorkspacePrimitives";
import { testingApi } from "../services/testing.service";
import { messageOf } from "../lib/testing";
import ContentOriginBadge from "../../../shared/components/common/ContentOriginBadge";

const emptySkill = () => ({
  name: "",
  level: "",
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

export default function MemberSkillProfilePanel({ projectId }) {
  const [profile, setProfile] = useState(null);
  const [skills, setSkills] = useState([]);
  const [experiences, setExperiences] = useState([]);
  const [availability, setAvailability] = useState("AVAILABLE");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const currentProjectId = useRef(projectId);
  currentProjectId.current = projectId;

  useEffect(() => {
    let active = true;
    setProfile(null);
    setSkills([]);
    setExperiences([]);
    setAvailability("AVAILABLE");
    setError("");
    setSaved(false);
    setSaving(false);
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

  if (loading) return <LoadingState label="Đang tải hồ sơ năng lực của bạn" />;

  return (
    <Panel title="Hồ sơ năng lực của tôi">
      {error && <ErrorState message={error} />}
      <form className="space-y-5 p-5" onSubmit={save}>
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

        <section
          aria-labelledby="member-skills-heading"
          className="space-y-3 border-b border-border pb-5"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold" id="member-skills-heading">
              Kỹ năng
            </h3>
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
              className="grid min-w-0 gap-3 rounded-xl border border-border bg-white p-4 md:grid-cols-2"
              key={`skill-${index}`}
            >
              <div className="flex flex-wrap items-center gap-2 md:col-span-2">
                <ContentOriginBadge
                  origin={skill.source_block_id ? "ai_generated" : "manual"}
                  aiLabel="Có nguồn dẫn chứng"
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
                <input
                  className="apple-input mt-2"
                  value={skill.level || ""}
                  onChange={(event) => patchAt(setSkills, index, { level: event.target.value })}
                  placeholder="Nhập cấp độ nếu dự án cần (tùy chọn)"
                  maxLength={100}
                />
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
                    Có dẫn chứng nguồn{skill.source_page_no ? `, trang ${skill.source_page_no}` : ""}
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
                aria-label={`Xóa kỹ năng ${index + 1}`}
                className="icon-button h-9 w-9 justify-self-start text-danger"
                title="Xóa kỹ năng"
                type="button"
                onClick={() =>
                  setSkills((items) => items.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                <Trash2 aria-hidden="true" size={16} />
              </button>
            </div>
          ))}
        </section>

        <section aria-labelledby="member-experiences-heading" className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="font-semibold" id="member-experiences-heading">
              Kinh nghiệm liên quan
            </h3>
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
              className="grid min-w-0 gap-3 rounded-xl border border-border bg-white p-4 md:grid-cols-2"
              key={`experience-${index}`}
            >
              <div className="flex flex-wrap items-center gap-2 md:col-span-2">
                <ContentOriginBadge
                  origin={experience.source_block_id ? "ai_generated" : "manual"}
                  aiLabel="Có nguồn dẫn chứng"
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
                Thời gian
                <input
                  className="apple-input mt-2"
                  value={experience.period || ""}
                  onChange={(event) =>
                    patchEvidenceAt(setExperiences, index, { period: event.target.value })
                  }
                  maxLength={120}
                  placeholder="Ví dụ: 2022–2024"
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
                    Có dẫn chứng nguồn
                    {experience.source_page_no ? `, trang ${experience.source_page_no}` : ""}
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
                aria-label={`Xóa kinh nghiệm ${index + 1}`}
                className="icon-button h-9 w-9 justify-self-start text-danger"
                title="Xóa kinh nghiệm"
                type="button"
                onClick={() =>
                  setExperiences((items) => items.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                <Trash2 aria-hidden="true" size={16} />
              </button>
            </div>
          ))}
        </section>

        <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
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
