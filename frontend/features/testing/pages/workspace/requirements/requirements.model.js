import { docText, emptyDoc, textDoc } from "../../../lib/testing";

export const REQUIREMENT_TYPES = [
  "functional",
  "non_functional",
  "business_rule",
  "api",
  "ui",
  "data",
  "permission",
  "integration",
  "constraint",
];

export const REQUIREMENT_LEVELS = ["critical", "high", "medium", "low"];

export const REQUIREMENT_IMPORT_FORMATS = ["md", "txt", "csv", "openapi", "postman"];

export const REQUIREMENT_SOURCE_TYPE_OPTIONS = [
  { value: "SRS", label: "Đặc tả yêu cầu phần mềm" },
  { value: "BRD", label: "Tài liệu yêu cầu nghiệp vụ" },
  { value: "USER_STORY", label: "Câu chuyện người dùng" },
  { value: "ACCEPTANCE_CRITERIA", label: "Tiêu chí chấp nhận" },
  { value: "BUSINESS_RULE", label: "Quy tắc nghiệp vụ" },
  { value: "API_SPEC", label: "Đặc tả giao diện lập trình ứng dụng" },
  { value: "UI_SPEC", label: "Đặc tả giao diện người dùng" },
  { value: "ARCHITECTURE", label: "Kiến trúc" },
  { value: "MEETING_NOTE", label: "Biên bản họp" },
  { value: "RELEASE_NOTE", label: "Ghi chú phát hành" },
  { value: "BUG_HISTORY", label: "Lịch sử lỗi" },
  { value: "TEST_ARTIFACT", label: "Tài sản kiểm thử" },
  { value: "REGULATION", label: "Quy định" },
  { value: "REFERENCE", label: "Tài liệu tham chiếu" },
  { value: "OTHER", label: "Nguồn khác" },
];

export const REQUIREMENT_SOURCE_AUTHORITY_OPTIONS = [
  { value: "APPROVED_SOURCE", label: "Đã được phê duyệt" },
  { value: "CONTROLLED_SOURCE", label: "Được quản lý chính thức" },
  { value: "PROJECT_REFERENCE", label: "Tài liệu tham chiếu của dự án" },
  { value: "SUPPLEMENTAL", label: "Tài liệu bổ sung" },
  { value: "DRAFT", label: "Bản nháp" },
  { value: "UNVERIFIED", label: "Chưa xác minh" },
];

export const REQUIREMENT_SOURCE_APPROVAL_OPTIONS = [
  { value: "DRAFT", label: "Bản nháp" },
  { value: "IN_REVIEW", label: "Đang rà soát" },
  { value: "APPROVED", label: "Đã phê duyệt" },
  { value: "REJECTED", label: "Từ chối" },
];

export const REQUIREMENT_STATUS_FILTERS = [
  { value: "", label: "Mọi trạng thái" },
  { value: "DRAFT", label: "Bản nháp" },
  { value: "IN_REVIEW", label: "Đang rà soát" },
  { value: "BASELINED", label: "Đã phê duyệt" },
  { value: "SUPERSEDED", label: "Đã được thay thế" },
  { value: "OBSOLETE", label: "Không còn hiệu lực" },
];

export const REQUIREMENT_COVERAGE_FILTERS = [
  { value: "", label: "Mọi độ phủ" },
  { value: "covered", label: "Đã phủ" },
  { value: "uncovered", label: "Chưa phủ" },
];

export const REQUIREMENT_SORT_OPTIONS = [
  { value: "-updated_at", label: "Mới cập nhật" },
  { value: "updated_at", label: "Cũ cập nhật" },
  { value: "requirement_key", label: "Mã tăng dần" },
  { value: "title", label: "Tên tăng dần" },
];

export function parseCommaValues(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function createInitialRequirementForm() {
  return {
    customValues: {},
    title: "",
    type: "functional",
    priority: "medium",
    risk: "medium",
    content_doc: emptyDoc(),
    acceptance: "",
    businessRules: "",
    actors: "",
    dependencies: "",
    tags: "",
    ownerId: "",
  };
}

export function splitRequirementBlocks(value) {
  return value
    .split(/\n\s*---\s*\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function parseAcceptanceCriteria(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean)
    .map((item, index) => ({
      key: `AC-${index + 1}`,
      content_doc: textDoc(item),
      status: "draft",
    }));
}

export function requirementSuggestionPreview(item) {
  const values = [];
  if (item.revised_title) values.push(["Tên", item.revised_title]);
  if (item.revised_content) values.push(["Nội dung", item.revised_content]);
  if (item.patch?.actors) values.push(["Tác nhân", item.patch.actors.join(" · ")]);
  if (item.patch?.business_rules) {
    values.push(["Quy tắc nghiệp vụ", item.patch.business_rules.join(" · ")]);
  }
  if (item.patch?.acceptance_criteria) {
    values.push([
      "Tiêu chí chấp nhận",
      item.patch.acceptance_criteria
        .map((criterion) => `${criterion.key} ${docText(criterion.content_doc)}`)
        .join(" · "),
    ]);
  }
  if (item.patch?.dependencies) {
    values.push(["Phụ thuộc", item.patch.dependencies.join(" · ")]);
  }
  return values;
}

export function requirementFieldLabel(value) {
  return {
    title: "Tên",
    content: "Nội dung",
    actors: "Tác nhân",
    business_rules: "Quy tắc nghiệp vụ",
    acceptance_criteria: "Tiêu chí chấp nhận",
    dependencies: "Phụ thuộc",
  }[value];
}
