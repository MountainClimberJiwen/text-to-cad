import {
  Toast,
  ToastProvider,
  ToastTitle,
  ToastViewport
} from "../ui/toast";

export default function StatusToast({ copyStatus, screenshotStatus, persistenceStatus, previewMode, onClear }) {
  const message = copyStatus || screenshotStatus || persistenceStatus;
  if (!message || previewMode) {
    return null;
  }

  return (
    <ToastProvider duration={2200} swipeDirection="right">
      <Toast
        open={true}
        onOpenChange={(open) => {
          if (!open) {
            onClear?.();
          }
        }}
      >
        <ToastTitle>{message}</ToastTitle>
      </Toast>
      <ToastViewport />
    </ToastProvider>
  );
}
