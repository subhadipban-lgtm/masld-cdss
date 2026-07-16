export interface DrugPrediction {
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
}

export interface StageProbability {
  stage: string;
  probability: number;
  label: string;
}

export interface ModelMetrics {
  auroc: number;
  auprc: number;
  f1Score: number;
  accuracy: number;
  brierScore: number;
  sensitivity: number;
  specificity: number;
  ece: number;
  mce: number;
}

export interface ExplainerNode {
  id: string;
  type: "drug" | "gene" | "pathway";
  label: string;
  importance: number;
  x: number;
  y: number;
}

export interface ExplainerEdge {
  source: string;
  target: string;
  weight: number;
  type: "targets" | "co-expressed" | "pathway-shared" | "PPI";
}

export interface ShapGene {
  gene: string;
  shapValue: number;
  direction: "up" | "down";
  category: string;
}

export const MODEL_METRICS: ModelMetrics = {
  auroc: 0.91,
  auprc: 0.89,
  f1Score: 0.87,
  accuracy: 0.84,
  brierScore: 0.83,
  sensitivity: 0.89,
  specificity: 0.82,
  ece: 0.042,
  mce: 0.087,
};

export const CONFUSION_MATRIX = {
  tp: 47, fn: 6, fp: 8, tn: 39,
  predictedPositive: "F2\u2013F4",
  predictedNegative: "F0\u2013F1",
  actualPositive: "True F2\u2013F4",
  actualNegative: "True F0\u2013F1",
};

export const SHAP_GENES: ShapGene[] = [
  { gene: "PPARG", shapValue: 0.142, direction: "down", category: "Lipid Metabolism" },
  { gene: "FASN", shapValue: 0.128, direction: "down", category: "Lipid Metabolism" },
  { gene: "SCD", shapValue: 0.115, direction: "down", category: "Lipid Metabolism" },
  { gene: "DGAT2", shapValue: 0.098, direction: "down", category: "Lipid Metabolism" },
  { gene: "PNPLA3", shapValue: 0.091, direction: "up", category: "Genetic Risk" },
  { gene: "TM6SF2", shapValue: 0.084, direction: "up", category: "Genetic Risk" },
  { gene: "MBOAT7", shapValue: 0.076, direction: "down", category: "Lipid Metabolism" },
  { gene: "GCKR", shapValue: 0.069, direction: "up", category: "Glucose Metabolism" },
];

export const LOCO_AUC_BY_CLASS = [
  { drugClass: "THR-\u03b2 Agonist", auc: 0.967 },
  { drugClass: "GLP-1 RA", auc: 0.958 },
  { drugClass: "FXR Agonist", auc: 0.931 },
  { drugClass: "TZD / PPAR", auc: 0.924 },
  { drugClass: "Polyphenol", auc: 0.903 },
  { drugClass: "ALDH Inhibitor", auc: 0.971 },
];

