"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Upload,
  CheckCircle2,
  Scissors,
  BarChart3,
  GitCompare,
  BrainCircuit,
  CheckCircle,
  RotateCcw,
  AlertCircle,
  Clock,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface JobStage {
  key: string;
  label: string;
  Icon: React.ElementType;
}

export interface JobStatus {
  job_id: string;
  status: "uploading" | "qc" | "trimming" | "quantifying" | "dge" | "gnn" | "completed" | "failed";
  stage_progress?: number;
  message?: string;
  error?: string;
}

export type PredictionResult = {
  drugs: {
    rank: number;
    drug: string;
    target: string;
    drugClass: string;
    approvalStatus: string;
    matchScore: number;
    stageHypothesis: "Early Intervention" | "Advanced Fibrosis" | "Pan-Stage";
    ageAdjustment: string;
    topTargets: { gene: string; logFC: number; pValue: number }[];
    ferroptosisRelevance: "Driver-focused" | "Suppressor-focused" | "Balanced";
    confidence: "High" | "Moderate" | "Low";
    isNovelCandidate?: boolean;
  }[];
  stageHypotheses: { stage: string; probability: number; label: string }[];
  reasoningSummary: string;
  attentionWeights: { gene: string; layer1: number; layer2: number }[];
};

interface JobTrackerProps {
  jobId: string;
  onCompleted: (results: PredictionResult) => void;
  onFailed?: (error: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Stage definitions                                                  */
/* ------------------------------------------------------------------ */

const STAGES: JobStage[] = [
  { key: "uploading", label: "Upload", Icon: Upload },
  { key: "qc", label: "QC", Icon: CheckCircle2 },
  { key: "trimming", label: "Trimming", Icon: Scissors },
  { key: "quantifying", label: "Quantifying", Icon: BarChart3 },
  { key: "dge", label: "DGE Analysis", Icon: GitCompare },
  { key: "gnn", label: "GNN Inference", Icon: BrainCircuit },
  { key: "completed", label: "Complete", Icon: CheckCircle },
];

const STATUS_ORDER: string[] = STAGES.map((s) => s.key);

// Approximate per-stage time in seconds (used for ETA)
const STAGE_DURATIONS: Record<string, number> = {
  uploading: 90,
  qc: 120,
  trimming: 180,
  quantifying: 150,
  dge: 120,
  gnn: 60,
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getStageIndex(status: JobStatus["status"]): number {
  if (status.status === "failed") return -1;
  return STATUS_ORDER.indexOf(status.status);
}

function computeProgress(status: JobStatus): number {
  const idx = getStageIndex(status);
  if (idx <= 0) return 0;
  if (status.status === "completed") return 100;

  const basePercent = (idx / (STAGES.length - 1)) * 100;
  const stageFraction = status.stage_progress ?? 0;
  const stagePortion = 100 / (STAGES.length - 1);
  return Math.min(99, basePercent + (stageFraction / 100) * stagePortion);
}

function computeEta(status: JobStatus): string {
  const idx = getStageIndex(status);
  if (idx < 0 || status.status === "completed") return "";

  let remaining = 0;
  // Partial current stage
  const currentDuration = STAGE_DURATIONS[status.status] ?? 60;
  const stageFraction = status.stage_progress ?? 0;
  remaining += currentDuration * (1 - stageFraction / 100);

  // Full remaining stages
  for (let i = idx + 1; i < STAGES.length - 1; i++) {
    remaining += STAGE_DURATIONS[STAGES[i].key] ?? 60;
  }

  if (remaining < 60) return `Estimated: ~${Math.ceil(remaining)}s remaining`;
  const mins = Math.ceil(remaining / 60);
  return `Estimated: ~${mins} min remaining`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function JobTracker({ jobId, onCompleted, onFailed }: JobTrackerProps) {
  const [status, setStatus] = useState<JobStatus>({
    job_id: jobId,
    status: "uploading",
  });
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const pollStatus = useCallback(async () => {
    try {
      const res = await fetch(`/api/job?job_id=${encodeURIComponent(jobId)}`);
      if (!res.ok) throw new Error(`Status check failed (${res.status})`);
      const data: JobStatus = await res.json();
      setStatus(data);

      if (data.status === "completed") {
        // Fetch results
        const rRes = await fetch(
          `/api/job/results?job_id=${encodeURIComponent(jobId)}`
        );
        if (!rRes.ok) throw new Error("Result fetch failed");
        const results: PredictionResult = await rRes.json();
        onCompleted(results);
      }

      if (data.status === "failed") {
        onFailed?.(data.error ?? "Job failed with an unknown error");
      }
    } catch {
      // Silently retry — network blips shouldn't kill the tracker
    }
  }, [jobId, onCompleted, onFailed]);

  // Auto-poll every 3 seconds while not terminal
  useEffect(() => {
    pollStatus(); // immediate first poll
    intervalRef.current = setInterval(pollStatus, 3000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [pollStatus]);

  // Stop polling on terminal states
  useEffect(() => {
    if (status.status === "completed" || status.status === "failed") {
      if (intervalRef.current) clearInterval(intervalRef.current);
    }
  }, [status.status]);

  const currentIdx = getStageIndex(status);
  const progress = computeProgress(status);
  const eta = computeEta(status);
  const isFailed = status.status === "failed";

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: "auto" }}
        exit={{ opacity: 0, height: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className={`border ${isFailed ? "border-red-400 dark:border-red-500" : ""}`}>
          <CardContent className="p-5 space-y-4">
            {/* Header row */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isFailed ? (
                  <AlertCircle className="h-4 w-4 text-red-500" />
                ) : (
                  <Clock className="h-4 w-4 text-emerald-600" />
                )}
                <span className="text-sm font-medium">
                  {isFailed ? "Pipeline Failed" : "Processing Pipeline"}
                </span>
                <span className="text-xs text-muted-foreground font-mono">
                  {jobId.slice(0, 8)}
                </span>
              </div>
              {eta && !isFailed && (
                <span className="text-xs text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {eta}
                </span>
              )}
            </div>

            {/* Overall progress bar */}
            {!isFailed && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {STAGES[Math.max(0, currentIdx)]?.label ?? "Starting"}…
                  </span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress
                  value={progress}
                  className="h-2 [&>div]:bg-emerald-500"
                />
              </div>
            )}

            {/* Stepper */}
            <div className="flex items-center justify-between gap-1">
              {STAGES.map((stage, i) => {
                const Icon = stage.Icon;
                const isCompleted = i < currentIdx;
                const isCurrent = i === currentIdx;
                const isFuture = i > currentIdx;

                return (
                  <div
                    key={stage.key}
                    className="flex flex-col items-center gap-1.5 flex-1 min-w-0"
                  >
                    {/* Connector line */}
                    {i > 0 && (
                      <div className="absolute left-0 right-0 top-1/2 h-0.5 -translate-y-1/2 -z-10 hidden" />
                    )}
                    <motion.div
                      key={`${stage.key}-${isCompleted}-${isCurrent}`}
                      initial={{ scale: 0.9, opacity: 0.6 }}
                      animate={{
                        scale: isCurrent ? 1.1 : 1,
                        opacity: isFuture ? 0.35 : 1,
                      }}
                      transition={{ type: "spring", stiffness: 300, damping: 20 }}
                      className={`
                        flex items-center justify-center h-8 w-8 rounded-full border-2 transition-colors
                        ${
                          isCompleted
                            ? "bg-emerald-500 border-emerald-500 text-white"
                            : isCurrent
                            ? "bg-emerald-100 dark:bg-emerald-950/40 border-emerald-500 text-emerald-600 dark:text-emerald-400"
                            : "bg-muted border-muted-foreground/20 text-muted-foreground/40"
                        }
                      `}
                    >
                      {isCompleted ? (
                        <CheckCircle className="h-4 w-4" />
                      ) : (
                        <Icon className="h-4 w-4" />
                      )}
                    </motion.div>
                    <span
                      className={`text-[10px] leading-tight text-center truncate w-full ${
                        isFuture
                          ? "text-muted-foreground/40"
                          : isCurrent
                          ? "text-emerald-600 dark:text-emerald-400 font-medium"
                          : "text-muted-foreground"
                      }`}
                    >
                      {stage.label}
                    </span>
                  </div>
                );
              })}
            </div>

            {/* Error state */}
            <AnimatePresence>
              {isFailed && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -4 }}
                  className="space-y-3"
                >
                  <div className="rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800/40 p-3">
                    <p className="text-xs text-red-700 dark:text-red-400">
                      {status.error ?? "An unexpected error occurred during pipeline processing."}
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-9 text-xs border-red-300 text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-950/30"
                    onClick={() => window.location.reload()}
                  >
                    <RotateCcw className="mr-1.5 h-3 w-3" />
                    Retry
                  </Button>
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}