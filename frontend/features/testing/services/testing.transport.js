import { API_URL, authenticatedFetch } from "@/shared/services/api-client";

function responseErrorMessage(response, body, fallback) {
  if (body?.error?.message) return body.error.message;
  if (response.status >= 500)
    return `Máy chủ gặp lỗi khi xử lý yêu cầu (HTTP ${response.status}). Vui lòng thử lại.`;
  return fallback;
}

function refreshProjectAccessAfterDenial(path, status, errorDetails = null, errorCode = "") {
  const projectPermissionDenied =
    errorCode === "PROJECT_PERMISSION_DENIED" && typeof errorDetails?.permission === "string";
  const membershipDenied =
    errorCode === "PROJECT_MEMBERSHIP_REQUIRED" ||
    errorCode === "PROJECT_MEMBERSHIP_INACTIVE" ||
    errorCode === "PROJECT_ARCHIVED_READ_DENIED";
  if (
    status !== 403 ||
    (!projectPermissionDenied && !membershipDenied) ||
    typeof window === "undefined"
  )
    return;
  const projectIdFromPath =
    path.match(/\/du-an\/([^/?]+)(?=\/|\?|$)/)?.[1] ||
    window.location.pathname.match(/\/du-an\/([^/?]+)(?=\/|$)/)?.[1];
  let projectId = projectIdFromPath;
  if (!projectId && typeof errorDetails?.project_id === "string")
    projectId = errorDetails.project_id;
  if (!projectId) return;
  window.dispatchEvent(
    new CustomEvent("veriq-project-access-denied", {
      detail: {
        projectId: decodeURIComponent(projectId),
        pagePath: window.location.pathname,
        permission: errorDetails?.permission || null,
        code: errorCode,
      },
    }),
  );
}

