"use client";

import AgentRunPanel from "../../components/AgentRunPanel";
import { ProjectCrumb, WorkspacePage } from "../../components/WorkspacePrimitives";

export default function ReviewQueuePage({ project }) {
  return (
    <WorkspacePage title="Hoạt động AI" actions={<ProjectCrumb projectId={project._id} />}>
      <AgentRunPanel project={project} showDefinitions={false} />
    </WorkspacePage>
  );
}
