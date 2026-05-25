import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";

const VIEWER_HOST = "127.0.0.1";
const VIEWER_PORT = 4178;
const HEALTH_PATH = "/__cad/catalog?dir=models";
const HEALTH_URL = `http://${VIEWER_HOST}:${VIEWER_PORT}${HEALTH_PATH}`;
const VIEWER_URL = `http://${VIEWER_HOST}:${VIEWER_PORT}`;
const PROBE_TIMEOUT_MS = 1000;
const STARTUP_TIMEOUT_MS = 30000;
const POLL_INTERVAL_MS = 250;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function probeViewer() {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);

  try {
    const response = await fetch(HEALTH_URL, {
      signal: controller.signal,
      cache: "no-store",
    });
    if (!response.ok) {
      return false;
    }
    const catalog = await response.json();
    return catalog?.root?.dir === "models" && Array.isArray(catalog?.entries);
  } catch {
    return false;
  } finally {
    clearTimeout(timeout);
  }
}

async function waitForViewer() {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (await probeViewer()) {
      return true;
    }
    await sleep(POLL_INTERVAL_MS);
  }
  return false;
}

async function main() {
  if (await probeViewer()) {
    console.log(`CAD Explorer is already running at ${VIEWER_URL}`);
    return;
  }

  const scriptPath = fileURLToPath(import.meta.url);
  const viewerRoot = path.resolve(path.dirname(scriptPath), "..");
  const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";

  console.log(`Starting CAD Explorer dev server at ${VIEWER_URL}`);
  const child = spawn(npmCommand, ["run", "dev"], {
    cwd: viewerRoot,
    detached: true,
    env: {
      ...process.env,
      VIEWER_PORT: String(VIEWER_PORT),
    },
    stdio: "ignore",
  });
  child.unref();

  if (await waitForViewer()) {
    console.log(`CAD Explorer is ready at ${VIEWER_URL}`);
    return;
  }

  console.error(`CAD Explorer did not become ready at ${HEALTH_URL} within ${STARTUP_TIMEOUT_MS}ms.`);
  process.exitCode = 1;
}

await main();
