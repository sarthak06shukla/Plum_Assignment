"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  FileCheck2,
  Loader2,
  XCircle,
} from "lucide-react";

import { MetricCard } from "@/components/metric-card";
import { StatusBadge } from "@/components/status-badge";
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

type DashboardMetric = {
  label: string;
  value: number;
  delta: string;
  icon: typeof FileCheck2;
};

export default function DashboardPage() {
  const { role } = useAuth();
  const [claims, setClaims] = useState<any[]>([]);
  const [metrics, setMetrics] = useState<DashboardMetric[]>([]);
  const [distribution, setDistribution] = useState<
    { label: string; count: number; color: string }[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        if (role?.toUpperCase() === "ADMIN") {
          const [dash, claimsList] = await Promise.all([
            api.getDashboard(),
            api.getAdminClaims(),
          ]);
          setClaims(claimsList);
          setMetrics([
            {
              label: "Total Claims",
              value: dash.total_claims,
              delta: `${claimsList.length} processed`,
              icon: FileCheck2,
            },
            {
              label: "Approved",
              value: dash.approved,
              delta: "auto-approved",
              icon: CheckCircle2,
            },
            {
              label: "Rejected",
              value: dash.rejected,
              delta: "policy exclusion",
              icon: XCircle,
            },
            {
              label: "Partial Approval",
              value: dash.partial ?? dash.partial_approval,
              delta: "limit-capped",
              icon: CircleDashed,
            },
            {
              label: "Manual Review",
              value: dash.manual_review,
              delta: "review queue",
              icon: AlertTriangle,
            },
          ]);
          const dist = dash.decision_distribution || {};
          setDistribution([
            {
              label: "Approved",
              count: dist.APPROVED || 0,
              color: "bg-emerald-600",
            },
            {
              label: "Rejected",
              count: dist.REJECTED || 0,
              color: "bg-red-600",
            },
            {
              label: "Partial",
              count: dist.PARTIAL || dist.PARTIAL_APPROVAL || 0,
              color: "bg-amber-500",
            },
            {
              label: "Review",
              count: dist.MANUAL_REVIEW || 0,
              color: "bg-zinc-600",
            },
          ]);
        } else {
          // Regular user: compute metrics from own claims
          const claimsList = await api.getClaims();
          setClaims(claimsList);
          const approved = claimsList.filter(
            (c: any) => c.status === "APPROVED",
          ).length;
          const rejected = claimsList.filter(
            (c: any) => c.status === "REJECTED",
          ).length;
          const partial = claimsList.filter(
            (c: any) => c.status === "PARTIAL" || c.status === "PARTIAL_APPROVAL",
          ).length;
          const review = claimsList.filter(
            (c: any) => c.status === "MANUAL_REVIEW",
          ).length;
          setMetrics([
            {
              label: "Total Claims",
              value: claimsList.length,
              delta: "your claims",
              icon: FileCheck2,
            },
            {
              label: "Approved",
              value: approved,
              delta: "auto-approved",
              icon: CheckCircle2,
            },
            {
              label: "Rejected",
              value: rejected,
              delta: "policy exclusion",
              icon: XCircle,
            },
            {
              label: "Partial Approval",
              value: partial,
              delta: "limit-capped",
              icon: CircleDashed,
            },
            {
              label: "Manual Review",
              value: review,
              delta: "review queue",
              icon: AlertTriangle,
            },
          ]);
          setDistribution([
            { label: "Approved", count: approved, color: "bg-emerald-600" },
            { label: "Rejected", count: rejected, color: "bg-red-600" },
            { label: "Partial", count: partial, color: "bg-amber-500" },
            { label: "Review", count: review, color: "bg-zinc-600" },
          ]);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [role]);

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

  const total = Math.max(claims.length, 1);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-normal">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            OPD adjudication workload and decision quality.
          </p>
        </div>
        <div className="text-xs text-muted-foreground">Policy PLUM-OPD-2026</div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>Recent Claims</CardTitle>
            <CardDescription>
              Claims sorted by latest submission.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Claim</TableHead>
                  <TableHead>Patient</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Claimed</TableHead>
                  <TableHead className="text-right">Payable</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {claims.map((claim: any) => (
                  <TableRow key={claim.id}>
                    <TableCell>
                      <Link
                        href={`/claims/${claim.id}`}
                        className="font-medium text-emerald-700 hover:underline"
                      >
                        {claim.id}
                      </Link>
                      <div className="text-xs text-muted-foreground">
                        {new Date(claim.created_at).toLocaleDateString()}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{claim.patient_name}</div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={claim.status} />
                    </TableCell>
                    <TableCell className="text-right numeric">
                      {money(claim.claimed_amount)}
                    </TableCell>
                    <TableCell className="text-right numeric">
                      {money(claim.approved_amount)}
                    </TableCell>
                    <TableCell className="text-right numeric">
                      {claim.confidence_score}%
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Decision Distribution</CardTitle>
            <CardDescription>
              Current adjudication mix.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {distribution.map((item) => {
              const width = `${Math.max(8, (item.count / total) * 100)}%`;
              return (
                <div key={item.label}>
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="font-medium">{item.label}</span>
                    <span className="numeric text-muted-foreground">
                      {item.count}
                    </span>
                  </div>
                  <div className="h-2 rounded-sm bg-zinc-200">
                    <div
                      className={`${item.color} h-2 rounded-sm`}
                      style={{ width }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
