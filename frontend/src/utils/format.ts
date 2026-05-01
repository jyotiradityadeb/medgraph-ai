export function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function ms(seconds: number): string {
  return `${(seconds * 1000).toFixed(0)} ms`;
}
