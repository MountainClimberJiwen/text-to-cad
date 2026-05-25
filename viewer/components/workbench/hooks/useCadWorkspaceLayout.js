import { useEffect } from "react";

const SIDEBAR_WRAPPER_SELECTOR = "[data-slot='sidebar-wrapper']";

function sidebarWrapperElement() {
  return document.querySelector(SIDEBAR_WRAPPER_SELECTOR);
}

function applySidebarWidth(width) {
  sidebarWrapperElement()?.style.setProperty("--sidebar-width", `${width}px`);
}

function scheduleSidebarWidth(resizeState, width) {
  resizeState.latestWidth = width;
  if (resizeState.animationFrame) {
    return;
  }

  resizeState.animationFrame = window.requestAnimationFrame(() => {
    resizeState.animationFrame = 0;
    applySidebarWidth(resizeState.latestWidth);
  });
}

export function useCadWorkspaceLayout({
  restoredCadWorkspaceSessionRef,
  viewportReadyRef,
  hasSelectedEntry,
  isDesktop,
  setIsDesktop,
  setSidebarOpen,
  setTabToolsOpen,
  clampSidebarWidth,
  clampTabToolsWidth,
  setSidebarWidth,
  setTabToolsWidth,
  panelResizeStateRef,
  tabToolsResizeStateRef,
  defaultSidebarWidth,
  sidebarMinWidth,
  tabToolsMinWidth,
  endPanelResize,
  endTabToolsResize
}) {
  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 1024px)");
    const syncViewport = (event) => {
      const nextIsDesktop = event.matches;
      setIsDesktop(nextIsDesktop);
      setSidebarOpen((current) => {
        if (nextIsDesktop) {
          return true;
        }
        if (!viewportReadyRef.current) {
          if (restoredCadWorkspaceSessionRef.current) {
            return current;
          }
          return !hasSelectedEntry;
        }
        return hasSelectedEntry ? false : current;
      });
      setTabToolsOpen((current) => {
        if (!viewportReadyRef.current) {
          if (restoredCadWorkspaceSessionRef.current) {
            return current;
          }
          return false;
        }
        return nextIsDesktop ? current : false;
      });
      viewportReadyRef.current = true;
    };

    syncViewport(mediaQuery);
    mediaQuery.addEventListener("change", syncViewport);
    return () => {
      mediaQuery.removeEventListener("change", syncViewport);
    };
  }, [
    restoredCadWorkspaceSessionRef,
    hasSelectedEntry,
    setIsDesktop,
    setSidebarOpen,
    setTabToolsOpen,
    viewportReadyRef
  ]);

  useEffect(() => {
    if (!isDesktop) {
      return undefined;
    }

    const syncPanelWidths = () => {
      setSidebarWidth((current) => clampSidebarWidth(current));
      setTabToolsWidth((current) => clampTabToolsWidth(current));
    };

    syncPanelWidths();
    window.addEventListener("resize", syncPanelWidths);
    return () => {
      window.removeEventListener("resize", syncPanelWidths);
    };
  }, [clampSidebarWidth, clampTabToolsWidth, isDesktop, setSidebarWidth, setTabToolsWidth]);

  useEffect(() => {
    const handlePointerMove = (event) => {
      const resizeState = panelResizeStateRef.current;
      if (!resizeState) {
        return;
      }

      const rawWidth = resizeState.startWidth + (event.clientX - resizeState.startX);
      if (rawWidth < sidebarMinWidth) {
        if (resizeState.animationFrame) {
          window.cancelAnimationFrame(resizeState.animationFrame);
          resizeState.animationFrame = 0;
        }
        applySidebarWidth(defaultSidebarWidth);
        setSidebarWidth(defaultSidebarWidth);
        setSidebarOpen(false);
        endPanelResize();
        return;
      }

      const nextWidth = clampSidebarWidth(rawWidth);
      scheduleSidebarWidth(resizeState, nextWidth);
    };

    const endResize = () => {
      const resizeState = panelResizeStateRef.current;
      if (!resizeState) {
        return;
      }
      if (resizeState.animationFrame) {
        window.cancelAnimationFrame(resizeState.animationFrame);
      }
      const nextWidth = Math.max(
        sidebarMinWidth,
        clampSidebarWidth(resizeState.latestWidth ?? resizeState.startWidth)
      );
      applySidebarWidth(nextWidth);
      setSidebarWidth(nextWidth);
      endPanelResize();
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", endResize);
    window.addEventListener("pointercancel", endResize);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", endResize);
      window.removeEventListener("pointercancel", endResize);
      const resizeState = panelResizeStateRef.current;
      if (resizeState?.animationFrame) {
        window.cancelAnimationFrame(resizeState.animationFrame);
      }
      if (!tabToolsResizeStateRef.current) {
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };
  }, [
    clampSidebarWidth,
    endPanelResize,
    panelResizeStateRef,
    defaultSidebarWidth,
    setSidebarOpen,
    setSidebarWidth,
    sidebarMinWidth,
    tabToolsResizeStateRef
  ]);

  useEffect(() => {
    const handlePointerMove = (event) => {
      const resizeState = tabToolsResizeStateRef.current;
      if (!resizeState) {
        return;
      }

      const nextWidth = resizeState.startWidth - (event.clientX - resizeState.startX);
      if (nextWidth < tabToolsMinWidth) {
        setTabToolsWidth(tabToolsMinWidth);
        setTabToolsOpen(false);
        endTabToolsResize();
        return;
      }
      setTabToolsWidth(clampTabToolsWidth(nextWidth));
    };

    const endResize = () => {
      if (!tabToolsResizeStateRef.current) {
        return;
      }
      endTabToolsResize();
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", endResize);
    window.addEventListener("pointercancel", endResize);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", endResize);
      window.removeEventListener("pointercancel", endResize);
      if (!panelResizeStateRef.current) {
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      }
    };
  }, [
    clampTabToolsWidth,
    endTabToolsResize,
    panelResizeStateRef,
    setTabToolsOpen,
    setTabToolsWidth,
    tabToolsMinWidth,
    tabToolsResizeStateRef
  ]);
}
