import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSidebarDirectoryTree,
  selectedEntryKeyFromUrl,
  listSidebarItems,
  filenameLabelForEntry,
  normalizeCadFileQueryParam,
  normalizeCadRefQueryParams,
  sidebarDirectoryIdForEntry,
  sidebarLabelForEntry
} from "./sidebar.js";
import {
  readCadWorkspaceGlassTone,
  readCadWorkspaceSessionState,
  resetCadWorkspacePersistence,
  writeCadWorkspaceSessionState
} from "./persistence.js";
import { restoredSidebarWidthForViewport } from "../../components/workbench/hooks/useCadWorkspaceSession.js";

function createMemoryStorage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => {
      values.set(key, String(value));
    },
    removeItem: (key) => {
      values.delete(key);
    }
  };
}

test("filenameLabelForEntry shows canonical step, stl, dxf, and urdf suffixes", () => {
  assert.equal(
    filenameLabelForEntry({
      file: "sample_mount.step",
      kind: "part",
      source: { format: "step", path: "parts/sample_mount.step" }
    }),
    "sample_mount.step"
  );

  assert.equal(
    filenameLabelForEntry({
      file: "sample_assembly.step",
      kind: "assembly",
      source: { format: "step", path: "assemblies/sample_assembly.step" }
    }),
    "sample_assembly.step"
  );

  assert.equal(
    filenameLabelForEntry({
      file: "imports/vendor/widget.stp",
      kind: "part",
      source: { format: "stp", path: "imports/vendor/widget.stp" },
      step: { path: "imports/vendor/widget.stp" }
    }),
    "widget.stp"
  );

  assert.equal(
    filenameLabelForEntry({
      file: "sample_robot.urdf",
      kind: "urdf",
      source: { format: "urdf", path: "sample_robot.urdf" },
      name: "sample_robot (URDF)"
    }),
    "sample_robot.urdf"
  );

  assert.equal(
    filenameLabelForEntry({
      file: "sample_plate.dxf",
      kind: "dxf",
      source: { format: "dxf", path: "drawings/sample_plate.dxf" }
    }),
    "sample_plate.dxf"
  );

  assert.equal(
    filenameLabelForEntry({
      file: "fixtures/bracket.stl",
      kind: "stl",
      source: { format: "stl", path: "fixtures/bracket.stl" }
    }),
    "bracket.stl"
  );
});

test("sidebarLabelForEntry uses the same suffix-aware filename labels", () => {
  const entry = {
    file: "sample_assembly.step",
    kind: "assembly",
    source: { format: "step", path: "assemblies/sample_assembly.step" }
  };

  assert.equal(sidebarLabelForEntry(entry), "sample_assembly.step");
});

test("sidebarDirectoryIdForEntry keeps exact CAD file folders", () => {
  assert.equal(
    sidebarDirectoryIdForEntry({
      file: "parts/sample_plate.step",
      kind: "part",
      source: { format: "step", path: "parts/sample_plate.step" }
    }),
    "parts"
  );

  assert.equal(
    sidebarDirectoryIdForEntry({
      file: "drawings/sample_plate.dxf",
      kind: "dxf",
      source: { format: "dxf", path: "drawings/sample_plate.dxf" }
    }),
    "drawings"
  );

  assert.equal(
    sidebarDirectoryIdForEntry({
      file: "sample_robot.urdf",
      kind: "urdf",
      source: { format: "urdf", path: "sample_robot.urdf" }
    }),
    ""
  );

  assert.equal(
    sidebarDirectoryIdForEntry({
      file: "meshes/fixture.stl",
      kind: "stl",
      source: { format: "stl", path: "meshes/fixture.stl" }
    }),
    "meshes"
  );

  assert.equal(
    sidebarDirectoryIdForEntry({
      file: "parts/mount.step",
      kind: "part",
      source: { format: "step", path: "parts/mount.step" }
    }),
    "parts"
  );
});

