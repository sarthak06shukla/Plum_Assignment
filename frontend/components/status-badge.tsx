import { Badge } from "@/components/ui/badge";

const statusMap: Record<
  string,
  { label: string; variant: "success" | "warning" | "danger" | "muted" }
> = {
  APPROVED: { label: "Approved", variant: "success" },
  REJECTED: { label: "Rejected", variant: "danger" },
  PARTIAL: { label: "Partial", variant: "warning" },
  PARTIAL_APPROVAL: { label: "Partial Approval", variant: "warning" },
  MANUAL_REVIEW: { label: "Manual Review", variant: "muted" },
  SUBMITTED: { label: "Submitted", variant: "muted" },
  PROCESSING: { label: "Processing", variant: "muted" },
};

export function StatusBadge({ status }: { status: string }) {
  const item = statusMap[status] ?? { label: status, variant: "muted" as const };
  return <Badge variant={item.variant}>{item.label}</Badge>;
}
