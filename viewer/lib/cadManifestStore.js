import initialCadCatalog from "virtual:cad-catalog";

const DEFAULT_CAD_DIRECTORY = "models";
const CAD_DIRECTORY_QUERY_PARAM = "dir";

function readCadDirectoryParam() {
  if (typeof window === "undefined") {
    return DEFAULT_CAD_DIRECTORY;
  }
  const params = new URLSearchParams(window.location.search);
  const value = String(params.get(CAD_DIRECTORY_QUERY_PARAM) || "").trim();
  return value || DEFAULT_CAD_DIRECTORY;
}

function normalizeCadDirectory(value = DEFAULT_CAD_DIRECTORY) {
  const rawValue = String(value || "").trim() || DEFAULT_CAD_DIRECTORY;
  return rawValue.replace(/\\/g, "/").replace(/^\/+/, "").replace(/\/+$/, "") || DEFAULT_CAD_DIRECTORY;
}

function normalizeCadManifest(manifest, fallbackDir = DEFAULT_CAD_DIRECTORY) {
  if (!manifest || typeof manifest !== "object") {
    const normalizedFallbackDir = normalizeCadDirectory(fallbackDir);
    return {
      schemaVersion: 3,
      root: {
        dir: normalizedFallbackDir,
        name: normalizedFallbackDir.split("/").filter(Boolean).pop() || normalizedFallbackDir,
        path: normalizedFallbackDir,
      },
      entries: [],
    };
  }

  const normalizedFallbackDir = normalizeCadDirectory(fallbackDir);
  return {
    ...manifest,
    root: manifest.root && typeof manifest.root === "object"
      ? manifest.root
      : {
          dir: normalizedFallbackDir,
          name: normalizedFallbackDir.split("/").filter(Boolean).pop() || normalizedFallbackDir,
          path: normalizedFallbackDir,
        },
    entries: Array.isArray(manifest.entries) ? manifest.entries : [],
  };
}

const listeners = new Set();
let currentSnapshot = {
  manifest: normalizeCadManifest(initialCadCatalog),
  revision: 0,
};
let refreshRequestId = 0;

function publishCadManifest(nextManifest) {
  currentSnapshot = {
    manifest: normalizeCadManifest(nextManifest, readCadDirectoryParam()),
    revision: currentSnapshot.revision + 1,
  };
  for (const listener of listeners) {
    listener();
  }
}

function currentSnapshotMatchesDirectory(dir = readCadDirectoryParam()) {
  return normalizeCadDirectory(currentSnapshot.manifest?.root?.dir) === normalizeCadDirectory(dir);
}

async function refreshCadCatalog() {
  if (typeof window === "undefined" || !import.meta.env.DEV) {
    return;
  }
  const requestId = ++refreshRequestId;
  const dir = readCadDirectoryParam();
  const response = await fetch(`/__cad/catalog?dir=${encodeURIComponent(dir)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Failed to scan CAD directory ${dir}: ${response.status} ${response.statusText}`);
  }
  const catalog = await response.json();
  if (requestId === refreshRequestId) {
    publishCadManifest(catalog);
  }
}

export function getCadManifestSnapshot() {
  return currentSnapshot;
}

export function subscribeCadManifest(listener) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

if (import.meta.hot) {
  import.meta.hot.accept("virtual:cad-catalog", (nextModule) => {
    publishCadManifest(nextModule?.default);
  });
  import.meta.hot.on("cad-catalog:changed", () => {
    refreshCadCatalog().catch((error) => {
      console.warn("Failed to refresh CAD catalog", error);
    });
  });
}

if (typeof window !== "undefined" && import.meta.env.DEV) {
  if (!currentSnapshotMatchesDirectory()) {
    refreshCadCatalog().catch((error) => {
      console.warn("Failed to load CAD catalog", error);
    });
  }
  window.addEventListener("popstate", () => {
    refreshCadCatalog().catch((error) => {
      console.warn("Failed to refresh CAD catalog", error);
    });
  });
}
