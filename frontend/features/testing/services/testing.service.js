import { designTestingApi } from "./testing.design";
import { executionTestingApi } from "./testing.execution";
import { projectTestingApi } from "./testing.projects";
import { qualityTestingApi } from "./testing.quality";

export {
  agentReadRequest,
  agentRequest,
  downloadTestingFile,
  testingRequest,
  testingStreamRequest,
} from "./testing.transport";

export const testingApi = {
  ...projectTestingApi,
  ...designTestingApi,
  ...executionTestingApi,
  ...qualityTestingApi,
};
