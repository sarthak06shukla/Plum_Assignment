"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { money } from "@/lib/data";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function ManualReviewPage() {
  const { role } = useAuth();
  const [reviews, setReviews] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // Track which review is being overridden: { reviewId, decision }
  const [overrideTarget, setOverrideTarget] = useState<{
    reviewId: string;
    decision: string;
  } | null>(null);
  const [overrideReason, setOverrideReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadReviews() {
    try {
      const data = await api.getManualReviews();
      setReviews(data);
    } catch (err: any) {
      setError(err.message || "Failed to load reviews");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (role?.toUpperCase() === "ADMIN") loadReviews();
    else setLoading(false);
  }, [role]);

  async function handleOverride() {
    if (!overrideTarget || !overrideReason.trim()) return;
    setSubmitting(true);
    try {
      await api.overrideReview(
        overrideTarget.reviewId,
        overrideTarget.decision,
        overrideReason,
      );
      setOverrideTarget(null);
      setOverrideReason("");
      // Refresh list
      await loadReviews();
    } catch (err: any) {
      setError(err.message || "Override failed");
    } finally {
      setSubmitting(false);
    }
  }

  if (role?.toUpperCase() !== "ADMIN") {
    return (
      <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
        Admin access required. You must be an admin to view this page.
      </div>
    );
  }

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
      <div>
        <h1 className="text-xl font-semibold tracking-normal">
          Manual Review Queue
        </h1>
        <p className="text-sm text-muted-foreground">
          Admin only queue for low confidence or fraud-routed claims.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Flagged Claims</CardTitle>
          <CardDescription>
            Reviewer override actions create audit log entries.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Claim</TableHead>
                <TableHead>Reason for Review</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead className="text-right">Confidence</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Override</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reviews.map((review: any) => (
                <TableRow key={review.review_id}>
                  <TableCell>
                    <div className="font-medium">{review.claim_id}</div>
                    <div className="text-xs text-muted-foreground">
                      {review.patient_name}
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="max-w-xl text-sm">{review.reason}</div>
                    {review.fraud_signals && review.fraud_signals.length > 0 && (
                      <div className="mt-1 text-xs text-muted-foreground">
                        {review.fraud_signals
                          .map((s: any) => (typeof s === "string" ? s : s.code))
                          .join(", ")}
                      </div>
                    )}
                  </TableCell>
                  <TableCell className="text-right numeric">
                    {money(review.claimed_amount)}
                  </TableCell>
                  <TableCell className="text-right numeric">
                    {review.confidence_score}%
                  </TableCell>
                  <TableCell>
                    {review.override_decision ? (
                      <Badge
                        variant={
                          review.override_decision === "APPROVED"
                            ? "success"
                            : "danger"
                        }
                      >
                        {review.override_decision}
                      </Badge>
                    ) : (
                      <Badge variant="muted">{review.status}</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    {overrideTarget?.reviewId === review.review_id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          placeholder="Reason..."
                          value={overrideReason}
                          onChange={(e) => setOverrideReason(e.target.value)}
                          className="h-8 w-40 rounded-md border px-2 text-xs outline-none focus:ring-2 focus:ring-emerald-600/30"
                          autoFocus
                        />
                        <Button
                          size="sm"
                          onClick={handleOverride}
                          disabled={submitting || !overrideReason.trim()}
                        >
                          {submitting ? (
                            <Loader2 className="h-3 w-3 animate-spin" />
                          ) : (
                            "Confirm"
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setOverrideTarget(null);
                            setOverrideReason("");
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    ) : (
                      <div className="flex justify-end gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={!!review.override_decision}
                          onClick={() =>
                            setOverrideTarget({
                              reviewId: review.review_id,
                              decision: "APPROVED",
                            })
                          }
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          Approve
                        </Button>
                        <Button
                          size="sm"
                          variant="destructive"
                          disabled={!!review.override_decision}
                          onClick={() =>
                            setOverrideTarget({
                              reviewId: review.review_id,
                              decision: "REJECTED",
                            })
                          }
                        >
                          <XCircle className="h-4 w-4" />
                          Reject
                        </Button>
                      </div>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