test("buildSidebarDirectoryTree lists CAD files in their exact source directory", () => {
  const tree = buildSidebarDirectoryTree([
    {
      file: "parts/sample_plate.step",
      kind: "part",
      source: { format: "step", path: "parts/sample_plate.step" }
    },
    {
      file: "drawings/sample_plate.dxf",
      kind: "dxf",
      source: { format: "dxf", path: "drawings/sample_plate.dxf" }
    }
  ]);

  const partsDirectory = tree.directories.find((directory) => directory.id === "parts");
  assert.ok(partsDirectory);
  const drawingsDirectory = tree.directories.find((directory) => directory.id === "drawings");
  assert.ok(drawingsDirectory);
  assert.deepEqual(
    [
      ...listSidebarItems(drawingsDirectory).map((item) => `${item.type}:${item.label}`),
      ...listSidebarItems(partsDirectory).map((item) => `${item.type}:${item.label}`),
    ],
    ["entry:sample_plate.dxf", "entry:sample_plate.step"]
  );
});

test("workspace global state persists expanded directories and URDF entry animation preference", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    localStorage: createMemoryStorage(),
    sessionStorage: createMemoryStorage()
  };

  try {
    writeCadWorkspaceSessionState({
      openTabs: [],
      selectedKey: "",
      query: "sample",
      expandedDirectoryIds: ["parts", "parts/imports", "parts"],
      sidebarOpen: false,
      sidebarWidth: 312,
      tabToolsWidth: 344,
      urdfEntryAnimationEnabled: false
    });

    const restoredSession = readCadWorkspaceSessionState();

    assert.deepEqual(
      restoredSession.expandedDirectoryIds,
      ["parts", "parts/imports"]
    );
    assert.equal(restoredSession.query, "sample");
    assert.equal(restoredSession.urdfEntryAnimationEnabled, false);
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("workspace global state migrates legacy default panel widths", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    localStorage: createMemoryStorage(),
    sessionStorage: createMemoryStorage()
  };

  try {
    writeCadWorkspaceSessionState({
      openTabs: [],
      selectedKey: "",
      sidebarWidth: 300,
      tabToolsWidth: 300
    });

    const restoredSession = readCadWorkspaceSessionState();

    assert.equal(restoredSession.sidebarWidth, 260);
    assert.equal(restoredSession.tabToolsWidth, 260);
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("workspace desktop restore resets auto-collapsed sidebar width", () => {
  assert.equal(
    restoredSidebarWidthForViewport(
      { sidebarOpen: true, sidebarWidth: 150 },
      { desktopViewport: true, defaultSidebarWidth: 260, sidebarMinWidth: 150 }
    ),
    260
  );
  assert.equal(
    restoredSidebarWidthForViewport(
      { sidebarOpen: false, sidebarWidth: 420 },
      { desktopViewport: true, defaultSidebarWidth: 260, sidebarMinWidth: 150 }
    ),
    260
  );
  assert.equal(
    restoredSidebarWidthForViewport(
      { sidebarOpen: true, sidebarWidth: 420 },
      { desktopViewport: true, defaultSidebarWidth: 260, sidebarMinWidth: 150 }
    ),
    420
  );
  assert.equal(
    restoredSidebarWidthForViewport(
      { sidebarOpen: false, sidebarWidth: 150 },
      { desktopViewport: false, defaultSidebarWidth: 260, sidebarMinWidth: 150 }
    ),
    150
  );
});

test("workspace global state defaults URDF entry animation preference to enabled", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    localStorage: createMemoryStorage(),
    sessionStorage: createMemoryStorage()
  };

  try {
    writeCadWorkspaceSessionState({
      openTabs: [],
      selectedKey: "",
      query: ""
    });

    const restoredSession = readCadWorkspaceSessionState();
    assert.equal(restoredSession.urdfEntryAnimationEnabled, true);
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("workspace glass tone defaults to cinematic dark tone", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    localStorage: createMemoryStorage(),
    sessionStorage: createMemoryStorage()
  };

  try {
    assert.equal(readCadWorkspaceGlassTone(), "dark");
    globalThis.window.localStorage.setItem("cad-explorer:workbench-glass-tone:v1", "light");
    assert.equal(readCadWorkspaceGlassTone(), "light");
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("resetCadWorkspacePersistence removes current CAD Explorer keys", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    localStorage: createMemoryStorage(),
    sessionStorage: createMemoryStorage()
  };

  try {
    globalThis.window.localStorage.setItem("cad-explorer:workbench-global:v1", "{}");
    globalThis.window.localStorage.setItem("cad-explorer:look-settings", "{}");
    globalThis.window.localStorage.setItem("cad-explorer-theme", "dark");
    globalThis.window.localStorage.setItem("cad-explorer:workbench-glass-tone:v1", "dark");
    globalThis.window.sessionStorage.setItem("cad-explorer:workbench-session:v2", "{}");
    globalThis.window.sessionStorage.setItem("cad-explorer:dxf-bend-overrides:v1", "{}");

    assert.equal(resetCadWorkspacePersistence(), true);

    assert.equal(globalThis.window.localStorage.getItem("cad-explorer:workbench-global:v1"), null);
    assert.equal(globalThis.window.localStorage.getItem("cad-explorer:look-settings"), null);
    assert.equal(globalThis.window.localStorage.getItem("cad-explorer-theme"), null);
    assert.equal(globalThis.window.localStorage.getItem("cad-explorer:workbench-glass-tone:v1"), null);
    assert.equal(globalThis.window.sessionStorage.getItem("cad-explorer:workbench-session:v2"), null);
    assert.equal(globalThis.window.sessionStorage.getItem("cad-explorer:dxf-bend-overrides:v1"), null);
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("normalizeCadRefQueryParams accepts canonical models refs", () => {
  assert.deepEqual(
    normalizeCadRefQueryParams(["models/parts/sample_plate#f2", "@cad[models/parts/sample_base#e1]", "parts/ignored#f1"]),
    ["@cad[models/parts/sample_plate#f2]", "@cad[models/parts/sample_base#e1]"]
  );
});

test("selectedEntryKeyFromUrl restores the selected file query param", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    location: {
      search: "?file=parts%2Fsample_plate.step"
    }
  };

  try {
    assert.equal(
      selectedEntryKeyFromUrl([
        {
          file: "parts/sample_base.step",
          cadPath: "models/parts/sample_base",
          kind: "part"
        },
        {
          file: "parts/sample_plate.step",
          cadPath: "models/parts/sample_plate",
          kind: "part"
        }
      ]),
      "parts/sample_plate.step"
    );
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("selectedEntryKeyFromUrl accepts repo-relative file params inside the active CAD directory", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    location: {
      search: "?dir=models&file=models%2Fparts%2Fsample_plate.step"
    }
  };

  try {
    assert.equal(
      selectedEntryKeyFromUrl([
        {
          file: "parts/sample_base.step",
          cadPath: "models/parts/sample_base",
          kind: "part"
        },
        {
          file: "parts/sample_plate.step",
          cadPath: "models/parts/sample_plate",
          kind: "part"
        }
      ]),
      "parts/sample_plate.step"
    );
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});

test("normalizeCadFileQueryParam keeps scan-relative file params unchanged", () => {
  assert.equal(normalizeCadFileQueryParam("parts/sample_plate.step", "models"), "parts/sample_plate.step");
  assert.equal(normalizeCadFileQueryParam("models/parts/sample_plate.step", "models"), "parts/sample_plate.step");
  assert.equal(normalizeCadFileQueryParam("models/imports/widget.step", "models/imports"), "widget.step");
});

test("selectedEntryKeyFromUrl restores the selected canonical ref query param", () => {
  const originalWindow = globalThis.window;
  globalThis.window = {
    location: {
      search: "?refs=models%2Fparts%2Fsample_plate%23f2"
    }
  };

  try {
    assert.equal(
      selectedEntryKeyFromUrl([
        {
          file: "parts/sample_base.step",
          cadPath: "models/parts/sample_base",
          kind: "part"
        },
        {
          file: "parts/sample_plate.step",
          cadPath: "models/parts/sample_plate",
          kind: "part"
        }
      ]),
      "parts/sample_plate.step"
    );
  } finally {
    if (originalWindow === undefined) {
      delete globalThis.window;
    } else {
      globalThis.window = originalWindow;
    }
  }
});
