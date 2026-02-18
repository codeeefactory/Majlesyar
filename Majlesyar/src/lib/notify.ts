let sonnerPromise: Promise<typeof import("sonner")> | null = null;

function loadSonner() {
  if (!sonnerPromise) {
    sonnerPromise = import("sonner");
  }
  return sonnerPromise;
}

export function notifySuccess(message: string) {
  void loadSonner().then(({ toast }) => {
    toast.success(message);
  });
}

export function notifyError(message: string) {
  void loadSonner().then(({ toast }) => {
    toast.error(message);
  });
}

export function notifyInfo(message: string) {
  void loadSonner().then(({ toast }) => {
    toast.info(message);
  });
}
