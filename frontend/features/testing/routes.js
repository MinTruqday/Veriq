export const PROJECTS_ROUTE = "/du-an";
export const OPERATIONS_ROUTE = "/van-hanh";

export const PROJECT_SECTION_SLUGS = Object.freeze({
  governance: "quan-tri-kiem-thu",
  testAnalysis: "phan-tich-kiem-thu",
  monitoring: "giam-sat-kiem-thu",
  projectTasks: "cong-viec",
  planning: "lap-ke-hoach",
  releases: "ban-phat-hanh",
  requirements: "yeu-cau",
  assurance: "ho-so-dam-bao",
  clarifications: "phieu-lam-ro",
  testDesign: "thiet-ke-kiem-thu",
  testRepository: "kho-kiem-thu",
  testCases: "ca-kiem-thu",
  reusableSteps: "buoc-dung-lai",
  testData: "du-lieu-kiem-thu",
  testSets: "bo-kiem-thu",
  testPlans: "ke-hoach-kiem-thu",
  testRuns: "lan-chay-kiem-thu",
  automation: "tu-dong-hoa",
  traceability: "truy-vet",
  changes: "thay-doi",
  execution: "thuc-thi",
  aiReview: "ra-soat-ai",
  defects: "loi",
  reports: "bao-cao",
  audit: "nhat-ky-kiem-toan",
  knowledge: "tri-thuc",
  settings: "cai-dat",
});

export function projectRoute(projectId, section = "", detailId = "") {
  const parts = [PROJECTS_ROUTE, encodeURIComponent(projectId)];
  if (section) parts.push(section);
  if (detailId) parts.push(encodeURIComponent(detailId));
  return parts.join("/");
}
