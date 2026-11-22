import type { ServerEvent } from "./events";

export type Status = "connecting" | "open" | "closed";

export interface Handlers {
  onEvent(e: ServerEvent): void;
  onStatus(s: Status): void;
  onReset(): void;
}

export interface Options { WebSocketImpl?: typeof WebSocket; backoffMs?: number[]; }

/** Connect with automatic reconnect. `onReset` fires on every (re)open, before `hello`. */
export function connect(url: string, handlers: Handlers, opts: Options = {}) {
  const Impl = opts.WebSocketImpl ?? WebSocket;
  const backoff = opts.backoffMs ?? [500, 1000, 2000, 5000];
  let ws: WebSocket | null = null;
  let attempt = 0;
  let closedByUser = false;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const open = () => {
    handlers.onStatus("connecting");
    const sock = new Impl(url);
    ws = sock;
    sock.onopen = () => {
      attempt = 0;
      handlers.onStatus("open");
      handlers.onReset();
    };
    sock.onmessage = (m: MessageEvent | { data: string }) => {
      let e: ServerEvent;
      try { e = JSON.parse(String(m.data)); } catch { return; }
      if (e && typeof e === "object" && typeof (e as { type?: unknown }).type === "string") handlers.onEvent(e);
    };
    sock.onclose = () => {
      if (ws !== sock) return;
      ws = null;
      handlers.onStatus("closed");
      if (closedByUser) return;
      const delay = backoff[Math.min(attempt, backoff.length - 1)];
      attempt += 1;
      timer = setTimeout(open, delay);
    };
    sock.onerror = () => { /* onclose follows */ };
  };
  open();

  return {
    send(msg: object) {
      if (ws && ws.readyState === 1) ws.send(JSON.stringify(msg));
    },
    close() {
      closedByUser = true;
      if (timer) clearTimeout(timer);
      ws?.close();
    },
  };
}
