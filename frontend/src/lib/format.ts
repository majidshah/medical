export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return iso;
  }
}

export function formatNumber(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "";
  return n.toFixed(decimals);
}
