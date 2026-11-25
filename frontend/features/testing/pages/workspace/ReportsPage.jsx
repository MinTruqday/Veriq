"use client";

import SimpleTestReports from "../../components/SimpleTestReports";
import { ProjectCrumb, WorkspacePage } from "../../components/WorkspacePrimitives";

export default function ReportsPage({ project }) {
  return (
    <WorkspacePage title="Báo cáo" actions={<ProjectCrumb projectId={project._id} />}>
      <SimpleTestReports project={project} />
    </WorkspacePage>
  );
}
