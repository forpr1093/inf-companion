import { expect, test } from "vitest";
import { bindPrompt, sourceText } from "./bindText";

test("prompts for keys and both scratch directions", () => {
  expect(bindPrompt("3")).toBe("Press key 3");
  expect(bindPrompt("S_up")).toBe("Spin the turntable one way (scratch up)");
  expect(bindPrompt("S_down")).toBe("Spin it the other way (scratch down)");
});

test("describes a bound source", () => {
  expect(sourceText({ kind: "button", index: 4, sign: 0, mask: 0 })).toBe("button 5");
  expect(sourceText({ kind: "axis", index: 0, sign: -1, mask: 0 })).toBe("axis 1 −");
  expect(sourceText({ kind: "hat", index: 0, sign: 0, mask: 4 })).toBe("hat 1 (4)");
  expect(sourceText(undefined)).toBe("not bound");
});
