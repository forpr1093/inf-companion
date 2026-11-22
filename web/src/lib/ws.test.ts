import { afterEach, expect, test, vi } from "vitest";
import { connect } from "./ws";

class FakeWS {
  static instances: FakeWS[] = [];
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  sent: string[] = [];
  readyState = 0;
  constructor(public url: string) { FakeWS.instances.push(this); }
  send(s: string) { this.sent.push(s); }
  close() { this.readyState = 3; this.onclose?.(); }
  open() { this.readyState = 1; this.onopen?.(); }
  message(obj: object) { this.onmessage?.({ data: JSON.stringify(obj) }); }
}

afterEach(() => { FakeWS.instances = []; vi.useRealTimers(); });

test("ws client reconnects and emits reset", async () => {
  vi.useFakeTimers();
  const events: string[] = [];
  connect("ws://x/ws", {
    onEvent: e => events.push(e.type),
    onStatus: s => events.push(s),
    onReset: () => events.push("reset"),
  }, { WebSocketImpl: FakeWS as unknown as typeof WebSocket, backoffMs: [10] });
  const s = FakeWS.instances;
  s[0].open(); s[0].message({ type: "hello" }); s[0].close();
  await vi.advanceTimersByTimeAsync(10);
  s[1].open();
  expect(events).toEqual(["connecting", "open", "reset", "hello", "closed", "connecting", "open", "reset"]);
});

test("send only when open, close stops reconnecting", async () => {
  vi.useFakeTimers();
  const c = connect("ws://x/ws", { onEvent() {}, onStatus() {}, onReset() {} },
    { WebSocketImpl: FakeWS as unknown as typeof WebSocket, backoffMs: [10] });
  c.send({ type: "bind_start" });
  expect(FakeWS.instances[0].sent).toEqual([]);
  FakeWS.instances[0].open();
  c.send({ type: "bind_start" });
  expect(FakeWS.instances[0].sent).toEqual(['{"type":"bind_start"}']);
  c.close();
  await vi.advanceTimersByTimeAsync(100);
  expect(FakeWS.instances.length).toBe(1);
});

test("bad json is ignored", () => {
  const got: string[] = [];
  connect("ws://x/ws", { onEvent: e => got.push(e.type), onStatus() {}, onReset() {} },
    { WebSocketImpl: FakeWS as unknown as typeof WebSocket });
  const w = FakeWS.instances[0];
  w.open();
  w.onmessage?.({ data: "{nope" });
  w.message({ type: "key_down" });
  expect(got).toEqual(["key_down"]);
});
