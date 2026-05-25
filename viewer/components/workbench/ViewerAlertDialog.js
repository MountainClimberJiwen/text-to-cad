import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from "../ui/alert-dialog";
import { Badge } from "../ui/badge";

export default function ViewerAlertDialog({
  viewerAlertOpen,
  viewerAlert,
  previewMode,
  setViewerAlertOpen
}) {
  if (!viewerAlert || previewMode) {
    return null;
  }
  const isWarning = viewerAlert.severity === "warning";

  return (
    <AlertDialog
      open={viewerAlertOpen}
      onOpenChange={setViewerAlertOpen}
    >
      <AlertDialogContent className="max-w-md">
        <AlertDialogHeader>
          <Badge
            variant={isWarning ? "warning" : "destructive"}
            className="mb-1"
          >
            {isWarning ? "Warning" : "Error"}
          </Badge>
          <AlertDialogTitle>{viewerAlert.title}</AlertDialogTitle>
          <AlertDialogDescription className="space-y-3 leading-6">
            <span className="block">{viewerAlert.message}</span>
            {viewerAlert.resolution ? (
              <span className="block text-muted-foreground/80">{viewerAlert.resolution}</span>
            ) : null}
          </AlertDialogDescription>
        </AlertDialogHeader>
        {viewerAlert.command ? (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">Rebuild command</p>
            <code className="mt-2 block rounded-md bg-muted px-4 py-3 text-xs leading-6 text-foreground">
              {viewerAlert.command}
            </code>
          </div>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel aria-label="Close alert dialog">Close</AlertDialogCancel>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