export async function testingRequest(path, options = {}) {
  const response = await authenticatedFetch(`${API_URL}/kiem-thu${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    refreshProjectAccessAfterDenial(path, response.status, body?.error?.details, body?.error?.code);
    const error = new Error(responseErrorMessage(response, body, "Không thể hoàn tất yêu cầu"));
    error.status = response.status;
    error.code = body?.error?.code;
    error.details = body?.error?.details;
    error.traceId = body?.trace_id;
    throw error;
  }
  return body?.data;
}

export async function testingImageRequest(path) {
  const response = await authenticatedFetch(`${API_URL}/kiem-thu${path}`, {
    headers: { Accept: "image/png" },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    refreshProjectAccessAfterDenial(path, response.status, body?.error?.details, body?.error?.code);
    const error = new Error(responseErrorMessage(response, body, "Không thể tải ảnh nguồn"));
    error.status = response.status;
    error.code = body?.error?.code;
    error.traceId = body?.trace_id;
    throw error;
  }
  if (response.headers.get("content-type")?.split(";")[0]?.trim() !== "image/png") {
    throw new Error("Ảnh nguồn trả về định dạng không được hỗ trợ");
  }
  return response.blob();
}

export async function automationRequest(path, options = {}) {
  const response = await authenticatedFetch(`${API_URL}/tu-dong-hoa-ai${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    refreshProjectAccessAfterDenial(path, response.status, body?.detail, body?.detail?.code);
    const detail = body?.detail;
    const error = new Error(detail?.message || detail?.code || "Không thể hoàn tất tự động hóa AI");
    error.status = response.status;
    error.code = detail?.code;
    error.details = detail?.latest;
    throw error;
  }
  return body;
}

export async function inferenceRequest(path, options = {}) {
  const response = await authenticatedFetch(`${API_URL}/suy-luan${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const error = new Error(
      typeof detail === "string"
        ? detail
        : detail?.message || detail?.code || "Không thể hoàn tất yêu cầu đánh giá AI",
    );
    error.status = response.status;
    error.code = detail?.code;
    error.traceId = body?.trace_id;
    throw error;
  }
  return body?.data ?? body;
}

export async function testingStreamRequest(path, options = {}) {
  const { onDelta, ...requestOptions } = options;
  const streamId = crypto.randomUUID();
  const notify = (status, message = "") => {
    window.dispatchEvent(
      new CustomEvent("veriq-ai-stream", {
        detail: { id: streamId, path, status, message },
      }),
    );
  };
  const response = await authenticatedFetch(`${API_URL}/kiem-thu${path}`, {
    ...requestOptions,
    headers: {
      ...(requestOptions.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      Accept: "text/event-stream",
      ...requestOptions.headers,
    },
  });
  const messageOf = (body, fallback) =>
    body?.error?.message ||
    body?.detail?.message ||
    body?.detail?.code ||
    body?.error?.code ||
    body?.detail ||
    fallback;
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => null);
    refreshProjectAccessAfterDenial(
      path,
      response.status,
      body?.error?.details || body?.detail,
      body?.error?.code || body?.detail?.code,
    );
    const error = new Error(messageOf(body, "Không thể hoàn tất yêu cầu AI"));
    error.status = response.status;
    error.code = body?.error?.code || body?.detail?.code;
    error.details = body?.error?.details || body?.detail?.details;
    notify("failed", error.message);
    throw error;
  }
  notify("streaming");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result;
  const consume = (rawEvent) => {
    const data = rawEvent
      .split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) return;
    const event = JSON.parse(data);
    if (event.type === "delta") {
      const delta = event.delta || "";
      onDelta?.(delta);
      notify("streaming");
    }
    if (event.type === "result") result = event.data;
    if (event.type === "error") {
      const body = event.data;
      const error = new Error(messageOf(body, event.code || "Không thể hoàn tất yêu cầu AI"));
      error.status = event.status || response.status;
      error.code = body?.error?.code || body?.detail?.code || event.code;
      error.details = body?.error?.details || body?.detail?.details;
      refreshProjectAccessAfterDenial(
        path,
        error.status,
        body?.error?.details || body?.detail,
        error.code,
      );
      throw error;
    }
  };
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    buffer = buffer.replaceAll("\r\n", "\n");
    const events = buffer.split("\n\n");
    buffer = events.pop() || "";
    for (const rawEvent of events) {
      try {
        consume(rawEvent);
      } catch (error) {
        notify("failed", error.message);
        throw error;
      }
    }
    if (done) {
      if (buffer.trim()) {
        try {
          consume(buffer);
        } catch (error) {
          notify("failed", error.message);
          throw error;
        }
      }
      break;
    }
  }
  if (!result) {
    notify("failed", "Luồng AI kết thúc nhưng không trả về kết quả");
    throw new Error("Luồng AI kết thúc nhưng không trả về kết quả");
  }
  notify("complete");
  return result?.data;
}

export async function downloadTestingFile(path, filename) {
  const response = await authenticatedFetch(`${API_URL}/kiem-thu${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    refreshProjectAccessAfterDenial(path, response.status, body?.error?.details, body?.error?.code);
    throw new Error(body?.error?.message || "Không thể tải tệp");
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export async function readTestingFile(path) {
  const response = await authenticatedFetch(`${API_URL}/kiem-thu${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    refreshProjectAccessAfterDenial(path, response.status, body?.error?.details, body?.error?.code);
    throw new Error(body?.error?.message || "Không thể mở tệp");
  }
  return URL.createObjectURL(await response.blob());
}

export function listQuery(value) {
  if (!value) return "";
  if (typeof value === "string") return `q=${encodeURIComponent(value)}`;
  if (value instanceof URLSearchParams) return value.toString();
  const query = new URLSearchParams();
  Object.entries(value).forEach(([key, item]) => {
    if (item !== "" && item !== null && item !== undefined) query.set(key, String(item));
  });
  return query.toString();
}

export async function listPage(path, value) {
  const query = listQuery(value);
  const result = await testingRequest(`${path}${query ? `?${query}` : ""}`);
  if (Array.isArray(result)) {
    return {
      items: result,
      page: 1,
      page_size: result.length,
      total: result.length,
      total_pages: result.length ? 1 : 0,
    };
  }
  return result;
}
