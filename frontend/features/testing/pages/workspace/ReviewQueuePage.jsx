"use client";

import AIRunPanel from "../../components/AIRunPanel";
import { ProjectCrumb, WorkspacePage } from "../../components/WorkspacePrimitives";

export default function ReviewQueuePage({ project }) {
  return (
    <WorkspacePage title="Hoạt động AI" actions={<ProjectCrumb projectId={project._id} />}>
      <AIRunPanel project={project} showPanelHeading={false} />
    </WorkspacePage>
  );
}
