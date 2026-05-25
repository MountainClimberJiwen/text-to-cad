import fs from "node:fs";
import path from "node:path";

export const DEFAULT_CAD_DIRECTORY = "models";

const SOURCE_EXTENSIONS = new Set([".step", ".stp", ".stl", ".dxf", ".urdf"]);
const SKIPPED_DIRECTORIES = new Set([".git", ".cache", ".viewer", "__pycache__", "node_modules"]);
const VIEWER_ARTIFACT_FILENAMES = new Set(["model.glb", "topology.json", "topology.bin"]);

function toPosixPath(value) {
  return String(value || "").split(path.sep).join("/");
}

function encodeUrlPath(repoRelativePath) {
  return `/${repoRelativePath.split("/").map((part) => encodeURIComponent(part)).join("/")}`;
}

export function normalizeCadDirectory(value = DEFAULT_CAD_DIRECTORY) {
  const rawValue = String(value || "").trim() || DEFAULT_CAD_DIRECTORY;
  const slashNormalized = rawValue.replace(/\\/g, "/").replace(/^\/+/, "");
  const normalized = path.posix.normalize(slashNormalized);
  if (!normalized || normalized === ".") {
    return DEFAULT_CAD_DIRECTORY;
  }
  if (normalized === ".." || normalized.startsWith("../")) {
    throw new Error(`CAD directory must stay inside the repository: ${rawValue}`);
  }
  return normalized.replace(/\/+$/, "");
}

export function resolveCadDirectory(repoRoot, dir = DEFAULT_CAD_DIRECTORY) {
  const normalizedDir = normalizeCadDirectory(dir);
  const resolvedRepoRoot = path.resolve(repoRoot);
  const rootPath = path.resolve(resolvedRepoRoot, normalizedDir);
  const relativePath = path.relative(resolvedRepoRoot, rootPath);
  if (relativePath.startsWith("..") || path.isAbsolute(relativePath)) {
    throw new Error(`CAD directory must stay inside the repository: ${normalizedDir}`);
  }
  return {
    dir: normalizedDir,
    rootPath,
    rootName: path.basename(rootPath) || normalizedDir,
  };
}

export function repoRelativePath(repoRoot, filePath) {
  return toPosixPath(path.relative(path.resolve(repoRoot), path.resolve(filePath)));
}

function scanRelativePath(rootPath, filePath) {
  return toPosixPath(path.relative(path.resolve(rootPath), path.resolve(filePath)));
}

function fileStats(filePath) {
  try {
    const stats = fs.statSync(filePath, { bigint: true });
    return stats.isFile() ? stats : null;
  } catch {
    return null;
  }
}

function fileVersion(filePath) {
  const stats = fileStats(filePath);
  if (!stats) {
    return "";
  }
  return `${stats.size.toString(36)}-${stats.mtimeNs.toString(36)}`;
}

function assetForPath(repoRoot, filePath) {
  const version = fileVersion(filePath);
  if (!version) {
    return null;
  }
  const repoPath = repoRelativePath(repoRoot, filePath);
  return {
    url: `${encodeUrlPath(repoPath)}?v=${encodeURIComponent(version)}`,
    hash: version,
  };
}

function readJsonObject(filePath) {
  try {
    const payload = JSON.parse(fs.readFileSync(filePath, "utf8"));
    return payload && typeof payload === "object" && !Array.isArray(payload) ? payload : null;
  } catch {
    return null;
  }
}

function stepKindFromTopology(topologyPath) {
  const topology = readJsonObject(topologyPath);
  return topology?.assembly?.root && typeof topology.assembly.root === "object"
    ? "assembly"
    : "part";
}

function sourceFormatFromExtension(extension) {
  const normalized = extension.toLowerCase().replace(/^\./, "");
  return normalized === "stp" ? "stp" : normalized;
}

function isPerStepViewerDirectoryName(name) {
  const normalized = String(name || "").toLowerCase();
  return normalized.startsWith(".") && (normalized.endsWith(".step") || normalized.endsWith(".stp"));
}

function isPathInsidePerStepViewerDirectory(filePath) {
  return String(filePath || "")
    .split(path.sep)
    .some((part) => isPerStepViewerDirectoryName(part));
}

function fileRefForSource(rootPath, sourcePath) {
  return scanRelativePath(rootPath, sourcePath);
}

