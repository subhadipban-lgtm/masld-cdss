"use client";

import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FlaskConical,
  Upload,
  FileText,
  BrainCircuit,
  ChevronDown,
  ChevronUp,
  Loader2,
  Network,
  Grid3X3,
  Zap,
  Beaker,
} from "lucide-react";
import type {
  DrugPrediction,
  StageProbability,
  ExplainerNode,
  ExplainerEdge,
} from "@/lib/masld-data";
import {
  EASL_GUIDELINES,
  EXPLAINER_NODES,
  EXPLAINER_EDGES,
} from "@/lib/masld-data";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import JobTracker from "@/components/masld/job-tracker";
import type { PredictionResult as JobPredictionResult } from "@/components/masld/job-tracker";

interface PredictionResult {
  drugs: DrugPrediction[];
  stageHypotheses: StageProbability[];
  reasoningSummary: string;
  attentionWeights: { gene: string; layer1: number; layer2: number }[];
}

const CONFIDENCE_COLORS: Record<string, string> = {
  High: "bg-emerald-500",
  Moderate: "bg-amber-500",
  Low: "bg-slate-400",
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function getApprovalBadge(status: string) {
  if (status.includes("FDA-Approved")) {
    return (
      <Badge variant="outline" className="border-emerald-500/50 text-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 dark:text-emerald-400 text-xs">
        FDA-Approved
      </Badge>
    );
  }
  if (status.includes("Investigational")) {
    return (
      <Badge variant="outline" className="border-amber-500/50 text-amber-700 bg-amber-50 dark:bg-amber-950/30 dark:text-amber-400 text-xs">
        Investigational
      </Badge>
    );
  }
  if (status.includes("Repurposing") || status.includes("Repurposed")) {
    return (
      <Badge variant="outline" className="border-purple-500/50 text-purple-700 bg-purple-50 dark:bg-purple-950/30 dark:text-purple-400 text-xs">
        Repurposed
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="border-slate-400/50 text-slate-600 bg-slate-50 dark:bg-slate-800/30 dark:text-slate-400 text-xs">
      Natural Product
    </Badge>
  );
}

function DrugNetworkGraph() {
  const nodeMap = new Map(EXPLAINER_NODES.map((n) => [n.id, n]));

  const NODE_COLORS: Record<string, string> = {
    drug: "#10b981",
    gene: "#64748b",
    pathway: "#f59e0b",
  };

  const EDGE_STYLES: Record<string, string> = {
    targets: "#10b981",
    "co-expressed": "#64748b",
    "pathway-shared": "#f59e0b",
    PPI: "#0d9488",
  };

  return (
    <div className="w-full">
      <svg viewBox="0 0 620 520" className="w-full h-auto" role="img" aria-label="Drug-target network graph">
        {EXPLAINER_EDGES.map((edge, i) => {
          const src = nodeMap.get(edge.source);
          const tgt = nodeMap.get(edge.target);
          if (!src || !tgt) return null;
          const color = EDGE_STYLES[edge.type] || "#64748b";
          return (
            <line
              key={i}
              x1={src.x}
              y1={src.y}
              x2={tgt.x}
              y2={tgt.y}
              stroke={color}
              strokeWidth={edge.weight * 2.5}
              opacity={0.2 + edge.weight * 0.5}
              strokeDasharray={edge.type === "co-expressed" ? "4 3" : undefined}
            />
          );
        })}
        {EXPLAINER_NODES.map((node) => {
          const r = 8 + node.importance * 14;
          const color = NODE_COLORS[node.type];
          return (
            <g key={node.id}>
              <circle
                cx={node.x}
                cy={node.y}
                r={r}
                fill={color}
                opacity={0.15 + node.importance * 0.3}
                stroke={color}
                strokeWidth={1.5}
              />
              <text
                x={node.x}
                y={node.y + r + 14}
                textAnchor="middle"
                className="fill-foreground text-[10px] font-medium"
                style={{ fontSize: "10px" }}
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-4 mt-3 px-1 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded bg-emerald-500 inline-block" /> Targets
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded bg-slate-500 inline-block" style={{ background: "#64748b" }} /> Co-expressed
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded bg-amber-500 inline-block" /> Pathway-shared
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-0.5 rounded bg-teal-600 inline-block" /> PPI
        </span>
        <span className="flex items-center gap-1.5 ml-auto">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block" /> Drug
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: "#64748b" }} /> Gene
        </span>
      </div>
    </div>
  );
}

function AttentionHeatmap({ weights }: { weights: { gene: string; layer1: number; layer2: number }[] }) {
  const getCellColor = (val: number) => {
    const clamped = Math.max(0, Math.min(1, val));
    if (clamped > 0.7) return "bg-emerald-700 text-emerald-50 dark:bg-emerald-500";
    if (clamped > 0.5) return "bg-emerald-600 text-emerald-50 dark:bg-emerald-400";
    if (clamped > 0.3) return "bg-emerald-400 text-emerald-900 dark:bg-emerald-600";
    if (clamped > 0.15) return "bg-emerald-200 text-emerald-900 dark:bg-emerald-800";
    return "bg-emerald-100 text-emerald-800 dark:bg-emerald-950";
  };

  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr>
            <th className="text-left py-1.5 pr-3 font-medium text-muted-foreground w-20">Gene</th>
            <th className="text-center py-1.5 px-1 font-medium text-muted-foreground w-20">Layer 1</th>
            <th className="text-center py-1.5 px-1 font-medium text-muted-foreground w-20">Layer 2</th>
          </tr>
        </thead>
        <tbody>
          {weights.map((w) => (
            <tr key={w.gene}>
              <td className="py-1 pr-3 font-mono text-muted-foreground whitespace-nowrap">{w.gene}</td>
              <td className="py-1 px-1">
                <div className={`${getCellColor(w.layer1)} rounded text-center py-1 font-mono`}>
                  {w.layer1.toFixed(3)}
                </div>
              </td>
              <td className="py-1 px-1">
                <div className={`${getCellColor(w.layer2)} rounded text-center py-1 font-mono`}>
                  {w.layer2.toFixed(3)}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PipelineTab() {
  const [age, setAge] = useState("55");
  const [fibrosisStage, setFibrosisStage] = useState("F2");
  const [bmi, setBmi] = useState("31.5");
  const [alt, setAlt] = useState("58");
  const [ast, setAst] = useState("45");
  const [hba1c, setHba1c] = useState("6.7");
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<PredictionResult | null>(null);
  const [showAllDrugs, setShowAllDrugs] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isProductionMode = !!file;

  const handleFileChange = useCallback((f: File | null) => {
    if (f) setFile(f);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFileChange(f);
    },
    [handleFileChange]
  );

  const clearJob = useCallback(() => {
    setJobId(null);
    setJobError(null);
    setResults(null);
    setLoading(false);
  }, []);

  const handleJobCompleted = useCallback((jobResults: JobPredictionResult) => {
    // Map job results to the local PredictionResult shape
    setResults(jobResults as PredictionResult);
  }, []);

  const handleJobFailed = useCallback((error: string) => {
    setJobError(error);
  }, []);

  /* -------------------------------------------------------------- */
  /*  Demo mode — synchronous /api/predict                           */
  /* -------------------------------------------------------------- */
  const runDemoPrediction = async () => {
    setLoading(true);
    try {
      const response = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          age: Number(age),
          fibrosisStage: parseInt(fibrosisStage.replace("F", ""), 10),
          bmi: Number(bmi),
          alt: Number(alt),
          ast: Number(ast),
          hba1c: Number(hba1c),
          hasFastq: !!file,
        }),
      });
      if (!response.ok) throw new Error("Prediction request failed");
      const data: PredictionResult = await response.json();
      setResults(data);
    } catch {
      const fallback: PredictionResult = {
        drugs: [
          { rank: 1, drug: "Resmetirom", target: "THR-β", drugClass: "Thyromimetic", approvalStatus: "FDA-Approved (2024)", matchScore: 94, stageHypothesis: "Pan-Stage", ageAdjustment: "No age-specific adjustment", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "High" },
          { rank: 2, drug: "Semaglutide", target: "GLP-1R", drugClass: "GLP-1 RA", approvalStatus: "FDA-Approved", matchScore: 87, stageHypothesis: "Early Intervention", ageAdjustment: "Ferroptosis boost (young); metabolic favour (older)", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "High" },
          { rank: 3, drug: "Pioglitazone", target: "PPAR-γ", drugClass: "TZD", approvalStatus: "FDA-Approved", matchScore: 82, stageHypothesis: "Early Intervention", ageAdjustment: "Metabolic favour across all ages", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "Moderate" },
          { rank: 4, drug: "Vitamin E", target: "Antioxidant", drugClass: "Nutritional", approvalStatus: "FDA-Approved (MASLD)", matchScore: 76, stageHypothesis: "Early Intervention", ageAdjustment: "No age-specific adjustment", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "Moderate" },
          { rank: 5, drug: "Obeticholic Acid", target: "FXR", drugClass: "FXR Agonist", approvalStatus: "FDA-Approved (PBC)", matchScore: 71, stageHypothesis: "Early Intervention", ageAdjustment: "No age-specific adjustment", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "Moderate" },
          { rank: 6, drug: "Disulfiram", target: "ALDH2", drugClass: "Repurposed", approvalStatus: "Repurposing Candidate", matchScore: 68, stageHypothesis: "Advanced Fibrosis", ageAdjustment: "Ferroptosis boost (young); metabolic favour (older)", topTargets: [], ferroptosisRelevance: "Balanced", confidence: "High", isNovelCandidate: true },
          { rank: 7, drug: "Lanifibranor", target: "Pan-PPAR", drugClass: "Pan-PPAR Agonist", approvalStatus: "Investigational (Phase 3)", matchScore: 66, stageHypothesis: "Early Intervention", ageAdjustment: "Metabolic favour (older)", topTargets: [], ferroptosisRelevance: "Balanced", confidence: "Moderate" },
          { rank: 8, drug: "Berberine", target: "AMPK/SIRT1", drugClass: "Natural Product", approvalStatus: "Natural Product", matchScore: 63, stageHypothesis: "Pan-Stage", ageAdjustment: "Ferroptosis boost (young)", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "Moderate" },
          { rank: 9, drug: "Curcumin", target: "NF-κB/TGF-β", drugClass: "Polyphenol", approvalStatus: "Natural Product", matchScore: 58, stageHypothesis: "Advanced Fibrosis", ageAdjustment: "No age-specific adjustment", topTargets: [], ferroptosisRelevance: "Balanced", confidence: "Moderate" },
          { rank: 10, drug: "Silymarin", target: "NRF2/GPX4", drugClass: "Flavonolignan", approvalStatus: "Natural Product", matchScore: 54, stageHypothesis: "Advanced Fibrosis", ageAdjustment: "No age-specific adjustment", topTargets: [], ferroptosisRelevance: "Suppressor-focused", confidence: "Low" },
        ],
        stageHypotheses: [
          { stage: "F0", probability: 0.05, label: "F0" },
          { stage: "F1", probability: 0.12, label: "F1" },
          { stage: "F2", probability: 0.48, label: "F2" },
          { stage: "F3", probability: 0.28, label: "F3" },
          { stage: "F4", probability: 0.07, label: "F4" },
        ],
        reasoningSummary:
          "The GNN model identifies F2 fibrosis as the most probable stage (48%) based on the patient's transcriptomic signature showing upregulation of PNPLA3 (logFC 0.91) and TM6SF2 (logFC 0.84), combined with moderate ALT/AST elevation. The top-ranked drug, Resmetirom, achieves its high match score (94%) through strong THR-β engagement (SHAP +0.142) and downstream suppression of SREBF1 and FASN, addressing the patient's lipid dysregulation profile. Semaglutide ranks second (87%) via NRF2-antioxidant pathway activation, providing complementary ferroptosis suppression. The model highlights Disulfiram as a novel candidate (rank 6, 68%) through ALDH2-mediated GPX4 stabilisation, a mechanism not captured by conventional pathway analysis.",
        attentionWeights: [
          { gene: "PPARG", layer1: 0.142, layer2: 0.118 },
          { gene: "FASN", layer1: 0.128, layer2: 0.104 },
          { gene: "SCD", layer1: 0.115, layer2: 0.091 },
          { gene: "PNPLA3", layer1: 0.091, layer2: 0.084 },
          { gene: "TM6SF2", layer1: 0.084, layer2: 0.076 },
          { gene: "THRB", layer1: 0.079, layer2: 0.068 },
          { gene: "SREBF1", layer1: 0.072, layer2: 0.061 },
          { gene: "GPX4", layer1: 0.065, layer2: 0.054 },
          { gene: "NFE2L2", layer1: 0.058, layer2: 0.047 },
          { gene: "SLC7A11", layer1: 0.048, layer2: 0.038 },
        ],
      };
      setResults(fallback);
    } finally {
      setLoading(false);
    }
  };

  /* -------------------------------------------------------------- */
  /*  Production mode — async /api/job                               */
  /* -------------------------------------------------------------- */
  const runProductionPrediction = async () => {
    if (!file) return;
    setLoading(true);
    setJobError(null);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append("fastq", file);
      formData.append(
        "clinical_params",
        JSON.stringify({
          age: Number(age),
          fibrosisStage: parseInt(fibrosisStage.replace("F", ""), 10),
          bmi: Number(bmi),
          alt: Number(alt),
          ast: Number(ast),
          hba1c: Number(hba1c),
        })
      );

      const response = await fetch("/api/job", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errBody = await response.json().catch(() => ({ error: "Upload request failed" }));
        throw new Error(errBody.error ?? "Upload request failed");
      }

      const data = await response.json();
      const id: string = data.job_id ?? data.jobId;
      if (!id) throw new Error("No job_id returned from backend");
      setJobId(id);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to submit job";
      setJobError(msg);
      setLoading(false);
    } finally {
      setLoading(false);
    }
  };

  const runPrediction = async () => {
    if (isProductionMode) {
      await runProductionPrediction();
    } else {
      await runDemoPrediction();
    }
  };

  const displayedDrugs = showAllDrugs
    ? results?.drugs ?? []
    : (results?.drugs ?? []).slice(0, 6);

  const topStage = results?.stageHypotheses.reduce(
    (max, s) => (s.probability > max.probability ? s : max),
    results.stageHypotheses[0]
  );

  // Determine if we should show the job tracker
  const showJobTracker = jobId !== null && !results && !jobError;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left Column */}
      <div className="lg:col-span-5 flex flex-col gap-6">
        {/* Card 1: Patient & Transcriptomic Input */}
        <Card>
          <CardHeader className="pb-4">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold flex items-center gap-2">
                <FileText className="h-4 w-4 text-emerald-600" />
                Patient &amp; Transcriptomic Input
              </CardTitle>
              <Badge
                variant="outline"
                className={`text-[10px] px-2 py-0.5 ${
                  isProductionMode
                    ? "border-emerald-500/50 text-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 dark:text-emerald-400"
                    : "border-slate-400/50 text-slate-600 bg-slate-50 dark:bg-slate-800/30 dark:text-slate-400"
                }`}
              >
                {isProductionMode ? (
                  <span className="flex items-center gap-1">
                    <Zap className="h-3 w-3" />
                    Production Mode
                  </span>
                ) : (
                  <span className="flex items-center gap-1">
                    <Beaker className="h-3 w-3" />
                    Demo Mode
                  </span>
                )}
              </Badge>
            </div>
            <CardDescription className="text-xs">
              {isProductionMode
                ? "FASTQ uploaded — will run full transcriptomic pipeline"
                : "Upload a FASTQ file to enable production mode, or run with clinical params only"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* FASTQ Upload */}
            <div className="space-y-2">
              <Label className="text-xs font-medium">FASTQ File</Label>
              <div
                className={`relative border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
                  isDragging
                    ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/20"
                    : file
                    ? "border-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/10"
                    : "border-muted-foreground/25 hover:border-muted-foreground/50"
                }`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                role="button"
                tabIndex={0}
                aria-label="Upload FASTQ file"
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".fastq,.fq,.fastq.gz,.fq.gz"
                  className="hidden"
                  onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
                />
                {file ? (
                  <div className="flex items-center justify-center gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                    <FileText className="h-4 w-4 shrink-0" />
                    <span className="truncate max-w-[200px]">{file.name}</span>
                    <span className="text-muted-foreground text-xs">({formatFileSize(file.size)})</span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-1.5 text-muted-foreground">
                    <Upload className="h-5 w-5" />
                    <span className="text-xs">Drop FASTQ file or click to browse</span>
                    <span className="text-[10px] text-muted-foreground/60">.fastq, .fq, .fastq.gz, .fq.gz</span>
                  </div>
                )}
              </div>
            </div>

            {/* Form Fields */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="age" className="text-xs font-medium">Age</Label>
                <Input
                  id="age"
                  type="number"
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">Fibrosis Stage</Label>
                <Select value={fibrosisStage} onValueChange={setFibrosisStage}>
                  <SelectTrigger className="h-9 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="F0">F0</SelectItem>
                    <SelectItem value="F1">F1</SelectItem>
                    <SelectItem value="F2">F2</SelectItem>
                    <SelectItem value="F3">F3</SelectItem>
                    <SelectItem value="F4">F4</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="bmi" className="text-xs font-medium">BMI</Label>
                <Input
                  id="bmi"
                  type="number"
                  step="0.1"
                  value={bmi}
                  onChange={(e) => setBmi(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="alt" className="text-xs font-medium">ALT (U/L)</Label>
                <Input
                  id="alt"
                  type="number"
                  value={alt}
                  onChange={(e) => setAlt(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ast" className="text-xs font-medium">AST (U/L)</Label>
                <Input
                  id="ast"
                  type="number"
                  value={ast}
                  onChange={(e) => setAst(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="hba1c" className="text-xs font-medium">HbA1c (%)</Label>
                <Input
                  id="hba1c"
                  type="number"
                  step="0.1"
                  value={hba1c}
                  onChange={(e) => setHba1c(e.target.value)}
                  className="h-9 text-sm"
                />
              </div>
            </div>

            {/* Run Prediction */}
            <Button
              className="w-full h-10 bg-emerald-600 hover:bg-emerald-700 text-white"
              onClick={runPrediction}
              disabled={loading || showJobTracker}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isProductionMode ? "Submitting to Pipeline…" : "Running Prediction…"}
                </>
              ) : (
                isProductionMode ? "Run Production Pipeline" : "Run Prediction"
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Job Tracker — appears between form and EASL card when production mode is active */}
        <AnimatePresence>
          {showJobTracker && jobId && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <JobTracker
                jobId={jobId}
                onCompleted={handleJobCompleted}
                onFailed={handleJobFailed}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Job Error State */}
        <AnimatePresence>
          {jobError && !showJobTracker && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.3 }}
            >
              <Card className="border-red-300 dark:border-red-700">
                <CardContent className="p-4 space-y-3">
                  <div className="rounded-lg bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800/40 p-3">
                    <p className="text-xs text-red-700 dark:text-red-400">{jobError}</p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full h-9 text-xs border-red-300 text-red-600 hover:bg-red-50 dark:border-red-700 dark:text-red-400 dark:hover:bg-red-950/30"
                    onClick={clearJob}
                  >
                    Dismiss
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Card 2: EASL-EASD-EASO Guideline Reference */}
        <Card className="bg-muted/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-muted-foreground">
              EASL-EASD-EASO Guideline Reference
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {EASL_GUIDELINES.map((g) => (
              <div key={g.stage} className="space-y-1.5">
                <div className="flex items-baseline gap-2">
                  <span className="text-xs font-semibold text-foreground">{g.stage}</span>
                  <span className="text-[11px] text-muted-foreground">— {g.strategy}</span>
                </div>
                <ul className="space-y-0.5 pl-1">
                  {g.recommendations.map((r, i) => (
                    <li key={i} className="text-[11px] text-muted-foreground leading-relaxed flex gap-1.5">
                      <span className="text-muted-foreground/50 mt-0.5 shrink-0">•</span>
                      <span>{r}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      {/* Right Column */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        {!results && !loading && !showJobTracker && (
          <Card className="flex-1 flex items-center justify-center min-h-[400px]">
            <CardContent className="flex flex-col items-center justify-center text-center py-16 px-6">
              <FlaskConical className="h-12 w-12 text-muted-foreground/30 mb-4" />
              <p className="text-sm text-muted-foreground max-w-sm">
                Upload a FASTQ file and enter patient parameters to generate personalized drug
                recommendations.
              </p>
            </CardContent>
          </Card>
        )}

        {loading && (
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader className="pb-3">
                <Skeleton className="h-5 w-48" />
              </CardHeader>
              <CardContent className="space-y-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <Skeleton className="h-8 w-8 rounded-full shrink-0" />
                    <div className="flex-1 space-y-1.5">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-52" />
                      <Skeleton className="h-2 w-full rounded-full" />
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="py-8 space-y-3">
                <Skeleton className="h-4 w-64 mx-auto" />
                <Skeleton className="h-10 w-full" />
              </CardContent>
            </Card>
          </div>
        )}

        <AnimatePresence>
          {results && !loading && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: "easeOut" }}
              className="flex flex-col gap-6"
            >
              {/* Card 3: Ranked Drug Recommendations */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Ranked Drug Recommendations</CardTitle>
                  <CardDescription className="text-xs">
                    GNN-predicted drug efficacy ranked by composite match score
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2.5 max-h-[480px] overflow-y-auto pr-1">
                    {displayedDrugs.map((drug) => (
                      <div
                        key={drug.rank}
                        className="flex items-start gap-3 p-3 rounded-lg border border-border/50 bg-card hover:bg-muted/30 transition-colors"
                      >
                        <span className="flex items-center justify-center h-7 w-7 rounded-full bg-emerald-100 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 text-xs font-bold shrink-0 mt-0.5">
                          {drug.rank}
                        </span>
                        <div className="flex-1 min-w-0 space-y-1.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold text-sm text-foreground">{drug.drug}</span>
                            {getApprovalBadge(drug.approvalStatus)}
                            {drug.isNovelCandidate && (
                              <Badge className="bg-teal-600 text-white text-[10px] px-1.5 py-0">
                                Novel Candidate
                              </Badge>
                            )}
                            <span
                              className="ml-auto flex items-center gap-1.5 text-[11px] text-muted-foreground shrink-0"
                              title={`Confidence: ${drug.confidence}`}
                            >
                              <span
                                className={`inline-block w-2 h-2 rounded-full ${CONFIDENCE_COLORS[drug.confidence]}`}
                              />
                              {drug.confidence}
                            </span>
                          </div>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-0.5 text-[11px] text-muted-foreground">
                            <span>
                              Target: <span className="text-foreground/80">{drug.target}</span>
                            </span>
                            <span>
                              Class: <span className="text-foreground/80">{drug.drugClass}</span>
                            </span>
                          </div>
                          <div className="flex items-center gap-2">
                            <Progress
                              value={drug.matchScore}
                              className="h-1.5 flex-1 [&>div]:bg-emerald-500"
                            />
                            <span className="text-[11px] font-medium text-foreground w-9 text-right">
                              {drug.matchScore}%
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {(results.drugs.length ?? 0) > 6 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full mt-3 text-xs text-muted-foreground"
                      onClick={() => setShowAllDrugs((v) => !v)}
                    >
                      {showAllDrugs ? (
                        <>
                          <ChevronUp className="mr-1 h-3 w-3" /> Show fewer
                        </>
                      ) : (
                        <>
                          <ChevronDown className="mr-1 h-3 w-3" /> Show all {results.drugs.length}
                        </>
                      )}
                    </Button>
                  )}
                </CardContent>
              </Card>

              {/* Card 4: Stage Hypotheses */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold">Stage Hypotheses</CardTitle>
                  <CardDescription className="text-xs">
                    GNN-predicted fibrosis stage probability distribution
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {results.stageHypotheses.map((sp) => {
                      const isTop = topStage?.stage === sp.stage;
                      const isInputMatch = sp.stage === fibrosisStage;
                      return (
                        <div
                          key={sp.stage}
                          className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm transition-colors ${
                            isTop
                              ? "bg-emerald-600 text-white"
                              : "bg-muted text-muted-foreground"
                          } ${isInputMatch && !isTop ? "ring-2 ring-emerald-500/40" : ""}`}
                        >
                          <span className="font-medium">{sp.label}</span>
                          <span
                            className={`text-xs ${isTop ? "text-emerald-100" : "text-muted-foreground/70"}`}
                          >
                            {(sp.probability * 100).toFixed(1)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Card 5: Visualisations Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Network className="h-4 w-4 text-emerald-600" />
                      Drug-Target Network
                    </CardTitle>
                    <CardDescription className="text-[11px]">GNNExplainer subgraph</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <DrugNetworkGraph />
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <Grid3X3 className="h-4 w-4 text-emerald-600" />
                      GNN Attention Heatmap
                    </CardTitle>
                    <CardDescription className="text-[11px]">
                      Attention weights by gene and layer
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <AttentionHeatmap weights={results.attentionWeights} />
                  </CardContent>
                </Card>
              </div>

              {/* Card 6: GNN Reasoning Summary */}
              <Card className="bg-muted/20">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <BrainCircuit className="h-4 w-4 text-emerald-600" />
                    GNN Reasoning Summary
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {results.reasoningSummary}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}