import assert from "node:assert/strict";
import test from "node:test";
import {
  formatProjectDate,
  invalidProjectDateRange,
  invalidTimelineRange,
  minimumProjectEndDate,
} from "./projectSchedule.logic.mjs";

test("ngày kết thúc tối thiểu là ngày sau ngày bắt đầu, kể cả khi qua tháng hoặc năm", () => {
  assert.equal(minimumProjectEndDate("2026-10-26"), "2026-10-27");
  assert.equal(minimumProjectEndDate("2026-01-31"), "2026-02-01");
  assert.equal(minimumProjectEndDate("2026-12-31"), "2027-01-01");
  assert.equal(minimumProjectEndDate("not-a-date"), undefined);
});

test("khoảng thời gian dự án phải có ngày kết thúc sau ngày bắt đầu", () => {
  assert.equal(invalidProjectDateRange("2026-10-26", "2026-10-26"), true);
  assert.equal(invalidProjectDateRange("2026-10-27", "2026-10-26"), true);
  assert.equal(invalidProjectDateRange("2026-10-26", "2026-10-27"), false);
  assert.equal(invalidProjectDateRange("", "2026-10-27"), false);
});

test("lộ trình đánh dấu khoảng công việc và Sprint cùng ngày là không hợp lệ, còn bản phát hành được phép cùng ngày", () => {
  const start = new Date("2026-10-26T00:00:00.000Z");
  const sameDay = new Date("2026-10-26T00:00:00.000Z");
  const nextDay = new Date("2026-10-27T00:00:00.000Z");

  assert.equal(invalidTimelineRange(start, sameDay), true);
  assert.equal(invalidTimelineRange(start, sameDay, true), false);
  assert.equal(invalidTimelineRange(start, nextDay), false);
  assert.equal(invalidTimelineRange(nextDay, start), true);
  assert.equal(invalidTimelineRange(null, nextDay), false);
});

test("ngày dự án được hiển thị theo ngày lịch UTC và không tự dịch ngày", () => {
  assert.equal(formatProjectDate("2026-10-26T00:00:00.000Z"), "26/10/2026");
  assert.equal(formatProjectDate("2026-02-30T00:00:00.000Z"), "Ngày không hợp lệ");
  assert.equal(formatProjectDate(null), "Chưa đặt");
});
