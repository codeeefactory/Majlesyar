import { buildUrl } from "@/lib/http";

const CLIENT_PING_STORAGE_KEY = "majlesyar_client_ping_ms";
const PING_ENDPOINT = "/api/v1/ping/";
const MAX_MEASUREMENT_WINDOW_MS = 900;
const MAX_ATTEMPTS = 3;

async function measureSingleRequest(): Promise<number> {
  const startedAt = performance.now();
  const response = await fetch(buildUrl(PING_ENDPOINT), {
    method: "GET",
    cache: "no-store",
    headers: {
      "Cache-Control": "no-cache",
      Pragma: "no-cache",
    },
  });

  if (!response.ok) {
    throw new Error(`Ping request failed with status ${response.status}`);
  }

  return performance.now() - startedAt;
}

function persistClientPing(pingMs: number): void {
  sessionStorage.setItem(CLIENT_PING_STORAGE_KEY, String(Math.round(pingMs)));
}

export function getStoredClientPingMs(): number | null {
  const rawValue = sessionStorage.getItem(CLIENT_PING_STORAGE_KEY);
  if (!rawValue) return null;

  const parsedValue = Number(rawValue);
  return Number.isFinite(parsedValue) ? parsedValue : null;
}

export async function measureAndStoreClientPing(): Promise<number | null> {
  if (typeof window === "undefined") return null;

  const deadline = performance.now() + MAX_MEASUREMENT_WINDOW_MS;
  let bestPingMs = Number.POSITIVE_INFINITY;

  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt += 1) {
    if (performance.now() >= deadline) break;

    try {
      const pingMs = await measureSingleRequest();
      if (pingMs < bestPingMs) {
        bestPingMs = pingMs;
      }
    } catch {
      const connectionRtt = navigator.connection?.rtt;
      if (typeof connectionRtt === "number" && connectionRtt > 0) {
        bestPingMs = Math.min(bestPingMs, connectionRtt);
      }
      break;
    }
  }

  if (!Number.isFinite(bestPingMs)) return null;

  persistClientPing(bestPingMs);
  return Math.round(bestPingMs);
}
