"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CheckCircle2, FileUp, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";

const uploadSlots = [
  { key: "prescription", label: "Prescription", required: true },
  { key: "medical_bill", label: "Medical Bill", required: true },
  { key: "diagnostic_report", label: "Diagnostic Report", required: false },
] as const;

type UploadState = "idle" | "uploading" | "processing" | "complete" | "error";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function SubmitClaimPage() {
  const router = useRouter();
  const [files, setFiles] = useState<Record<string, File | null>>({
    prescription: null,
    medical_bill: null,
    diagnostic_report: null,
  });
  const [uploadState, setUploadState] = useState<UploadState>("idle");
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  const canSubmit =
    files.prescription !== null &&
    files.medical_bill !== null &&
    (uploadState === "idle" || uploadState === "error");

  function handleFileChange(key: string, fileList: FileList | null) {
    if (fileList && fileList.length > 0) {
      setFiles((prev) => ({ ...prev, [key]: fileList[0] }));
      if (uploadState === "error") {
        setUploadState("idle");
        setError("");
      }
    }
  }

  async function handleSubmit() {
    setError("");
    setUploadState("uploading");
    setProgress(20);

    const formData = new FormData();
    formData.append("prescription", files.prescription!);
    formData.append("medical_bill", files.medical_bill!);
    if (files.diagnostic_report) {
      formData.append("diagnostic_report", files.diagnostic_report);
    }

    setProgress(40);
    let progressTimer: ReturnType<typeof setInterval> | null = null;

    try {
      setProgress(60);
      setUploadState("processing");
      progressTimer = setInterval(() => {
        setProgress((current) => {
          if (current >= 95) return current;
          return current + 5;
        });
      }, 900);
      const result = await api.submitClaim(formData);
      if (progressTimer) clearInterval(progressTimer);
      setProgress(100);
      setUploadState("complete");
      // Redirect to processing page after brief delay
      setTimeout(() => router.push(`/claims/${result.id}/processing`), 600);
    } catch (err: any) {
      if (progressTimer) clearInterval(progressTimer);
      setError(err.message || "Upload failed");
      setUploadState("error");
      setProgress(0);
    }
  }

  const stateLabel: Record<UploadState, string> = {
    idle: "Waiting for files",
    uploading: "Uploading documents",
    processing: "Processing claim",
    complete: "Claim submitted",
    error: "Upload failed",
  };

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-normal">Submit Claim</h1>
        <p className="text-sm text-muted-foreground">
          Upload required OPD evidence for automated adjudication.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
        <Card>
          <CardHeader>
            <CardTitle>Documents</CardTitle>
            <CardDescription>
              Supported formats: PDF, PNG, JPG, JPEG.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3 md:grid-cols-3">
            {uploadSlots.map((slot) => {
              const file = files[slot.key];
              return (
                <label
                  key={slot.key}
                  className="flex min-h-44 cursor-pointer flex-col justify-between rounded-lg border border-dashed bg-zinc-50 p-4 hover:bg-white"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">
                      {slot.label}
                      {slot.required && (
                        <span className="ml-1 text-red-500">*</span>
                      )}
                    </span>
                    {file ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                    ) : (
                      <FileUp className="h-4 w-4 text-zinc-500" />
                    )}
                  </div>
                  <div>
                    {file ? (
                      <div className="space-y-1">
                        <p className="truncate text-xs font-medium">
                          {file.name}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatSize(file.size)}
                        </p>
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        Select file
                      </p>
                    )}
                    <input
                      className="mt-3 w-full text-xs"
                      type="file"
                      accept=".pdf,.png,.jpg,.jpeg"
                      onChange={(e) => handleFileChange(slot.key, e.target.files)}
                      disabled={uploadState !== "idle"}
                    />
                  </div>
                </label>
              );
            })}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Upload Progress</CardTitle>
            <CardDescription>{stateLabel[uploadState]}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Progress value={progress} />
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="numeric">{progress}%</span>
              <span>
                {uploadState === "complete" ? "Completed" : "Pending"}
              </span>
            </div>

            {error && (
              <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
                {error}
              </p>
            )}

            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!canSubmit}
            >
              {uploadState === "uploading" || uploadState === "processing" ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileUp className="h-4 w-4" />
              )}
              {uploadState === "complete"
                ? "Submitted"
                : uploadState === "error"
                  ? "Retry Upload"
                  : "Start Upload"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