function cadPathForStepSource(repoRoot, sourcePath, extension) {
  const relativePath = repoRelativePath(repoRoot, sourcePath);
  return relativePath.slice(0, -extension.length);
}

function createStepEntry({ repoRoot, rootPath, sourcePath, extension }) {
  const viewerDir = path.join(path.dirname(sourcePath), `.${path.basename(sourcePath)}`);
  const glbPath = path.join(viewerDir, "model.glb");
  const topologyPath = path.join(viewerDir, "topology.json");
  const topologyBinaryPath = path.join(viewerDir, "topology.bin");
  const assets = {};

  for (const [key, assetPath] of [
    ["glb", glbPath],
    ["topology", topologyPath],
    ["topologyBinary", topologyBinaryPath],
  ]) {
    const asset = assetForPath(repoRoot, assetPath);
    if (asset) {
      assets[key] = asset;
    }
  }

  const sourceRelPath = fileRefForSource(rootPath, sourcePath);
  return {
    file: fileRefForSource(rootPath, sourcePath),
    cadPath: cadPathForStepSource(repoRoot, sourcePath, extension),
    kind: stepKindFromTopology(topologyPath),
    name: path.basename(sourcePath),
    source: {
      kind: "file",
      format: sourceFormatFromExtension(extension),
      path: sourceRelPath,
    },
    assets,
    step: {
      path: sourceRelPath,
      hash: fileVersion(sourcePath),
    },
  };
}

function createSingleAssetEntry({ repoRoot, rootPath, sourcePath, extension }) {
  const kind = sourceFormatFromExtension(extension);
  const asset = assetForPath(repoRoot, sourcePath);
  const assets = asset ? { [kind]: asset } : {};
  return {
    file: fileRefForSource(rootPath, sourcePath),
    kind,
    name: path.basename(sourcePath),
    source: {
      kind: "file",
      format: kind,
      path: repoRelativePath(repoRoot, sourcePath),
    },
    assets,
  };
}

function shouldSkipDirectory(name) {
  return SKIPPED_DIRECTORIES.has(name) || isPerStepViewerDirectoryName(name);
}

function collectCadSourceFiles(rootPath, result = []) {
  let entries = [];
  try {
    entries = fs.readdirSync(rootPath, { withFileTypes: true });
  } catch {
    return result;
  }

  for (const entry of entries) {
    const entryPath = path.join(rootPath, entry.name);
    if (entry.isDirectory()) {
      if (!shouldSkipDirectory(entry.name)) {
        collectCadSourceFiles(entryPath, result);
      }
      continue;
    }
    if (!entry.isFile()) {
      continue;
    }
    const extension = path.extname(entry.name).toLowerCase();
    if (SOURCE_EXTENSIONS.has(extension)) {
      result.push(entryPath);
    }
  }
  return result;
}

function compareEntries(a, b) {
  return String(a.file || "").localeCompare(String(b.file || ""), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

export function scanCadDirectory({ repoRoot, dir = DEFAULT_CAD_DIRECTORY } = {}) {
  if (!repoRoot) {
    throw new Error("repoRoot is required");
  }
  const resolved = resolveCadDirectory(repoRoot, dir);
  const entries = collectCadSourceFiles(resolved.rootPath)
    .map((sourcePath) => {
      const extension = path.extname(sourcePath).toLowerCase();
      if (extension === ".step" || extension === ".stp") {
        return createStepEntry({
          repoRoot,
          rootPath: resolved.rootPath,
          sourcePath,
          extension,
        });
      }
      return createSingleAssetEntry({
        repoRoot,
        rootPath: resolved.rootPath,
        sourcePath,
        extension,
      });
    })
    .sort(compareEntries);

  return {
    schemaVersion: 3,
    root: {
      dir: resolved.dir,
      name: resolved.rootName,
      path: resolved.dir,
    },
    entries,
  };
}

export function isServedCadAsset(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (SOURCE_EXTENSIONS.has(extension)) {
    return true;
  }
  if (!isPathInsidePerStepViewerDirectory(filePath)) {
    return false;
  }
  return extension === ".glb" || VIEWER_ARTIFACT_FILENAMES.has(path.basename(filePath));
}

export function isCatalogRelevantPath(filePath) {
  return isServedCadAsset(filePath);
}
