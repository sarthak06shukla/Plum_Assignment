import * as React from "react";

import { cn } from "@/lib/utils";

export function Progress({
  value,
  className
}: {
  value: number;
  className?: string;
}) {
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-sm bg-zinc-200", className)}>
      <div className="h-full bg-emerald-600 transition-all" style={{ width: `${Math.max(0, Math.min(value, 100))}%` }} />
    </div>
  );
}
