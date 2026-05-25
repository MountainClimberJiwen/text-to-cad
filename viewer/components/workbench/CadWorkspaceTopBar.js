import { Fragment } from "react";
import { Palette, PanelRightIcon } from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbEllipsis,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { SidebarTrigger, useSidebar } from "@/components/ui/sidebar";

function pathSegmentsForEntry(entry, fallbackLabel) {
  if (!entry) {
    return [fallbackLabel];
  }

  const sourcePath = String(entry.source?.path || entry.step?.path || entry.id || "").trim();
  const segments = sourcePath
    ? sourcePath.replace(/\\/g, "/").split("/").filter(Boolean)
    : [];

  if (!segments.length) {
    return [fallbackLabel];
  }

  return [
    ...segments.slice(0, -1),
    fallbackLabel
  ];
}

function collapsedBreadcrumbSegments(segments) {
  if (segments.length <= 3) {
    return segments.map((segment) => ({ type: "segment", label: segment }));
  }

  return [
    { type: "segment", label: segments[0] },
    { type: "ellipsis", label: "..." },
    ...segments.slice(-2).map((segment) => ({ type: "segment", label: segment }))
  ];
}

function fileSheetLabel(fileSheetKind) {
  if (fileSheetKind === "dxf") {
    return "DXF sheet";
  }
  if (fileSheetKind === "urdf") {
    return "URDF sheet";
  }
  if (fileSheetKind === "stepAssembly") {
    return "assembly sheet";
  }
  return "file sheet";
}

export default function CadWorkspaceTopBar({
  previewMode,
  lookMenuOpen,
  sidebarLabelForEntry,
  selectedEntry,
  setLookMenuOpen,
  fileSheetKind = "",
  fileSheetOpen = false,
  onToggleFileSheet
}) {
  const { isMobile, state: sidebarState } = useSidebar();

  if (previewMode) {
    return null;
  }

  const selectedFileLabel = selectedEntry ? sidebarLabelForEntry(selectedEntry) : "Select a file";
  const selectedFileTitle = selectedEntry
    ? String(selectedEntry.source?.path || selectedEntry.step?.path || selectedEntry.id || selectedFileLabel)
    : selectedFileLabel;
  const breadcrumbSegments = pathSegmentsForEntry(selectedEntry, selectedFileLabel);
  const breadcrumbItems = collapsedBreadcrumbSegments(breadcrumbSegments);
  const activeIconButtonClasses = "bg-accent text-accent-foreground";
  const showFileSheetToggle = !!fileSheetKind && typeof onToggleFileSheet === "function";
  const lookSheetToggleLabel = lookMenuOpen
    ? "Collapse viewer settings"
    : "Expand viewer settings";
  const fileSheetToggleLabel = fileSheetOpen
    ? `Collapse ${fileSheetLabel(fileSheetKind)}`
    : `Expand ${fileSheetLabel(fileSheetKind)}`;
  const showTopBarSidebarTrigger = isMobile || sidebarState !== "expanded";

  return (
    <header
      className="cad-glass-surface pointer-events-auto flex h-11 shrink-0 items-center gap-2 border-b border-sidebar-border px-2 text-sidebar-foreground"
    >
      {showTopBarSidebarTrigger ? (
        <SidebarTrigger
          title="Toggle CAD Explorer"
          aria-label="Toggle CAD Explorer"
        />
      ) : null}

      <Breadcrumb className="min-w-0 flex-1">
        <BreadcrumbList className="min-w-0 flex-nowrap gap-1.5 text-xs sm:gap-1.5">
          {breadcrumbItems.map((item, index) => (
            <Fragment key={`${item.type}:${item.label}:${index}`}>
              <BreadcrumbItem className="min-w-0">
                {item.type === "ellipsis" ? (
                  <BreadcrumbEllipsis className="h-auto w-auto px-0.5 text-muted-foreground [&>svg]:hidden">
                    <span aria-hidden="true">...</span>
                    <span className="sr-only">Collapsed path</span>
                  </BreadcrumbEllipsis>
                ) : index < breadcrumbItems.length - 1 ? (
                  <BreadcrumbLink asChild className="block max-w-32 truncate text-xs font-medium">
                    <span title={selectedFileTitle}>{item.label}</span>
                  </BreadcrumbLink>
                ) : (
                  <BreadcrumbPage
                    className="block max-w-[min(36rem,55vw)] truncate text-xs font-medium"
                    title={selectedFileTitle}
                  >
                    {item.label}
                  </BreadcrumbPage>
                )}
              </BreadcrumbItem>
              {index < breadcrumbItems.length - 1 ? (
                <BreadcrumbSeparator className="text-muted-foreground/60" />
              ) : null}
            </Fragment>
          ))}
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex shrink-0 items-center gap-1">
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          aria-label={lookSheetToggleLabel}
          title={lookSheetToggleLabel}
          aria-pressed={lookMenuOpen}
          onClick={() => {
            setLookMenuOpen((current) => !current);
          }}
          className={`size-8 ${lookMenuOpen ? activeIconButtonClasses : ""}`}
        >
          <Palette className="size-4" strokeWidth={2} aria-hidden="true" />
        </Button>

        {showFileSheetToggle ? (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={fileSheetToggleLabel}
            title={fileSheetToggleLabel}
            aria-pressed={fileSheetOpen}
            onClick={onToggleFileSheet}
            className={`size-7 ${fileSheetOpen ? activeIconButtonClasses : ""}`}
          >
            <PanelRightIcon />
            <span className="sr-only">{fileSheetToggleLabel}</span>
          </Button>
        ) : null}
      </div>
    </header>
  );
}
