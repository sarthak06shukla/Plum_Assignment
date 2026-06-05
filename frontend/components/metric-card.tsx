import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function MetricCard({
  label,
  value,
  delta,
  icon: Icon
}: {
  label: string;
  value: string | number;
  delta: string;
  icon: LucideIcon;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between p-4">
        <div>
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <p className="mt-2 text-2xl font-semibold tracking-normal numeric">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{delta}</p>
        </div>
        <div className="rounded-md border bg-zinc-50 p-2 text-zinc-600">
          <Icon className="h-4 w-4" />
        </div>
      </CardContent>
    </Card>
  );
}
