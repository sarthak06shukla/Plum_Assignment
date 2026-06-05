"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Loader2 } from "lucide-react";

import { StageTimeline } from "@/components/stage-timeline";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";

const terminalStatuses = ["APPROVED", "REJECTED", "PARTIAL", "PARTIAL_APPROVAL", "MANUAL_REVIEW"];

export default function ClaimProcessingClient() {
  const params = useParams<{ id: string }>();
  const [stages, setStages] = useState<any[]>([]);
  const [claim, setClaim] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isFinal = claim ? terminalStatuses.includes(claim.status) : false;

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function load() {
      try {
        const [stagesData, claimData] = await Promise.all([
          api.getProcessing(params.id),
          api.getClaim(params.id),
        ]);
        if (cancelled) return;
        setStages(stagesData);
        setClaim(claimData);
        setError("");
        if (!terminalStatuses.includes(claimData.status)) {
          timer = setTimeout(load, 3000);
        }
      } catch (err: any) {
        if (cancelled) return;
        setError(err.message || "Failed to load processing status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [params.id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-normal">
            Claim Processing
          </h1>
          <p className="text-sm text-muted-foreground">
            {claim?.id} - {claim?.patient_name}
          </p>
        </div>
        {claim?.confidence_score != null && (
          <div className="text-sm font-medium numeric">
            {isFinal ? `${claim.confidence_score}% confidence` : "Processing..."}
          </div>
        )}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <Card>
          <CardHeader>
            <CardTitle>Processing Stages</CardTitle>
            <CardDescription>
              Every stage writes auditable evidence for the final decision.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <StageTimeline stages={stages} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Decision Confidence</CardTitle>
            <CardDescription>
              OCR, extraction completeness, document completeness and fraud penalty.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Progress value={claim?.confidence_score ?? 0} />
            <div className="text-3xl font-semibold numeric">
              {isFinal ? `${claim?.confidence_score ?? 0}%` : "Processing"}
            </div>
            {claim?.decision_explanation && (
              <p className="whitespace-pre-line text-sm text-muted-foreground">
                {claim.decision_explanation}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
