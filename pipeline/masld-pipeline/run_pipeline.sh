#!/usr/bin/env bash
# ============================================================================
# MASLD Drug Prediction Master Pipeline — Orchestration Script
# ============================================================================
# 
# "Decoding the functional signature of ferroptosis-driven fibrosis 
#  with a personalised GNN"
#
# Banerjee S, Charoensupa R, Vanden Berghe W
# Mae Fah Luang University & University of Antwerp
#
# This script orchestrates the complete 9-stage pipeline from raw GEO data
# to personalized drug predictions using a GraphSAGE GNN.
#
# Usage:
#   chmod +x run_pipeline.sh
#   ./run_pipeline.sh
#
# Requirements:
#   - R >= 4.2 with Bioconductor >= 3.16
#   - Python >= 3.9 with PyTorch + PyTorch Geometric
#   - 32GB RAM recommended (WGCNA + GNN training)
#   - ~50GB disk space for raw GEO data
# ============================================================================

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Pipeline root directory
PIPELINE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${PIPELINE_ROOT}/data"
RESULTS_DIR="${PIPELINE_ROOT}/results"
R_SCRIPTS="${PIPELINE_ROOT}/scripts/R"
PY_SCRIPTS="${PIPELINE_ROOT}/scripts/python"

# Create output directories
mkdir -p "${DATA_DIR}/raw" "${DATA_DIR}/processed" "${RESULTS_DIR}"

echo -e "${PURPLE}============================================================================${NC}"
echo -e "${PURPLE}  MASLD Drug Prediction Master Pipeline${NC}"
echo -e "${PURPLE}  Personalised GraphSAGE GNN for Ferroptosis-Driven Fibrosis${NC}"
echo -e "${PURPLE}============================================================================${NC}"
echo ""
echo -e "${BLUE}Pipeline Root: ${PIPELINE_ROOT}${NC}"
echo -e "${BLUE}Started at: $(date)${NC}"
echo ""

# ============================================================================
# STAGE 1: Metadata Harmonization (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 1: Metadata Harmonization${NC}"
echo -e "${YELLOW}    Downloading and harmonizing metadata from 5 GEO MASLD cohorts${NC}"
echo -e "${YELLOW}    Cohorts: GSE126848, GSE135251, GSE167523, GSE130970, GSE185051${NC}"
cd "${DATA_DIR}/raw"
Rscript "${R_SCRIPTS}/01_metadata_harmonise.R"
echo -e "${GREEN}    ✓ Metadata harmonized: harmonized_MASLD_metadata.csv${NC}"
echo ""

# ============================================================================
# STAGE 2: Batch Correction & Data Integration (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 2: Batch Correction & Data Integration${NC}"
echo -e "${YELLOW}    Combining 5 cohorts + ComBat-seq batch correction${NC}"
Rscript "${R_SCRIPTS}/02_combine_correct_masld.R"
echo -e "${GREEN}    ✓ Batch-corrected: harmonized_MASLD_RNAseq_counts.csv${NC}"
echo ""

# ============================================================================
# STAGE 3: Network Analysis & DGE (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 3: Differential Gene Expression & Pathway Enrichment${NC}"
echo -e "${YELLOW}    limma DGE (~0 + fibrosis_group + age) → GO/KEGG/Reactome/MSigDB${NC}"
Rscript "${R_SCRIPTS}/03_network_analysis.R"
echo -e "${GREEN}    ✓ DGE results + PPI network + enrichment outputs${NC}"
echo ""

# ============================================================================
# STAGE 4: Ferroptosis Analysis (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 4: Ferroptosis Gene Analysis${NC}"
echo -e "${YELLOW}    GSVA scores + GSEA + ferroptosis DEG visualization${NC}"
Rscript "${R_SCRIPTS}/04_ferroptosis_analysis.R"
echo -e "${GREEN}    ✓ Ferroptosis analysis complete${NC}"
echo ""

# ============================================================================
# STAGE 5: TF Activity Analysis (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 5: Transcription Factor Activity (DoRothEA/VIPER)${NC}"
echo -e "${YELLOW}    TF activity calculation + differential analysis${NC}"
Rscript "${R_SCRIPTS}/05_tf_activity_analysis.R"
echo -e "${GREEN}    ✓ TF activity heatmap saved${NC}"
echo ""

# ============================================================================
# STAGE 6: Score Correlation Analysis (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 6: Correlation Analysis${NC}"
echo -e "${YELLOW}    Metadata × Ferroptosis scores (Pearson + Spearman)${NC}"
Rscript "${R_SCRIPTS}/06_score_correlation.R"
echo -e "${GREEN}    ✓ Correlation results saved${NC}"
echo ""

# ============================================================================
# STAGE 7: Heatmap Visualization (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 7: Publication-Grade Heatmaps${NC}"
echo -e "${YELLOW}    DEG heatmaps + ferroptosis gene visualization${NC}"
Rscript "${R_SCRIPTS}/07_masld_heatmaps.R"
echo -e "${GREEN}    ✓ Heatmaps generated${NC}"
echo ""

# ============================================================================
# STAGE 8: WGCNA Visualization (R)
# ============================================================================
echo -e "${GREEN}>>> STAGE 8: WGCNA Module Visualization${NC}"
echo -e "${YELLOW}    Fibrosis module GO enrichment + hub genes + eigengene correlation${NC}"
Rscript "${R_SCRIPTS}/08_wgcna_visualization.R"
echo -e "${GREEN}    ✓ WGCNA Figure 8 panels generated${NC}"
echo ""

# ============================================================================
# STAGE 9: GraphSAGE GNN Pipeline (Python)
# ============================================================================
echo -e "${GREEN}>>> STAGE 9: GraphSAGE GNN Drug Prediction${NC}"
echo -e "${YELLOW}    Knowledge Graph construction + GNN training + inductive evaluation${NC}"
echo -e "${YELLOW}    This stage requires PyTorch + PyTorch Geometric${NC}"
echo -e "${YELLOW}    Estimated runtime: 30-60 minutes (GPU recommended)${NC}"
cd "${PIPELINE_ROOT}"
python "${PY_SCRIPTS}/09_graphsage_pipeline.py"
echo -e "${GREEN}    ✓ GNN training complete — results in results_final/${NC}"
echo ""

# ============================================================================
# COMPLETE
# ============================================================================
echo -e "${PURPLE}============================================================================${NC}"
echo -e "${GREEN}  PIPELINE COMPLETE${NC}"
echo -e "${PURPLE}============================================================================${NC}"
echo ""
echo -e "${BLUE}Results directory: ${RESULTS_DIR}${NC}"
echo -e "${BLUE}Finished at: $(date)${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "  1. Review results in ${RESULTS_DIR}/"
echo -e "  2. Launch the web tool: cd web-tool && npm install && npm run dev"
echo -e "  3. For publication: see docs/REPRODUCIBILITY.md"
echo ""
