"use client";

import { motion } from "framer-motion";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  MODEL_METRICS,
  CONFUSION_MATRIX,
  SHAP_GENES,
  LOCO_AUC_BY_CLASS,
} from "@/lib/masld-data";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  ResponsiveContainer,
  ReferenceLine,
  LineChart,
  Line,
  Tooltip,
} from "recharts";

const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.08, duration: 0.45, ease: "easeOut" },
  }),
};

const calibrationData = [
  { predicted: 0.1, observed: 0.08 },
  { predicted: 0.2, observed: 0.22 },
  { predicted: 0.3, observed: 0.28 },
  { predicted: 0.4, observed: 0.42 },
  { predicted: 0.5, observed: 0.48 },
  { predicted: 0.6, observed: 0.63 },
  { predicted: 0.7, observed: 0.68 },
  { predicted: 0.8, observed: 0.78 },
  { predicted: 0.9, observed: 0.91 },
];

const metricCards = [
  { value: MODEL_METRICS.auroc, label: "Area Under ROC Curve" },
  { value: MODEL_METRICS.f1Score, label: "F1 Score" },
  { value: MODEL_METRICS.brierScore, label: "Brier Score" },
  { value: MODEL_METRICS.auprc, label: "Avg. Precision" },
];

export default function ValidationTab() {
  const { tp, fn, fp, tn } = CONFUSION_MATRIX;
  const maxVal = Math.max(tp, fn, fp, tn);

  const matrixCells = [
    { value: tn, label: "TN", row: 0, col: 0 },
    { value: fp, label: "FP", row: 0, col: 1 },
    { value: fn, label: "FN", row: 1, col: 0 },
    { value: tp, label: "TP", row: 1, col: 1 },
  ];

  const getMatrixBg = (val: number) => {
    const ratio = val / maxVal;
    if (ratio > 0.8) return "bg-emerald-600 text-white";
    if (ratio > 0.6) return "bg-emerald-500 text-white";
    if (ratio > 0.4) return "bg-emerald-400/70 text-white";
    return "bg-emerald-300/50 text-emerald-900";
  };

  const shapData = [...SHAP_GENES].reverse();

  return (
    <div className="space-y-6">
      {/* Top Section: Two-Column Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ---- Left Column ---- */}

        {/* Card 1: Model Performance */}
        <motion.div
          custom={0}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
        >
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-semibold text-slate-800">
                Model Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {metricCards.map((m) => (
                  <div
                    key={m.label}
                    className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 text-center"
                  >
                    <p className="text-3xl font-bold tracking-tight text-slate-900">
                      {m.value.toFixed(2)}
                    </p>
                    <p className="mt-1 text-xs text-slate-500">{m.label}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Card 2: Confusion Matrix */}
        <motion.div
          custom={1}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
        >
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-semibold text-slate-800">
                Confusion Matrix
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {/* Matrix Table */}
              <div className="mx-auto w-fit">
                {/* Empty corner + column headers */}
                <div className="grid grid-cols-[auto_auto_auto] gap-1">
                  <div />
                  <div className="flex h-10 w-24 items-center justify-center text-xs font-medium text-slate-500">
                    Pred F0–F1
                  </div>
                  <div className="flex h-10 w-24 items-center justify-center text-xs font-medium text-slate-500">
                    Pred F2–F4
                  </div>

                  {/* Row 1: True F0–F1 */}
                  <div className="flex h-12 w-24 items-center justify-center text-xs font-medium text-slate-500">
                    True F0–F1
                  </div>
                  {matrixCells
                    .filter((c) => c.row === 0)
                    .sort((a, b) => a.col - b.col)
                    .map((c) => (
                      <div
                        key={c.label}
                        className={`flex h-12 w-24 flex-col items-center justify-center rounded-md font-semibold ${getMatrixBg(
                          c.value
                        )}`}
                      >
                        <span className="text-xl leading-none">{c.value}</span>
                        <span className="mt-0.5 text-[10px] font-medium opacity-80">
                          {c.label}
                        </span>
                      </div>
                    ))}

                  {/* Row 2: True F2–F4 */}
                  <div className="flex h-12 w-24 items-center justify-center text-xs font-medium text-slate-500">
                    True F2–F4
                  </div>
                  {matrixCells
                    .filter((c) => c.row === 1)
                    .sort((a, b) => a.col - b.col)
                    .map((c) => (
                      <div
                        key={c.label}
                        className={`flex h-12 w-24 flex-col items-center justify-center rounded-md font-semibold ${getMatrixBg(
                          c.value
                        )}`}
                      >
                        <span className="text-xl leading-none">{c.value}</span>
                        <span className="mt-0.5 text-[10px] font-medium opacity-80">
                          {c.label}
                        </span>
                      </div>
                    ))}
                </div>
              </div>

              {/* Derived metrics */}
              <div className="flex items-center justify-center gap-6 text-sm">
                <div className="text-center">
                  <p className="font-bold text-slate-800">
                    {Math.round(MODEL_METRICS.sensitivity * 100)}%
                  </p>
                  <p className="text-xs text-slate-500">Sensitivity</p>
                </div>
                <div className="h-6 w-px bg-slate-200" />
                <div className="text-center">
                  <p className="font-bold text-slate-800">
                    {Math.round(MODEL_METRICS.specificity * 100)}%
                  </p>
                  <p className="text-xs text-slate-500">Specificity</p>
                </div>
                <div className="h-6 w-px bg-slate-200" />
                <div className="text-center">
                  <p className="font-bold text-slate-800">
                    {Math.round(MODEL_METRICS.accuracy * 100)}%
                  </p>
                  <p className="text-xs text-slate-500">Accuracy</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* ---- Right Column ---- */}

        {/* Card 3: Calibration & Reliability */}
        <motion.div
          custom={2}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
        >
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-semibold text-slate-800">
                Calibration &amp; Reliability
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-4 text-sm">
                <div>
                  <span className="text-slate-500">ECE: </span>
                  <span className="font-semibold text-slate-800">
                    {MODEL_METRICS.ece.toFixed(3)}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500">MCE: </span>
                  <span className="font-semibold text-slate-800">
                    {MODEL_METRICS.mce.toFixed(3)}
                  </span>
                </div>
              </div>

              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={calibrationData}
                    margin={{ top: 10, right: 16, bottom: 0, left: 0 }}
                  >
                    <ReferenceLine
                      segment={[
                        { x: 0, y: 0 },
                        { x: 1, y: 1 },
                      ]}
                      stroke="#94a3b8"
                      strokeDasharray="4 3"
                      strokeWidth={1.5}
                    />
                    <XAxis
                      dataKey="predicted"
                      domain={[0, 1]}
                      ticks={[0, 0.5, 1]}
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      axisLine={{ stroke: "#cbd5e1" }}
                      tickLine={false}
                      label={{
                        value: "Mean Predicted Probability",
                        position: "insideBottom",
                        offset: -2,
                        fontSize: 10,
                        fill: "#94a3b8",
                      }}
                    />
                    <YAxis
                      domain={[0, 1]}
                      ticks={[0, 0.5, 1]}
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      axisLine={{ stroke: "#cbd5e1" }}
                      tickLine={false}
                      label={{
                        value: "Observed Frequency",
                        angle: -90,
                        position: "insideLeft",
                        offset: 10,
                        fontSize: 10,
                        fill: "#94a3b8",
                      }}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 8,
                        border: "1px solid #e2e8f0",
                        fontSize: 12,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                      }}
                      formatter={(val: number) => [val.toFixed(2), "Model"]}
                      labelFormatter={(lbl) => `Predicted: ${lbl}`}
                    />
                    <Line
                      type="monotone"
                      dataKey="observed"
                      stroke="#0d9488"
                      strokeWidth={2.5}
                      dot={{ r: 4, fill: "#0d9488", strokeWidth: 0 }}
                      activeDot={{ r: 5, fill: "#0d9488", strokeWidth: 2, stroke: "#fff" }}
                      name="Model"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Card 4: Feature Importance (SHAP) */}
        <motion.div
          custom={3}
          variants={fadeUp}
          initial="hidden"
          animate="visible"
        >
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-lg font-semibold text-slate-800">
                Feature Importance (SHAP)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={shapData}
                    layout="vertical"
                    margin={{ top: 4, right: 40, bottom: 4, left: 4 }}
                  >
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      axisLine={{ stroke: "#cbd5e1" }}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="gene"
                      width={72}
                      tick={{ fontSize: 12, fill: "#334155", fontWeight: 500 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 8,
                        border: "1px solid #e2e8f0",
                        fontSize: 12,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                      }}
                      formatter={(val: number) => [val.toFixed(3), "SHAP Value"]}
                    />
                    <Bar dataKey="shapValue" radius={[0, 4, 4, 0]} barSize={20}>
                      {shapData.map((entry, idx) => (
                        <Cell
                          key={idx}
                          fill={
                            entry.direction === "down"
                              ? "#10b981"
                              : "#f59e0b"
                          }
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              {/* Legend */}
              <div className="mt-2 flex items-center justify-center gap-4 text-xs text-slate-500">
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-emerald-500" />
                  Down-regulated
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="inline-block h-2.5 w-2.5 rounded-sm bg-amber-500" />
                  Up-regulated
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* ---- Bottom Section: Methodology ---- */}
      <motion.div
        custom={4}
        variants={fadeUp}
        initial="hidden"
        animate="visible"
      >
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold text-slate-800">
              Methodology &amp; Scientific Framework
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" className="w-full">
              <AccordionItem value="data-integration">
                <AccordionTrigger className="text-sm font-medium text-slate-700 hover:no-underline">
                  Data Integration &amp; Personalisation
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-slate-600">
                  Transcriptomic profiles from five independent GEO cohorts were harmonised using batch-correction
                  methods to remove inter-study technical variation while preserving biological signal. A 437-patient
                  analysis subset was defined by the availability of paired histological fibrosis staging (F0–F4).
                  Differential expression analysis contrasting late-stage (F2–F4) versus early-stage (F0–F1) biopsies
                  yielded patient-specific feature vectors. CIBERSORTx single-cell deconvolution with a
                  liver-specific reference matrix was applied to estimate cell-type proportions, enriching each
                  patient profile with microenvironmental context.
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="knowledge-graph">
                <AccordionTrigger className="text-sm font-medium text-slate-700 hover:no-underline">
                  Knowledge Graph Construction
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-slate-600">
                  Multi-omic relationships—including ferroptosis regulators, drug-target interactions, and
                  disease-associated gene modules—were integrated into a heterogeneous knowledge graph. The graph
                  was enriched with high-confidence protein-protein interactions (STRING ≥ 0.7) and pathway
                  co-membership edges derived from Reactome. This expansion transformed the base gene–drug bipartite
                  structure into a densely connected graph that captures both direct mechanistic links and
                  higher-order functional associations relevant to MASLD progression.
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="gnn-framework">
                <AccordionTrigger className="text-sm font-medium text-slate-700 hover:no-underline">
                  Graph Neural Network Framework
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-slate-600">
                  An inductive GraphSAGE architecture was employed to learn functional node embeddings by
                  aggregating neighbourhood information across the knowledge graph. The model uses a two-layer
                  mean-aggregation scheme that enables zero-shot predictions for drugs absent from the training
                  set, provided their target genes are represented in the graph. This inductive design supports
                  generalisation to novel pharmacological classes and supports mechanistic interpretability via
                  neighbourhood-level attention weights.
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="validation-strategy">
                <AccordionTrigger className="text-sm font-medium text-slate-700 hover:no-underline">
                  Validation Strategy
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-slate-600">
                  A Leave-One-Class-Out (LOCO) cross-validation protocol was adopted to evaluate the model's
                  capacity to generalise to previously unseen pharmacological classes. In each fold, all drugs
                  belonging to one class were withheld from training and used exclusively for testing.
                  GNNExplainer was applied to generate edge-level attribution maps, linking predictions to
                  interpretable biological mechanisms. Feature ablation studies quantified the contribution of
                  individual gene modules and cell-type proportions to overall predictive performance.
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="translational">
                <AccordionTrigger className="text-sm font-medium text-slate-700 hover:no-underline">
                  Translational Significance
                </AccordionTrigger>
                <AccordionContent className="text-sm leading-relaxed text-slate-600">
                  The model bridges patient-specific transcriptomic states to therapeutic hypotheses by mapping
                  molecular signatures onto the drug knowledge graph and ranking candidates by predicted
                  fibrosis-stage benefit. This approach aligns with EASL-EASD-EASO guidelines for
                  stage-specific MASLD management, offering a data-driven complement to current clinical
                  decision-making. By incorporating both approved and investigational agents, the framework
                  supports rational drug repurposing and prioritisation of candidates for further preclinical
                  validation.
                </AccordionContent>
              </AccordionItem>
            </Accordion>

            {/* LOCO Cross-Validation Chart */}
            <div className="mt-8 space-y-4">
              <div className="flex items-baseline gap-3">
                <h3 className="text-sm font-semibold text-slate-700">
                  LOCO Cross-Validation
                </h3>
                <Badge
                  variant="secondary"
                  className="bg-teal-50 text-teal-700 hover:bg-teal-100"
                >
                  Mean AUROC: 0.942
                </Badge>
              </div>

              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={LOCO_AUC_BY_CLASS}
                    layout="vertical"
                    margin={{ top: 4, right: 40, bottom: 4, left: 4 }}
                  >
                    <XAxis
                      type="number"
                      domain={[0.88, 1.0]}
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      axisLine={{ stroke: "#cbd5e1" }}
                      tickLine={false}
                    />
                    <YAxis
                      type="category"
                      dataKey="drugClass"
                      width={110}
                      tick={{ fontSize: 11, fill: "#334155" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 8,
                        border: "1px solid #e2e8f0",
                        fontSize: 12,
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                      }}
                      formatter={(val: number) => [val.toFixed(3), "AUROC"]}
                    />
                    <Bar dataKey="auc" radius={[0, 4, 4, 0]} barSize={18}>
                      {LOCO_AUC_BY_CLASS.map((_, idx) => (
                        <Cell
                          key={idx}
                          fill="#0d9488"
                          opacity={0.7 + (idx * 0.05)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}