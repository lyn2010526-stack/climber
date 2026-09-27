/**
 * Deterministic fixture server for the performance baseline.
 *
 * The server is the single source of truth for the app's API state. Scenarios
 * program it before the run (message counts, stream pacing) and read the
 * recorded request log afterwards, so a run's inputs and the traffic they
 * produced stay in one place.
 *
 * A real `text/event-stream` is served from `/api/v1/sessions/:id/chat`:
 * `page.route` can fulfil a body but cannot pace it, and pacing is the whole
 * point of the render-bound measurement — 50ms and 16ms framing have to come
 * from a clock, not from a loop the page controls.
 */
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const DIST = path.resolve(HERE, '../../dist');

const MIME: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
};

export interface StreamConfig {
  /** Text frames emitted before the terminal done frame. */
  chunks: number;
  /** Delay between frames, in ms. */
  delayMs: number;
  /** Deterministic per-frame token body. */
  token: string;
  /** Emit tool_call / tool_result frames halfway through. */
  withToolFrames: boolean;
  /** Wall-clock ceiling so a stuck stream cannot hang a run. */
  maxDurationMs: number;
}

export interface SessionFixture {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

/** Programmable app state. Scenarios mutate this before driving the page. */
export interface FixtureState {
  session: SessionFixture;
  sessions: SessionFixture[];
  /** Serialized `{ messages: [...] }` returned to the app. */
  messagesPayload: string;
  /** Message ids the app was told exist, for assertions. */
  messageCount: number;
  stream: StreamConfig;
}

export interface FixtureServer {
  port: number;
  baseUrl: string;
  state: FixtureState;
  /** Every API path the app requested, in order. */
  requestLog: Array<{ method: string; path: string; at: number }>;
  /** Frames actually written to the chat stream. */
  streamFramesWritten: number;
  close: () => Promise<void>;
}

function defaultState(): FixtureState {
  return {
    session: { id: 'perf-session-1', title: 'Perf session', status: 'idle', created_at: new Date(0).toISOString() },
    sessions: [],
    messagesPayload: JSON.stringify({ messages: [] }),
    messageCount: 0,
    stream: { chunks: 5, delayMs: 50, token: 'tok', withToolFrames: false, maxDurationMs: 120_000 },
  };
}

function textFrame(index: number, token: string): string {
  return `event: text\ndata: ${JSON.stringify({ content: `${token}${index} ` })}\n\n`;
}

function toolFrames(): string[] {
  return [
    `event: tool_call\ndata: ${JSON.stringify({ id: 'tc-1', name: 'ledger_query', arguments: { range: '2026-01', limit: 50 } })}\n\n`,
    `event: tool_result\ndata: ${JSON.stringify({ id: 'tc-1', result: JSON.stringify({ rows: 50, elapsed_ms: 9 }) })}\n\n`,
  ];
}

function serveStatic(res: http.ServerResponse, pathname: string) {
  let file = path.join(DIST, pathname === '/' ? 'index.html' : pathname);
  if (!file.startsWith(DIST)) file = path.join(DIST, 'index.html');
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(DIST, 'index.html');
  res.writeHead(200, {
    'Content-Type': MIME[path.extname(file)] ?? 'application/octet-stream',
    'Cache-Control': 'no-store',
  });
  res.end(fs.readFileSync(file));
}

function serveStream(
  req: http.IncomingMessage,
  res: http.ServerResponse,
  config: StreamConfig,
  onFrame: () => void,
) {
  res.writeHead(200, {
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  let index = 0;
  let closed = false;
  const started = Date.now();
  const timer = setInterval(() => {
    if (closed) return;
    if (Date.now() - started > config.maxDurationMs) {
      closed = true; clearInterval(timer); res.end(); return;
    }
    if (config.withToolFrames && index === Math.floor(config.chunks / 2)) {
      for (const frame of toolFrames()) { res.write(frame); onFrame(); }
    }
    if (index >= config.chunks) {
      closed = true; clearInterval(timer);
      res.write(`event: done\ndata: ${JSON.stringify({ message_id: 'assistant-perf-1' })}\n\n`);
      onFrame();
      res.end();
      return;
    }
    res.write(textFrame(index, config.token));
    onFrame();
    index += 1;
  }, config.delayMs);

  req.on('close', () => { closed = true; clearInterval(timer); });
}

export function startFixtureServer(port = 0): Promise<FixtureServer> {
  const state = defaultState();
  state.sessions = [state.session];
  const requestLog: FixtureServer['requestLog'] = [];
  let framesWritten = 0;

  const server = http.createServer((req, res) => {
    const url = new URL(req.url ?? '/', 'http://localhost');
    const method = req.method ?? 'GET';

    if (url.pathname.startsWith('/api/v1')) {
      requestLog.push({ method, path: url.pathname, at: Date.now() });

      if (url.pathname.endsWith('/chat')) {
        serveStream(req, res, state.stream, () => { framesWritten += 1; });
        return;
      }
      if (url.pathname.endsWith('/messages')) {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
        res.end(state.messagesPayload);
        return;
      }
      if (/\/api\/v1\/sessions\/?$/.test(url.pathname)) {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
        res.end(method === 'POST' ? JSON.stringify(state.session) : JSON.stringify(state.sessions));
        return;
      }
      if (url.pathname === '/api/v1/auth/me') {
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
        res.end(JSON.stringify({ id: 'perf-owner', username: 'perf', role: 'user' }));
        return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
      res.end('{}');
      return;
    }

    serveStatic(res, url.pathname);
  });

  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => {
      const address = server.address();
      const bound = typeof address === 'object' && address ? address.port : port;
      resolve({
        port: bound,
        baseUrl: `http://127.0.0.1:${bound}`,
        state,
        requestLog,
        get streamFramesWritten() { return framesWritten; },
        close: () => new Promise<void>((done) => server.close(() => done())),
      });
    });
  });
}
