// Generic, domain-agnostic formatting for the replay axis. A spec's `step` is a plain time-grain
// token (hour/day/…), NOT domain knowledge — these helpers only turn a frame index into a label.

const STEP_UNIT: Record<string, string> = {
  second: "秒",
  minute: "分钟",
  hour: "小时",
  day: "天",
  week: "周",
  month: "月",
  year: "年",
  frame: "帧",
};

export function stepUnit(step: string): string {
  return STEP_UNIT[step] ?? step;
}

// A label for one frame, relative to `now`: "现在" at now, "现在 −12 小时" / "现在 +3 小时" otherwise.
export function frameLabel(frame: number, now: number, step: string): string {
  const delta = frame - now;
  if (delta === 0) return "现在";
  const sign = delta > 0 ? "+" : "−"; // U+2212 MINUS SIGN for a clean typographic minus
  return `现在 ${sign}${Math.abs(delta)} ${stepUnit(step)}`;
}
