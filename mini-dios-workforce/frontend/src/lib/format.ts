import type { Currency } from "./types";

export function convertCurrency(
  amount: number,
  fromCurrency: Currency,
  toCurrency: Currency,
  fxEgpPerSar: number
): number {
  if (fromCurrency === toCurrency) return amount;
  if (fromCurrency === "SAR" && toCurrency === "EGP") return amount * fxEgpPerSar;
  if (fromCurrency === "EGP" && toCurrency === "SAR") return amount / fxEgpPerSar;
  return amount;
}

export function formatMoney(amount: number, currency: Currency): string {
  const formatted = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: 0,
  }).format(Math.round(amount));
  return `${currency} ${formatted}`;
}

export function formatNumber(val: number, decimals = 1): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(val);
}
