import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import {
  normalizeCadDirectory,
  scanCadDirectory,
} from "./cadDirectoryScanner.mjs";

function makeTempRepo() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "cad-explorer-scan-"));
}

function writeFile(filePath, content = "") {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, content);
}

function entryByFile(catalog, file) {
  return catalog.entries.find((entry) => entry.file === file);
}

test("scanCadDirectory discovers CAD files directly and infers STEP assets", () => {
  const repoRoot = makeTempRepo();
  writeFile(path.join(repoRoot, "models/sample_part/sample_part.step"), "ISO-10303-21;\nEND-ISO-10303-21;\n");
  writeFile(path.join(repoRoot, "models/sample_part/.sample_part.step/model.glb"), "glb");
  writeFile(path.join(repoRoot, "models/sample_part/.sample_part.step/topology.json"), JSON.stringify({
    schemaVersion: 2,
    assembly: { root: { nodeType: "assembly" } },
  }));
  writeFile(path.join(repoRoot, "models/sample_part/.sample_part.step/topology.bin"), "bin");
  writeFile(path.join(repoRoot, "models/sample_part/.sample_part.step/ignored.step"), "ignored\n");
  writeFile(path.join(repoRoot, "models/sample_part/sample_part.stl"), "solid sample_part\nendsolid sample_part\n");
  writeFile(path.join(repoRoot, "models/sheets/bracket.dxf"), "0\nEOF\n");
  writeFile(path.join(repoRoot, "models/robots/sample_robot.urdf"), "<robot name=\"sample_robot\" />\n");
  writeFile(path.join(repoRoot, "models/sample_part/sample_part.py"), "print('ignored')\n");

  const catalog = scanCadDirectory({ repoRoot, dir: "models" });

  assert.equal(catalog.root.dir, "models");
  assert.equal(entryByFile(catalog, "sample_part/sample_part.step").kind, "assembly");
  assert.equal(entryByFile(catalog, "sample_part/sample_part.step").cadPath, "models/sample_part/sample_part");
  assert.ok(entryByFile(catalog, "sample_part/sample_part.step").assets.glb.url.startsWith("/models/sample_part/.sample_part.step/model.glb?v="));
  assert.ok(entryByFile(catalog, "sample_part/sample_part.step").assets.topologyBinary.hash);
  assert.equal(entryByFile(catalog, "sample_part/sample_part.stl").kind, "stl");
  assert.equal(entryByFile(catalog, "sheets/bracket.dxf").kind, "dxf");
  assert.equal(entryByFile(catalog, "robots/sample_robot.urdf").kind, "urdf");
  assert.equal(entryByFile(catalog, "sample_part/sample_part.py"), undefined);
  assert.equal(entryByFile(catalog, "sample_part/.sample_part.step/ignored.step"), undefined);
});

test("scanCadDirectory uses the requested directory as the displayed root", () => {
  const repoRoot = makeTempRepo();
  writeFile(path.join(repoRoot, "models/imports/sample_part.step"), "ISO-10303-21;\nEND-ISO-10303-21;\n");

  const catalog = scanCadDirectory({ repoRoot, dir: "models/imports" });

  assert.equal(catalog.root.dir, "models/imports");
  assert.equal(catalog.root.name, "imports");
  assert.deepEqual(catalog.entries.map((entry) => entry.file), ["sample_part.step"]);
});

test("normalizeCadDirectory rejects traversal", () => {
  assert.equal(normalizeCadDirectory("models/samples"), "models/samples");
  assert.throws(() => normalizeCadDirectory("../models"), /inside the repository/);
});
