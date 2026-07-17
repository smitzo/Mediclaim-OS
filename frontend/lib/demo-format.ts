/** Format the fixed INR fixture without converting monetary values to floats. */
export function formatInr(amount: string): string {
  const match = /^(\d+)\.(\d{2})$/.exec(amount);
  if (!match) return "Unavailable";
  const whole = new Intl.NumberFormat("en-IN").format(BigInt(match[1]));
  return `₹${whole}${match[2] === "00" ? "" : `.${match[2]}`}`;
}

export function formatDemoDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" })
    .format(new Date(`${value}T00:00:00Z`));
}
