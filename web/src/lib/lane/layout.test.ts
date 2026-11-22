import { expect, test } from "vitest";
import { laneLayout } from "./layout";

test("1P puts scratch left, 2P right, skin proportions", () => {
  const l1 = laneLayout("1P", 576, 1000), l2 = laneLayout("2P", 576, 1000);
  expect(l1.lanes[0].lane).toBe("S"); expect(l2.lanes.at(-1)!.lane).toBe("S");
  const last = l1.lanes.at(-1)!; expect(l1.lanes[0].x).toBe(0); expect(last.x + last.w).toBeCloseTo(576);
  expect(l1.lanes[0].w).toBeCloseTo(120); expect(l1.lanes[1].x).toBeCloseTo(124);
  expect(l1.lanes.find(l => l.lane === "2")!.color).toBe("black");
  expect(laneLayout("1P", 288, 500).lanes[0].w).toBeCloseTo(60);
});

test("2P order and full width", () => {
  const l2 = laneLayout("2P", 576, 1000);
  expect(l2.lanes.map(l => l.lane)).toEqual(["1", "2", "3", "4", "5", "6", "7", "S"]);
  const last = l2.lanes.at(-1)!; expect(last.x + last.w).toBeCloseTo(576);
  expect(l2.judgeY).toBeCloseTo(880);
});
