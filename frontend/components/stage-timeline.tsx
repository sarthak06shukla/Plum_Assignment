"use client";

import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

type Stage = {
  name: string;
  status: string;
  detail?: string | null;
  progress?: number;
  started_at?: string | null;
  completed_at?: string | null;
  confidence_score?: number | null;
};

export function StageTimeline({ stages }: { stages: Stage[] }) {
  return (
    <div className="space-y-3">
      {stages.map((stage, index) => {
        const status = stage.status.toLowerCase();
        const completed = status === "completed";
        const running = status === "running";
        const failed = status === "failed";
        return (
          <div key={stage.name} className="grid grid-cols-[24px_1fr_auto] gap-3">
            <div className="flex flex-col items-center">
              {completed ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              ) : failed ? (
                <XCircle className="h-5 w-5 text-red-600" />
              ) : running ? (
                <Loader2 className="h-5 w-5 animate-spin text-amber-600" />
              ) : (
                <Circle className="h-5 w-5 text-zinc-300" />
              )}
              {index < stages.length - 1 ? (
                <div className="mt-1 h-10 w-px bg-zinc-200" />
              ) : null}
            </div>
            <div className="pb-3">
              <p className="text-sm font-medium">{stage.name}</p>
              {stage.detail && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {stage.detail}
                </p>
              )}
              {(stage.started_at || stage.completed_at) && (
                <p className="mt-1 text-xs text-muted-foreground">
                  {stage.completed_at
                    ? new Date(stage.completed_at).toLocaleString()
                    : stage.started_at
                      ? new Date(stage.started_at).toLocaleString()
                      : ""}
                </p>
              )}
              {stage.confidence_score != null && (
                <p className="mt-1 text-xs text-muted-foreground">
                  Confidence: {stage.confidence_score}%
                </p>
              )}
              {stage.progress != null && (
                <div className="mt-2 max-w-sm">
                  <Progress value={stage.progress} />
                </div>
              )}
            </div>
            <Badge variant={completed ? "success" : failed ? "danger" : running ? "warning" : "muted"}>
              {stage.status}
            </Badge>
          </div>
        );
      })}
    </div>
  );
}
