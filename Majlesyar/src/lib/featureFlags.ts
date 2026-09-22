const enabledValues = new Set(['1', 'true', 'yes', 'on']);

// Temporary public kill switch. Existing models and background generation stay intact.
export const PUBLIC_3D_MODELS_ENABLED = enabledValues.has(
  String(import.meta.env.VITE_PUBLIC_3D_MODELS_ENABLED ?? '').trim().toLowerCase(),
);
