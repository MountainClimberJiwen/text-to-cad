import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import {
  DEFAULT_CAD_DIRECTORY,
  isCatalogRelevantPath,
  isServedCadAsset,
  normalizeCadDirectory,
  repoRelativePath,
  resolveCadDirectory,
  scanCadDirectory,
} from "./lib/cadDirectoryScanner.mjs";

const DEFAULT_VIEWER_PORT = 4178;
const resolvedPort = Number.parseInt(process.env.VIEWER_PORT || process.env.GUI_PORT || process.env.PORT || "", 10);
const viewerPort = Number.isFinite(resolvedPort) ? resolvedPort : DEFAULT_VIEWER_PORT;
const viewerRoot = process.cwd();
const repoRoot = path.resolve(viewerRoot, "..");
const buildCadDir = normalizeCadDirectory(process.env.CAD_DIR || DEFAULT_CAD_DIRECTORY);

function emptyCatalog(dir = DEFAULT_CAD_DIRECTORY) {
  const normalizedDir = normalizeCadDirectory(dir);
  return {
    schemaVersion: 3,
    root: {
      dir: normalizedDir,
      name: path.basename(normalizedDir) || normalizedDir,
      path: normalizedDir,
    },
    entries: [],
  };
}

function readCadCatalog(dir = buildCadDir) {
  try {
    return scanCadDirectory({ repoRoot, dir });
  } catch {
    return emptyCatalog(dir);
  }
}

function pathIsInside(childPath, parentPath) {
  const relativePath = path.relative(path.resolve(parentPath), path.resolve(childPath));
  return Boolean(relativePath) && !relativePath.startsWith("..") && !path.isAbsolute(relativePath);
}

function serveStaticFile(root, requestUrl, res, next, { allow } = {}) {
  const requestPath = String(requestUrl || "").replace(/\?.*$/, "");
  let decodedRequestPath = "";
  try {
    decodedRequestPath = decodeURIComponent(requestPath);
  } catch {
    res.statusCode = 400;
    res.end("Bad request");
    return true;
  }
  const filePath = path.resolve(root, decodedRequestPath.replace(/^\/+/, ""));
  if (
    !(filePath === path.resolve(root) || pathIsInside(filePath, root))
    || (typeof allow === "function" && !allow(filePath))
  ) {
    res.statusCode = 403;
    res.end("Forbidden");
    return true;
  }
  fs.stat(filePath, (error, stats) => {
    if (error || !stats.isFile()) {
      next();
      return;
    }
    fs.createReadStream(filePath).pipe(res);
  });
  return true;
}

function copyRecursiveFiltered(sourceRoot, destinationRoot, predicate) {
  if (!fs.existsSync(sourceRoot)) {
    return;
  }
  for (const entry of fs.readdirSync(sourceRoot, { withFileTypes: true })) {
    const sourcePath = path.join(sourceRoot, entry.name);
    const destinationPath = path.join(destinationRoot, entry.name);
    if (entry.isDirectory()) {
      copyRecursiveFiltered(sourcePath, destinationPath, predicate);
      continue;
    }
    if (!predicate(sourcePath)) {
      continue;
    }
    fs.mkdirSync(path.dirname(destinationPath), { recursive: true });
    fs.copyFileSync(sourcePath, destinationPath);
  }
}

function sendJson(res, statusCode, payload) {
  res.statusCode = statusCode;
  res.setHeader("content-type", "application/json; charset=utf-8");
  res.setHeader("cache-control", "no-store");
  res.end(JSON.stringify(payload));
}

