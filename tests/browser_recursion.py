#!/usr/bin/env python3
"""Run a staged Linux Orc against a loopback recursive browsing fixture.

Uses the actual bundled engine, two simultaneous workspace profiles, and
four document levels per workspace. All reports stay on the loopback
server. Each document must retain isolation, run a worker and Wasm, and
share a SAB with its worker. Cookies/storage must remain workspace-local.
A frame forbidden by X-Frame-Options must never execute its script.

Usage: python tests/browser_recursion.py /absolute/path/to/staged/orc
"""
import argparse
import http.server
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import tempfile
import threading
import time
from urllib.parse import parse_qs, urlsplit

DEPTH = 3
SCOPES = ("alpha", "beta")
FRAME = r'''<!doctype html><meta charset="utf-8"><title>Orc recursion probe</title>
<script>
(async () => {
  const query = new URLSearchParams(location.search);
  const depth = Number(query.get("depth"));
  const scope = query.get("scope");
  const report = {scope, depth, run: query.get("run")};
  try {
    if (depth === 0) {
      document.cookie = `orc_scope=${scope}; Max-Age=3600; SameSite=Strict; Path=/`;
      localStorage.setItem("orc_scope", scope);
      const blocked = document.createElement("iframe");
      blocked.src = "/blocked?" + query;
      document.body.append(blocked);
    }
    report.isolated = crossOriginIsolated;
    report.cookie = document.cookie;
    report.storage = localStorage.getItem("orc_scope");
    const shared = new SharedArrayBuffer(4);
    const values = new Int32Array(shared);
    values[0] = 41;
    const worker = new Worker("/worker.js");
    const result = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error("worker timed out")), 5000);
      worker.onmessage = event => { clearTimeout(timer); resolve(event.data); };
      worker.onerror = event => { clearTimeout(timer); reject(new Error(event.message)); };
      worker.postMessage(shared);
    });
    worker.terminate();
    report.worker = result;
    report.shared = Atomics.load(values, 0) === 42;
    if (depth < 3) {
      const child = document.createElement("iframe");
      query.set("depth", depth + 1);
      child.src = "/frame?" + query;
      document.body.append(child);
    }
  } catch (error) { report.error = String(error); }
  await fetch("/report", {method: "POST", body: JSON.stringify(report)});
})();
</script><body>Recursive fixture</body>'''
# Script runs after parsing the body so document.body always exists.
FRAME = FRAME.replace("(async () => {", 'addEventListener("DOMContentLoaded", async () => {').replace(
    "})();", "});")
WORKER = r'''onmessage = event => {
  // An actual Wasm add function, not just feature detection.
  const module = new WebAssembly.Module(new Uint8Array([
    0,97,115,109,1,0,0,0,1,7,1,96,2,127,127,1,127,
    3,2,1,0,7,7,1,3,97,100,100,0,0,
    10,9,1,7,0,32,0,32,1,106,11
  ]));
  const wasm = new WebAssembly.Instance(module).exports.add(20, 22);
  Atomics.add(new Int32Array(event.data), 0, 1);
  postMessage({isolated: crossOriginIsolated, wasm});
};'''


def run(launcher, timeout=40):
    if os.name != "posix":
        raise RuntimeError("this process-group smoke runner currently supports POSIX only")
    token = secrets.token_hex(16)
    reports = []
    blocked_requests = []
    lock = threading.Lock()
    ready = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, body, mime="text/html", blocked=False):
            body = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cache-Control", "no-store")
            if blocked:
                self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/worker.js":
                self.reply(WORKER, "text/javascript")
            elif path == "/blocked":
                query = parse_qs(urlsplit(self.path).query)
                with lock:
                    blocked_requests.append(query.get("scope", [""])[0])
                body = json.dumps(dict(run=query.get("run", [""])[0], forbidden=True))
                self.reply('<script>fetch("/report", {method:"POST",body:JSON.stringify(' + body + ')});</script>',
                           blocked=True)
            elif path == "/frame":
                self.reply(FRAME)
            else:
                self.send_error(404)

        def do_POST(self):
            if self.path != "/report":
                self.send_error(404)
                return
            size = int(self.headers.get("Content-Length", 0))
            if not 0 < size <= 8192:
                self.send_error(400)
                return
            report = json.loads(self.rfile.read(size))
            if report.get("run") != token:
                self.send_error(403)
                return
            with lock:
                reports.append(report)
                if len(reports) >= len(SCOPES) * (DEPTH + 1):
                    ready.set()
            self.reply("ok", "text/plain")

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    processes = []
    try:
        with tempfile.TemporaryDirectory(prefix="orc-browser-smoke-") as folder:
            root = Path(folder)
            env = dict(os.environ, HOME=folder, XDG_DATA_HOME=str(root / "data"))
            env.pop("ORC_WORKSPACE", None)
            env.pop("ORC_WORKSPACE_DEPTH", None)
            logfiles = []
            try:
                for scope in SCOPES:
                    log = (root / (scope + ".log")).open("wb")
                    logfiles.append(log)
                    url = (f"http://127.0.0.1:{server.server_port}/frame?"
                           f"run={token}&scope={scope}&depth=0")
                    process = subprocess.Popen(
                        [str(launcher), "--orc-workspace", "recursion/" + scope,
                         "--headless", "--new-window", url],
                        env=env, stdout=log, stderr=log, start_new_session=True)
                    processes.append(process)
                complete = ready.wait(timeout)
                # Give the intentionally forbidden frame time to reveal a failure.
                if complete:
                    time.sleep(0.5)
                with lock:
                    snapshot = list(reports)
                    blocked_snapshot = list(blocked_requests)
                for report in snapshot:
                    if report.get("forbidden") or report.get("error"):
                        raise AssertionError(f"recursive frame failure: {report}")
                    expected = dict(isolated=True, cookie="orc_scope=" + report["scope"],
                                    storage=report["scope"], shared=True,
                                    worker=dict(isolated=True, wasm=42))
                    for key, value in expected.items():
                        if report.get(key) != value:
                            raise AssertionError(f"{key}: expected {value!r}, received {report}")
                observed = sorted((r["scope"], r["depth"]) for r in snapshot)
                expected = sorted((scope, depth) for scope in SCOPES for depth in range(DEPTH + 1))
                if not complete or observed != expected:
                    logs = "\n".join((root / (s + ".log")).read_text(errors="replace")[-6000:]
                                     for s in SCOPES)
                    raise AssertionError(f"missing recursive documents: {observed}\n{logs}")
                if sorted(blocked_snapshot) != sorted(SCOPES):
                    raise AssertionError(f"forbidden frames were not requested: {blocked_snapshot}")
                print(json.dumps(dict(workspaces=len(SCOPES), levels=DEPTH + 1,
                                      documents=len(snapshot), isolated=True,
                                      worker_shared_memory=True, wasm=True,
                                      separate_storage=True, forbidden_frame_blocked=True)))
            finally:
                for process in processes:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                for process in processes:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
                for log in logfiles:
                    log.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("launcher", type=Path)
    parser.add_argument("--timeout", type=int, default=40)
    args = parser.parse_args()
    run(args.launcher.resolve(), args.timeout)
