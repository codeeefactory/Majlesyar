export function getInstagramHandle(url: string): string {
  const cleaned = url.trim().replace(/\/+$/, "");
  const match = cleaned.match(/instagram\.com\/([^/?#]+)/i);
  return match?.[1] ? `@${match[1]}` : cleaned;
}

export function getSameAsLinks(urls: Array<string | undefined | null>): string[] {
  return Array.from(new Set(urls.map((url) => (url || "").trim()).filter(Boolean)));
}
