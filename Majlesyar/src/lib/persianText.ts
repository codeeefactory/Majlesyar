export function normalizePersianDisplayText(text: string) {
  return text
    .replace(/\s*[0-9۰-۹]+\s*آدرس\.\s*(مادر|اول|دوم|سوم|چهارم|پنجم|اصلی):?.*$/g, "")
    .replace(/\s*آدرس\s*(اول|دوم|سوم|چهارم|پنجم|اصلی)?:?.*$/g, "")
    .replace(/\)\s*([^()]+?)\s*\(/g, "($1)")
    .replace(/\(([^()]+):\)/g, "($1):")
    .replace(/\)\s+:/g, "):")
    .replace(/\)\s+،/g, ")،")
    .replace(/\(\s+/g, "(")
    .replace(/\s+\)/g, ")")
    .replace(/([^\s(])\(/g, "$1 (")
    .replace(/\)(?=[^\s:،.؟!])/g, ") ")
    .replace(/\s+/g, " ")
    .trim();
}