function cadCatalogPlugin() {
  const virtualId = "virtual:cad-catalog";
  const resolvedVirtualId = `\0${virtualId}`;
  let resolvedConfig = null;
  const activeDirectories = new Map();
  const refreshTimers = new Map();

  function activateDirectory(server, dir) {
    const resolved = resolveCadDirectory(repoRoot, dir);
    activeDirectories.set(resolved.rootPath, resolved.dir);
    server.watcher.add(resolved.rootPath);
    return resolved;
  }

  function scheduleCatalogRefresh(server, rootPath, dir) {
    if (refreshTimers.has(rootPath)) {
      clearTimeout(refreshTimers.get(rootPath));
    }
    refreshTimers.set(rootPath, setTimeout(() => {
      refreshTimers.delete(rootPath);
      server.ws.send({
        type: "custom",
        event: "cad-catalog:changed",
        data: { dir },
      });
    }, 150));
  }

  function notifyChangedPath(server, changedPath) {
    const resolvedChangedPath = path.resolve(changedPath);
    if (!isCatalogRelevantPath(resolvedChangedPath)) {
      return;
    }
    for (const [rootPath, dir] of activeDirectories.entries()) {
      if (resolvedChangedPath === rootPath || pathIsInside(resolvedChangedPath, rootPath)) {
        scheduleCatalogRefresh(server, rootPath, dir);
      }
    }
  }

  return {
    name: "cad-catalog",
    configResolved(config) {
      resolvedConfig = config;
    },
    resolveId(id) {
      if (id === virtualId) {
        return resolvedVirtualId;
      }
      return null;
    },
    load(id) {
      if (id !== resolvedVirtualId) {
        return null;
      }
      const catalog = readCadCatalog(buildCadDir);
      return `export default ${JSON.stringify(catalog)};`;
    },
    configureServer(server) {
      activateDirectory(server, buildCadDir);
      server.middlewares.use((req, res, next) => {
        const requestUrl = new URL(req.url || "/", "http://localhost");
        if (requestUrl.pathname !== "/__cad/catalog") {
          next();
          return;
        }
        const dir = requestUrl.searchParams.get("dir") || DEFAULT_CAD_DIRECTORY;
        let catalog;
        try {
          const resolved = activateDirectory(server, dir);
          catalog = scanCadDirectory({ repoRoot, dir: resolved.dir });
        } catch (error) {
          sendJson(res, 400, {
            error: error instanceof Error ? error.message : String(error),
          });
          return;
        }
        sendJson(res, 200, catalog);
      });
      server.middlewares.use((req, res, next) => {
        const requestPath = String(req.url || "").replace(/\?.*$/, "");
        let decodedRequestPath = "";
        try {
          decodedRequestPath = decodeURIComponent(requestPath);
        } catch {
          next();
          return;
        }
        const candidatePath = path.resolve(repoRoot, decodedRequestPath.replace(/^\/+/, ""));
        if (!isServedCadAsset(candidatePath)) {
          next();
          return;
        }
        serveStaticFile(repoRoot, req.url, res, next, {
          allow: (filePath) => (
            isServedCadAsset(filePath) &&
            (filePath === repoRoot || pathIsInside(filePath, repoRoot))
          ),
        });
      });
      for (const eventName of ["add", "change", "unlink"]) {
        server.watcher.on(eventName, (changedPath) => notifyChangedPath(server, changedPath));
      }
    },
    writeBundle() {
      const outDir = resolvedConfig?.build?.outDir || "dist";
      const resolved = resolveCadDirectory(repoRoot, buildCadDir);
      const cadDestinationRoot = path.resolve(viewerRoot, outDir, repoRelativePath(repoRoot, resolved.rootPath));
      copyRecursiveFiltered(resolved.rootPath, cadDestinationRoot, (filePath) => {
        return isServedCadAsset(filePath);
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), cadCatalogPlugin()],
  resolve: {
    alias: {
      "@": viewerRoot,
    },
  },
  esbuild: {
    loader: "jsx",
    include: /.*\.[jt]sx?$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        ".js": "jsx",
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 800,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) {
            return undefined;
          }
          if (id.includes("/three/")) {
            return "vendor-three";
          }
          if (id.includes("/react/") || id.includes("/react-dom/")) {
            return "vendor-react";
          }
          if (id.includes("/radix-ui/") || id.includes("/@radix-ui/")) {
            return "vendor-ui";
          }
          if (id.includes("/lucide-react/")) {
            return "vendor-icons";
          }
          return undefined;
        },
      },
    },
  },
  server: {
    host: "127.0.0.1",
    port: viewerPort,
    strictPort: true,
  },
  preview: {
    host: "127.0.0.1",
    port: viewerPort,
    strictPort: true,
  },
});
