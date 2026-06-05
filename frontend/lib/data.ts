export type ClaimStatus =
  | "APPROVED"
  | "REJECTED"
  | "PARTIAL"
  | "PARTIAL_APPROVAL"
  | "MANUAL_REVIEW"
  | "SUBMITTED"
  | "PROCESSING";

export function money(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}
