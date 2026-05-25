import { StrictMode, useSyncExternalStore } from "react";
import { createRoot } from "react-dom/client";
import CadWorkspace from "./components/CadWorkspace";
import faviconUrl from "./app/favicon.png";
import "./app/globals.css";
import { getCadManifestSnapshot, subscribeCadManifest } from "./lib/cadManifestStore";
import { consumeCadWorkspacePersistenceResetRequest } from "./lib/workbench/persistence";

const ROOT_ID = "root";

function ensureFavicon() {
  if (typeof document === "undefined") {
    return;
  }

  let icon = document.querySelector('link[rel="icon"]');
  if (!icon) {
    icon = document.createElement("link");
    icon.rel = "icon";
    document.head.appendChild(icon);
  }
  icon.type = "image/png";
  icon.href = faviconUrl;
}

function bootstrap() {
  const rootElement = document.getElementById(ROOT_ID);
  if (!rootElement) {
    throw new Error(`Missing #${ROOT_ID} mount point.`);
  }
  ensureFavicon();
  consumeCadWorkspacePersistenceResetRequest();
  document.title = "CAD Explorer";
  createRoot(rootElement).render(
    <StrictMode>
      <AppRoot />
    </StrictMode>,
  );
}

function AppRoot() {
  const { manifest, revision } = useSyncExternalStore(
    subscribeCadManifest,
    getCadManifestSnapshot,
    getCadManifestSnapshot,
  );

  return (
    <CadWorkspace
      manifestRevision={revision}
      manifestEntries={manifest.entries}
      catalogRootName={manifest.root?.name}
    />
  );
}

bootstrap();
