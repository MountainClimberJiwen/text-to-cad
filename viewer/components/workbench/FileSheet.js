import { cn } from "../../lib/cn";

const DEFAULT_FILE_SHEET_WIDTH = 260;
const DESKTOP_FILE_SHEET_MIN_WIDTH = 240;
const DESKTOP_FILE_SHEET_MAX_WIDTH = "calc(100vw - 0.75rem)";
const MOBILE_FILE_SHEET_WIDTH = "min(24rem, calc(100vw - 0.75rem))";

function normalizeFileSheetWidth(width) {
  const numericWidth = Number(width);
  if (!Number.isFinite(numericWidth) || numericWidth <= 0) {
    return DEFAULT_FILE_SHEET_WIDTH;
  }
  return Math.max(DESKTOP_FILE_SHEET_MIN_WIDTH, numericWidth);
}

export default function FileSheet({
  open,
  title,
  isDesktop,
  width,
  bodyClassName,
  children
}) {
  if (!open) {
    return null;
  }

  const desktopWidth = `min(${normalizeFileSheetWidth(width)}px, ${DESKTOP_FILE_SHEET_MAX_WIDTH})`;
  const sheetStyle = isDesktop
    ? {
      width: desktopWidth,
      flexBasis: desktopWidth,
      minWidth: `min(${DESKTOP_FILE_SHEET_MIN_WIDTH}px, ${DESKTOP_FILE_SHEET_MAX_WIDTH})`,
      maxWidth: DESKTOP_FILE_SHEET_MAX_WIDTH
    }
    : {
      width: MOBILE_FILE_SHEET_WIDTH,
      flexBasis: MOBILE_FILE_SHEET_WIDTH,
      maxWidth: DESKTOP_FILE_SHEET_MAX_WIDTH
    };

  return (
    <aside
      className="cad-glass-surface pointer-events-auto relative z-30 flex h-full shrink-0 max-w-[calc(100vw_-_0.75rem)] flex-col border-l border-sidebar-border text-sidebar-foreground"
      style={sheetStyle}
      aria-label={title}
    >
      <div className={cn("min-h-0 flex-1 overflow-y-auto", bodyClassName)}>
        {children}
      </div>
    </aside>
  );
}