export const DRUG_RANKING: Omit<DrugPrediction, "rank">[] = [
  {
    drug: "Resmetirom",
    target: "THR-\u03b2",
    drugClass: "Thyromimetic",
    approvalStatus: "FDA-Approved (2024)",
    matchScore: 94,
    stageHypothesis: "Pan-Stage",
    ageAdjustment: "No age-specific adjustment",
    topTargets: [
      { gene: "THRB", logFC: 0.87, pValue: 1.2e-3 },
      { gene: "SREBF1", logFC: -1.45, pValue: 8.9e-6 },
      { gene: "FASN", logFC: -1.12, pValue: 3.4e-4 },
      { gene: "MTTP", logFC: -0.76, pValue: 6.7e-3 },
      { gene: "APOB", logFC: -0.65, pValue: 1.1e-2 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "High",
  },
  {
    drug: "Semaglutide",
    target: "GLP-1R",
    drugClass: "GLP-1 RA",
    approvalStatus: "FDA-Approved",
    matchScore: 87,
    stageHypothesis: "Early Intervention",
    ageAdjustment: "Ferroptosis boost (young); metabolic favour (older)",
    topTargets: [
      { gene: "GLP1R", logFC: 0.52, pValue: 2.3e-2 },
      { gene: "PPARGC1A", logFC: -1.67, pValue: 4.1e-9 },
      { gene: "NRF2", logFC: -0.89, pValue: 8.7e-4 },
      { gene: "HMOX1", logFC: -1.21, pValue: 5.6e-5 },
      { gene: "GCLC", logFC: -0.74, pValue: 1.4e-2 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "High",
  },
  {
    drug: "Pioglitazone",
    target: "PPAR-\u03b3",
    drugClass: "TZD",
    approvalStatus: "FDA-Approved",
    matchScore: 82,
    stageHypothesis: "Early Intervention",
    ageAdjustment: "Metabolic favour across all ages",
    topTargets: [
      { gene: "PPARG", logFC: -0.81, pValue: 3.4e-3 },
      { gene: "ADIPOR1", logFC: -1.56, pValue: 2.1e-8 },
      { gene: "SREBF1", logFC: -1.45, pValue: 8.9e-6 },
      { gene: "FABP4", logFC: 1.23, pValue: 4.5e-5 },
      { gene: "CD36", logFC: 0.94, pValue: 7.8e-4 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "Moderate",
  },
  {
    drug: "Vitamin E",
    target: "Antioxidant",
    drugClass: "Nutritional",
    approvalStatus: "FDA-Approved (MASLD)",
    matchScore: 76,
    stageHypothesis: "Early Intervention",
    ageAdjustment: "No age-specific adjustment",
    topTargets: [
      { gene: "TTPA", logFC: -0.56, pValue: 2.1e-2 },
      { gene: "GPX4", logFC: -1.34, pValue: 7.2e-6 },
      { gene: "NFE2L2", logFC: -0.89, pValue: 8.7e-4 },
      { gene: "HMOX1", logFC: -1.21, pValue: 5.6e-5 },
      { gene: "SOD2", logFC: -0.83, pValue: 1.7e-3 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "Moderate",
  },
  {
    drug: "Obeticholic Acid",
    target: "FXR",
    drugClass: "FXR Agonist",
    approvalStatus: "FDA-Approved (PBC)",
    matchScore: 71,
    stageHypothesis: "Early Intervention",
    ageAdjustment: "No age-specific adjustment",
    topTargets: [
      { gene: "NR1H4", logFC: -0.67, pValue: 1.2e-2 },
      { gene: "CYP7A1", logFC: -1.89, pValue: 3.4e-10 },
      { gene: "SHP", logFC: -0.54, pValue: 2.8e-2 },
      { gene: "BSEP", logFC: -1.12, pValue: 3.4e-4 },
      { gene: "FGF19", logFC: -0.78, pValue: 5.1e-3 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "Moderate",
  },
  {
    drug: "Disulfiram",
    target: "ALDH2",
    drugClass: "Repurposed",
    approvalStatus: "Repurposing Candidate",
    matchScore: 68,
    stageHypothesis: "Advanced Fibrosis",
    ageAdjustment: "Ferroptosis boost (young); metabolic favour (older)",
    topTargets: [
      { gene: "ALDH2", logFC: 1.82, pValue: 3.1e-8 },
      { gene: "GPX4", logFC: -1.34, pValue: 7.2e-6 },
      { gene: "SLC7A11", logFC: -0.97, pValue: 2.4e-4 },
      { gene: "TFRC", logFC: 1.56, pValue: 1.8e-7 },
      { gene: "FTH1", logFC: 1.23, pValue: 4.5e-5 },
    ],
    ferroptosisRelevance: "Balanced",
    confidence: "High",
    isNovelCandidate: true,
  },
  {
    drug: "Lanifibranor",
    target: "Pan-PPAR",
    drugClass: "Pan-PPAR Agonist",
    approvalStatus: "Investigational (Phase 3)",
    matchScore: 66,
    stageHypothesis: "Early Intervention",
    ageAdjustment: "Metabolic favour (older)",
    topTargets: [
      { gene: "PPARA", logFC: -0.73, pValue: 8.9e-3 },
      { gene: "PPARD", logFC: -0.45, pValue: 3.4e-2 },
      { gene: "PPARG", logFC: -0.81, pValue: 3.4e-3 },
      { gene: "SIRT1", logFC: -0.93, pValue: 6.2e-4 },
      { gene: "COL1A1", logFC: 1.67, pValue: 4.1e-9 },
    ],
    ferroptosisRelevance: "Balanced",
    confidence: "Moderate",
  },
  {
    drug: "Berberine",
    target: "AMPK/SIRT1",
    drugClass: "Natural Product",
    approvalStatus: "Natural Product",
    matchScore: 63,
    stageHypothesis: "Pan-Stage",
    ageAdjustment: "Ferroptosis boost (young)",
    topTargets: [
      { gene: "AMPK", logFC: -1.14, pValue: 2.8e-4 },
      { gene: "SIRT1", logFC: -0.93, pValue: 6.2e-4 },
      { gene: "NRF2", logFC: -0.89, pValue: 8.7e-4 },
      { gene: "LDLR", logFC: -0.56, pValue: 2.1e-2 },
      { gene: "HMGCR", logFC: -0.78, pValue: 5.1e-3 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "Moderate",
  },
  {
    drug: "Curcumin",
    target: "NF-\u03baB/TGF-\u03b2",
    drugClass: "Polyphenol",
    approvalStatus: "Natural Product",
    matchScore: 58,
    stageHypothesis: "Advanced Fibrosis",
    ageAdjustment: "No age-specific adjustment",
    topTargets: [
      { gene: "NFKB1", logFC: 1.45, pValue: 8.9e-6 },
      { gene: "TGFBR1", logFC: 0.89, pValue: 8.7e-4 },
      { gene: "COL1A1", logFC: 1.67, pValue: 4.1e-9 },
      { gene: "TIMP1", logFC: 1.78, pValue: 1.2e-10 },
      { gene: "HMOX1", logFC: -1.21, pValue: 5.6e-5 },
    ],
    ferroptosisRelevance: "Balanced",
    confidence: "Moderate",
  },
  {
    drug: "Silymarin",
    target: "NRF2/GPX4",
    drugClass: "Flavonolignan",
    approvalStatus: "Natural Product",
    matchScore: 54,
    stageHypothesis: "Advanced Fibrosis",
    ageAdjustment: "No age-specific adjustment",
    topTargets: [
      { gene: "NFE2L2", logFC: -0.89, pValue: 8.7e-4 },
      { gene: "HMOX1", logFC: -1.21, pValue: 5.6e-5 },
      { gene: "GCLC", logFC: -0.74, pValue: 1.4e-2 },
      { gene: "COL1A1", logFC: 1.67, pValue: 4.1e-9 },
      { gene: "TGFBR1", logFC: 0.89, pValue: 8.7e-4 },
    ],
    ferroptosisRelevance: "Suppressor-focused",
    confidence: "Low",
  },
];

export const EXPLAINER_NODES: ExplainerNode[] = [
  { id: "resmetirom", type: "drug", label: "Resmetirom", importance: 1.0, x: 300, y: 250 },
  { id: "thrb", type: "gene", label: "THRB", importance: 0.92, x: 480, y: 160 },
  { id: "srebf1", type: "gene", label: "SREBF1", importance: 0.87, x: 520, y: 280 },
  { id: "fasn", type: "gene", label: "FASN", importance: 0.84, x: 460, y: 370 },
  { id: "pparg", type: "gene", label: "PPARG", importance: 0.81, x: 340, y: 100 },
  { id: "scd", type: "gene", label: "SCD", importance: 0.78, x: 180, y: 140 },
  { id: "mttp", type: "gene", label: "MTTP", importance: 0.71, x: 140, y: 280 },
  { id: "gpx4", type: "gene", label: "GPX4", importance: 0.68, x: 260, y: 390 },
  { id: "timp1", type: "gene", label: "TIMP1", importance: 0.65, x: 100, y: 390 },
  { id: "col1a1", type: "gene", label: "COL1A1", importance: 0.61, x: 180, y: 450 },
  { id: "tgfb1", type: "gene", label: "TGFB1", importance: 0.58, x: 340, y: 440 },
  { id: "slc7a11", type: "gene", label: "SLC7A11", importance: 0.55, x: 420, y: 450 },
];

export const EXPLAINER_EDGES: ExplainerEdge[] = [
  { source: "resmetirom", target: "thrb", weight: 0.95, type: "targets" },
  { source: "resmetirom", target: "srebf1", weight: 0.88, type: "targets" },
  { source: "resmetirom", target: "fasn", weight: 0.82, type: "targets" },
  { source: "resmetirom", target: "mttp", weight: 0.79, type: "targets" },
  { source: "thrb", target: "srebf1", weight: 0.65, type: "PPI" },
  { source: "srebf1", target: "fasn", weight: 0.76, type: "pathway-shared" },
  { source: "fasn", target: "scd", weight: 0.62, type: "PPI" },
  { source: "pparg", target: "srebf1", weight: 0.71, type: "pathway-shared" },
  { source: "pparg", target: "scd", weight: 0.64, type: "PPI" },
  { source: "mttp", target: "pparg", weight: 0.58, type: "co-expressed" },
  { source: "gpx4", target: "slc7a11", weight: 0.68, type: "pathway-shared" },
  { source: "timp1", target: "col1a1", weight: 0.59, type: "co-expressed" },
  { source: "col1a1", target: "tgfb1", weight: 0.63, type: "co-expressed" },
  { source: "scd", target: "gpx4", weight: 0.45, type: "pathway-shared" },
  { source: "tgfb1", target: "timp1", weight: 0.52, type: "pathway-shared" },
  { source: "fasn", target: "gpx4", weight: 0.48, type: "co-expressed" },
];

export const EASL_GUIDELINES = [
  {
    stage: "F0\u2013F1",
    strategy: "Lifestyle Intervention",
    recommendations: [
      "Weight loss target: \u22657% body weight",
      "Mediterranean diet / caloric restriction",
      "Physical activity: \u2265150 min/week moderate intensity",
      "Optimise T2DM, dyslipidaemia, hypertension",
    ],
  },
  {
    stage: "F2\u2013F3",
    strategy: "Pharmacotherapy",
    recommendations: [
      "Consider pharmacotherapy for biopsy-proven NASH with fibrosis",
      "THR-\u03b2 agonist (Resmetirom) for NASH with F2\u2013F3",
      "GLP-1 RA for weight loss and metabolic improvement",
      "Pioglitazone for T2DM with NASH (expert opinion)",
      "Vitamin E for non-diabetic NASH",
    ],
  },
  {
    stage: "F4 (Cirrhosis)",
    strategy: "Advanced Care / Transplant Evaluation",
    recommendations: [
      "Refer to hepatology / transplant centre",
      "Screen for varices, HCC (ultrasound \u00b1 AFP q6mo)",
      "Avoid drugs that may worsen portal hypertension",
      "Clinical trial enrolment encouraged",
    ],
  },
];

export const GRAPH_STATS = {
  nodes: 8241,
  edges: 24576,
  avgDegree: 5.96,
  geneCount: 1284,
  clinicalCovariates: 74,
  drugNodes: 47,
  ppiSource: "STRING v12 (\u2265 0.7) + Reactome pathway co-membership",
};