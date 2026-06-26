import { describe, expect, it } from "vitest";
import { frameLabel, stepUnit } from "./time";

describe("stepUnit", () => {
  it("maps known time grains to a label", () => {
    expect(stepUnit("hour")).toBe("小时");
    expect(stepUnit("day")).toBe("天");
    expect(stepUnit("frame")).toBe("帧");
  });
  it("passes unknown grains through unchanged (domain-agnostic)", () => {
    expect(stepUnit("fortnight")).toBe("fortnight");
  });
});

describe("frameLabel", () => {
  it("labels the now frame", () => {
    expect(frameLabel(36, 36, "hour")).toBe("现在");
  });
  it("labels past frames with a minus offset", () => {
    expect(frameLabel(24, 36, "hour")).toBe("现在 −12 小时");
  });
  it("labels future frames with a plus offset", () => {
    expect(frameLabel(39, 36, "hour")).toBe("现在 +3 小时");
  });
  it("uses the spec's step grain", () => {
    expect(frameLabel(20, 22, "day")).toBe("现在 −2 天");
  });
});
