export const PROJECTS_ROUTE = "/du-an";
export const OPERATIONS_ROUTE = "/van-hanh";

export const PROJECT_SECTION_SLUGS = Object.freeze({
  governance: "quan-tri-kiem-thu",
  testAnalysis: "phan-tich-kiem-thu",
  monitoring: "giam-sat-kiem-thu",
  projectTasks: "cong-viec",
  requirements: "yeu-cau",
  testDesign: "thiet-ke-kiem-thu",
  traceability: "truy-vet",
  changes: "thay-doi",
  execution: "thuc-thi",
  aiReview: "ra-soat-ai",
  defects: "loi",
  reports: "bao-cao",
  knowledge: "tri-thuc",
  settings: "cai-dat",
});

export function projectRoute(projectId, section = "", detailId = "") {
  const parts = [PROJECTS_ROUTE, encodeURIComponent(projectId)];
  if (section) parts.push(section);
  if (detailId) parts.push(encodeURIComponent(detailId));
  return parts.join("/");
}
