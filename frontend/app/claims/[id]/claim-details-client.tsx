"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, FileText, Loader2 } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { money } from "@/lib/data";
import { api, ApiError } from "@/lib/api";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

export default function ClaimDetailsClient() {
  const params = useParams<{ id: string }>();
  const [claim, setClaim] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const terminalStatuses = ["APPROVED", "REJECTED", "PARTIAL", "PARTIAL_APPROVAL", "MANUAL_REVIEW"];

    async function load() {
      try {
        const data = await api.getClaim(params.id);
        if (cancelled) return;
        setClaim(data);
        setError("");
        if (!terminalStatuses.includes(data.status) || !data.extracted_information) {
          timer = setTimeout(load, 3000);
        }
      } catch (err: any) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setError("Claim not found");
        } else {
          setError(err.message || "Failed to load claim");
        }
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

  if (error || !claim) {
    return (
      <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
        {error || "Claim not found"}
      </div>
    );
  }

  const extractedInfo = claim.extracted_information || {};
  const policyRules = claim.policy_evaluation || [];
  const auditTrail = claim.audit_trail || [];
  const fraudSignals = claim.fraud_signals || [];
  const documents = claim.documents || [];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-normal">{claim.id}</h1>
          <p className="text-sm text-muted-foreground">{claim.patient_name}</p>
        </div>
        <StatusBadge status={claim.status} />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Extracted Information</CardTitle>
              <CardDescription>
                Structured fields produced from OPD documents.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              {Object.entries(extractedInfo).map(([key, value]) => (
                <div key={key} className="rounded-md border bg-zinc-50 p-3">
                  <p className="text-xs font-medium uppercase text-muted-foreground">
                    {key.replaceAll("_", " ")}
                  </p>
                  <p className="mt-1 text-sm">
                    {Array.isArray(value)
                      ? value.join(", ")
                      : String(value ?? "")}
                  </p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Policy Evaluation</CardTitle>
              <CardDescription>
                Deterministic rule results in adjudication order.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Rule</TableHead>
                    <TableHead>Decision</TableHead>
                    <TableHead>Explanation</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {policyRules.map((rule: any, i: number) => (
                    <TableRow key={i}>
                      <TableCell className="font-mono text-xs">
                        {rule.rule}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            rule.status === "FAILED" || rule.decision === "FAILED" || rule.decision === "Failed"
                              ? "danger"
                              : rule.status === "ADJUSTED" || rule.decision === "ADJUSTED" || rule.decision === "Adjusted"
                                ? "warning"
                                : "success"
                          }
                        >
                          {rule.decision}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {rule.explanation}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Rule Audit Trail</CardTitle>
              <CardDescription>
                Pass/fail trail for every adjudication rule.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {auditTrail.map((item: any, i: number) => (
                <div
                  key={`${item.rule}-${i}`}
                  className="flex items-start gap-3 rounded-md border bg-zinc-50 p-3"
                >
                  <Badge
                    variant={
                      item.status === "FAILED"
                        ? "danger"
                        : item.status === "ADJUSTED"
                          ? "warning"
                          : "success"
                    }
                  >
                    {item.status === "PASSED" ? "Pass" : item.status === "FAILED" ? "Fail" : "Adjusted"}
                  </Badge>
                  <div>
                    <p className="text-sm font-medium">{item.label}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {item.explanation}
                    </p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          {claim.decision_explanation && (
            <Card>
              <CardHeader>
                <CardTitle>Decision Explanation</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-line text-sm leading-relaxed text-muted-foreground">
                  {claim.decision_explanation}
                </p>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Decision</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-md border bg-zinc-50 p-3">
                  <p className="text-xs text-muted-foreground">Claimed</p>
                  <p className="mt-1 text-lg font-semibold numeric">
                    {money(claim.claimed_amount)}
                  </p>
                </div>
                <div className="rounded-md border bg-zinc-50 p-3">
                  <p className="text-xs text-muted-foreground">Approved</p>
                  <p className="mt-1 text-lg font-semibold numeric">
                    {money(claim.approved_amount)}
                  </p>
                </div>
              </div>
              <div>
                <div className="mb-2 flex items-center justify-between text-xs">
                  <span>Confidence Score</span>
                  <span className="numeric">{claim.confidence_score}%</span>
                </div>
                <Progress value={claim.confidence_score} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Document Inspection</CardTitle>
              <CardDescription>
                Stored evidence, preview and OCR output.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {documents.map((doc: any) => (
                <div
                  key={doc.id || doc.filename}
                  className="rounded-md border p-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-zinc-500" />
                      <div>
                        <p className="text-sm font-medium">{doc.type}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.filename}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs numeric">
                      {doc.ocr_confidence}%
                    </span>
                  </div>
                  {doc.preview_url && (
                    <a
                      href={`${API_BASE}${doc.preview_url}`}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-flex text-xs font-medium text-emerald-700 hover:underline"
                    >
                      Open document preview
                    </a>
                  )}
                  <div className="mt-3 rounded-md bg-zinc-50 p-2">
                    <p className="mb-1 text-xs font-medium text-muted-foreground">
                      OCR Extracted Text
                    </p>
                    <pre className="max-h-36 overflow-auto whitespace-pre-wrap text-xs leading-relaxed text-zinc-700">
                      {doc.ocr_text || "No OCR text extracted."}
                    </pre>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Fraud Signals</CardTitle>
              <CardDescription>
                Signals route claims to review without auto-rejection.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              {fraudSignals.length === 0 ? (
                <Badge variant="success">No fraud signal detected</Badge>
              ) : (
                fraudSignals.map((signal: any) => (
                  <div
                    key={signal.code}
                    className="rounded-md border border-amber-200 bg-amber-50 p-3 text-amber-800"
                  >
                    <div className="flex items-center gap-2 text-sm font-medium">
                      <AlertTriangle className="h-4 w-4" />
                      {signal.code}
                    </div>
                    <p className="mt-1 text-xs">{signal.description}</p>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
