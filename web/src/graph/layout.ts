// Fixed, semantic positions on a 1200×720 canvas (design §7.1). No automatic layout: where a node sits
// says what it is. Edge paths are computed here too, so back-edges route above and below the bench.

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export const CANVAS = { width: 1200, height: 720 };
export const NODE = { w: 176, h: 64 };

export const BANDS = {
  vendor: { x: 0, y: 110, w: 220, h: 490, label: "The vendor's word" },
  bench: { x: 380, y: 110, w: 400, h: 490, label: "The bench" },
  records: { x: 920, y: 110, w: 240, h: 490, label: "The company's records" },
  reasoning: { x: 380, y: 0, w: 780, h: 90, label: "Reasoning engine" },
  ruling: { x: 0, y: 620, w: 1160, h: 100, label: "The ruling" },
};

const FIXED: Record<string, { x: number; y: number; w?: number; h?: number }> = {
  "vendor.answers": { x: 22, y: 190 },
  "vendor.documents": { x: 22, y: 300 },
  "vendor.components": { x: 22, y: 410 },
  guard: { x: 244, y: 300, w: 120 },
  evidence: { x: 400, y: 190 },
  evaluator: { x: 596, y: 190 },
  planner: { x: 400, y: 330 },
  challenger: { x: 596, y: 470 },
  clash: { x: 586, y: 296, w: 196, h: 140 },
  usl: { x: 952, y: 120 },
  "rec.procurement": { x: 952, y: 210 },
  "rec.clm": { x: 952, y: 290 },
  "rec.itsm": { x: 952, y: 370 },
  "rec.grc": { x: 952, y: 450 },
  "rec.kev": { x: 952, y: 530 },
  engine: { x: 400, y: 14, h: 56 },
  policy: { x: 22, y: 636 },
  memory: { x: 254, y: 636 },
  reporter: { x: 486, y: 636 },
  contract: { x: 718, y: 636 },
  outcome: { x: 952, y: 636 },
};

/** Position of any node id; model nodes line up along the reasoning band in order of first use. */
export function rectFor(id: string, modelOrder: string[] = []): Rect {
  const fixed = FIXED[id];
  if (fixed) return { x: fixed.x, y: fixed.y, w: fixed.w ?? NODE.w, h: fixed.h ?? NODE.h };
  if (id.startsWith("model:")) {
    const k = Math.max(0, modelOrder.indexOf(id));
    return { x: 610 + k * 190, y: 14, w: NODE.w, h: 56 };
  }
  if (id.startsWith("rec.")) {
    // A system the design does not name: below the known records.
    return { x: 952, y: 610 - NODE.h, w: NODE.w, h: NODE.h };
  }
  return { x: 400, y: 560, w: NODE.w, h: NODE.h };
}

const mid = (r: Rect) => ({ cx: r.x + r.w / 2, cy: r.y + r.h / 2 });

function bezier(x1: number, y1: number, x2: number, y2: number, horizontal: boolean): string {
  if (horizontal) {
    const dx = Math.max(30, Math.abs(x2 - x1) / 2);
    const s = x2 >= x1 ? 1 : -1;
    return `M ${x1} ${y1} C ${x1 + dx * s} ${y1}, ${x2 - dx * s} ${y2}, ${x2} ${y2}`;
  }
  const dy = Math.max(30, Math.abs(y2 - y1) / 2);
  const s = y2 >= y1 ? 1 : -1;
  return `M ${x1} ${y1} C ${x1} ${y1 + dy * s}, ${x2} ${y2 - dy * s}, ${x2} ${y2}`;
}

function rounded(points: [number, number][], r = 12): string {
  let d = `M ${points[0][0]} ${points[0][1]}`;
  for (let k = 1; k < points.length - 1; k++) {
    const [px, py] = points[k - 1];
    const [x, y] = points[k];
    const [nx, ny] = points[k + 1];
    const inLen = Math.hypot(x - px, y - py) || 1;
    const outLen = Math.hypot(nx - x, ny - y) || 1;
    const rr = Math.min(r, inLen / 2, outLen / 2);
    d += ` L ${x - ((x - px) / inLen) * rr} ${y - ((y - py) / inLen) * rr}`;
    d += ` Q ${x} ${y} ${x + ((nx - x) / outLen) * rr} ${y + ((ny - y) / outLen) * rr}`;
  }
  const last = points[points.length - 1];
  return `${d} L ${last[0]} ${last[1]}`;
}

export interface EdgeGeometry {
  path: string;
  labelX: number;
  labelY: number;
}

/** Forward edges take the short way; send-backs arc above the bench, re-plans below it. */
export function edgeGeometry(type: "forward" | "sendback" | "replan" | "thread", a: Rect, b: Rect): EdgeGeometry {
  const A = mid(a);
  const B = mid(b);
  if (type === "sendback") {
    const top = BANDS.bench.y + 2;
    const left = b.x - 16;
    const pts: [number, number][] = [
      [A.cx, a.y],
      [A.cx, top],
      [left, top],
      [left, B.cy - 10],
      [b.x, B.cy - 10],
    ];
    return { path: rounded(pts), labelX: (A.cx + left) / 2, labelY: top };
  }
  if (type === "replan") {
    const bottom = BANDS.bench.y + BANDS.bench.h - 4;
    const left = b.x - 28;
    const pts: [number, number][] = [
      [A.cx, a.y + a.h],
      [A.cx, bottom],
      [left, bottom],
      [left, B.cy + 10],
      [b.x, B.cy + 10],
    ];
    return { path: rounded(pts), labelX: (A.cx + left) / 2, labelY: bottom };
  }
  const horizontalGap = b.x > a.x + a.w ? b.x - (a.x + a.w) : a.x > b.x + b.w ? a.x - (b.x + b.w) : -1;
  if (horizontalGap >= 0) {
    const forwardRight = b.x > a.x;
    const x1 = forwardRight ? a.x + a.w : a.x;
    const x2 = forwardRight ? b.x : b.x + b.w;
    return { path: bezier(x1, A.cy, x2, B.cy, true), labelX: (x1 + x2) / 2, labelY: (A.cy + B.cy) / 2 };
  }
  const down = b.y > a.y;
  const y1 = down ? a.y + a.h : a.y;
  const y2 = down ? b.y : b.y + b.h;
  return { path: bezier(A.cx, y1, B.cx, y2, false), labelX: (A.cx + B.cx) / 2, labelY: (y1 + y2) / 2 };
}
