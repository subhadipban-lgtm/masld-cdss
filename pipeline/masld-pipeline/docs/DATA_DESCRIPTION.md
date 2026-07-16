# Data File Descriptions

This document describes all input and output data files used in the MASLD Drug Prediction Pipeline.

## Input Files

### Raw GEO Data (Stage 1-2)

| File | Type | Description |
|------|------|-------------|
| `GSE126848_raw_counts_GRCh38.p13_NCBI.tsv` | TSV | Raw gene count matrix for GSE126848 cohort |
| `GSE135251_raw_counts_GRCh38.p13_NCBI.tsv` | TSV | Raw gene count matrix for GSE135251 cohort |
| `GSE167523_raw_counts_GRCh38.p13_NCBI.tsv` | TSV | Raw gene count matrix for GSE167523 cohort |
| `GSE130970_raw_counts_GRCh38.p13_NCBI.tsv` | TSV | Raw gene count matrix for GSE130970 cohort |
| `GSE185051_raw_counts_GRCh38.p13_NCBI.tsv` | TSV | Raw gene count matrix for GSE185051 cohort |

### Auxiliary Data Files

| File | Type | Description | Source |
|------|------|-------------|--------|
| `ferroptosis_driver.csv` | CSV | FerrDb V2 ferroptosis driver gene list (column: `symbol`) | http://www.zhounan.org/ferrdb/ |
| `ferroptosis_suppressor.csv` | CSV | FerrDb V2 ferroptosis suppressor gene list (column: `symbol`) | http://www.zhounan.org/ferrdb/ |
| `MASLD molecules.csv` | CSV | Literature-curated drug-target pairs (columns: `Drug Molecule`, `Target(s) Mentioned in Document`) | Manuscript Supplementary |
| `masld_drug_gene_kg.gexf` | GEXF | Baseline (General) knowledge graph | Stage 5 output or pre-built |
| `masld_personalized_kg.gexf` | GEXF | Personalised knowledge graph with DGE features | Stage 5 output |
| `masld_expression_504_samples.csv` | CSV | Expression matrix for causal discovery (patients × genes) | Stage 2 output |
| `WGCNA_fibrosis_module_genes.csv` | CSV | WGCNA blue module gene list (column: `genes`) | WGCNA analysis output |

## Output Files

### Stage 1-2: Harmonized Data

| File | Type | Description |
|------|------|-------------|
| `harmonized_MASLD_metadata.csv` | CSV | Harmonized clinical metadata: `sample_id`, `disease_status`, `fibrosis_stage`, `age`, `sex`, `bmi`, `batch` |
| `harmonized_MASLD_RNAseq_counts.csv` | CSV | Batch-corrected (ComBat-seq) gene count matrix: `GeneID` + sample columns |
| `normalized_expression_matrix.rds` | RDS | Normalized (log2-CPM, quantile) expression matrix (genes × samples) |

### Stage 3: DGE & Enrichment

| File | Type | Description |
|------|------|-------------|
| `DGE_Full_Results_Fibrosis_and_Age.csv` | CSV | Full limma DGE results with both `Late_vs_Early` and `Age` coefficients: `GeneSymbol`, `logFC`, `P.Value`, `adj.P.Val`, `logFC_age`, `P.Value_age`, `adj.P.Val_age` |
| `enrichment_results/GO_BP_enrichment.csv` | CSV | GO Biological Process enrichment results |
| `enrichment_results/KEGG_enrichment.csv` | CSV | KEGG pathway enrichment results |
| `enrichment_results/Reactome_enrichment.csv` | CSV | Reactome pathway enrichment results |
| `enrichment_results/MSigDB_Hallmark_enrichment.csv` | CSV | MSigDB Hallmark gene set enrichment results |
| `networks/PPI_Network.graphml` | GraphML | Protein-protein interaction network (igraph format) |
| `networks/PPI_Network.sif` | SIF | PPI network in Simple Interaction Format (Cytoscape-compatible) |
| `networks/PPI_Network_EdgeList.csv` | CSV | PPI network edge list with STRING combined scores |
| `networks/PPI_Network_NodeList.csv` | CSV | PPI network node list with logFC and adj.P.Val annotations |

### Stage 4-5: Ferroptosis & TF Analysis

| File | Type | Description |
|------|------|-------------|
| `harmonized_ferroptosis_GSVA_scores.csv` | CSV | GSVA scores for ferroptosis driver/suppressor gene sets per sample: `SampleID`, `GSVA_Drivers_Score`, `GSVA_Suppressors_Score` |
| `metadata_ferroptosis_correlation_results.csv` | CSV | Pearson/Spearman correlations between metadata features and ferroptosis scores |

### Stage 9: GNN Outputs

| File | Type | Description |
|------|------|-------------|
| `masld_personalized_kg_enhanced.pt` | PyTorch | Trained GraphSAGE model (Personalised KG) |
| `masld_drug_gene_kg_enhanced.pt` | PyTorch | Trained GraphSAGE model (General KG) |
| `General KG (Inductive)_test_predictions.csv` | CSV | Inductive test predictions for General KG |
| `Personalized KG (Inductive)_test_predictions.csv` | CSV | Inductive test predictions for Personalised KG |
| `all_holdout_drugs_top_targets.csv` | CSV | Top predicted targets for all holdout drugs with DGE features |
| `comparative_regulatory_hubs.csv` | CSV | Comparative regulatory hub analysis across drugs |
| `explainer_outputs/[DRUG]_[TARGET]_subgraph_visualization.png` | PNG | GNNExplainer subgraph visualization |
| `explainer_outputs/[DRUG]_[TARGET]_subgraph_nodes.csv` | CSV | Node importance scores from GNNExplainer |
| `explainer_outputs/[DRUG]_[TARGET]_subgraph_edges.csv` | CSV | Edge importance scores from GNNExplainer |

## File Dependency Graph

```
GEO Raw Data
    │
    ▼
harmonized_MASLD_metadata.csv  ──────────────────────┐
    │                                                │
    ▼                                                │
harmonized_MASLD_RNAseq_counts.csv                   │
    │                                                │
    ▼                                                │
normalized_expression_matrix.rds                     │
    │                                                │
    ├──► DGE_Full_Results_Fibrosis_and_Age.csv ──────┤
    │         │                                      │
    │         ▼                                      │
    │    PPI_Network.* + enrichment_results/         │
    │                                                │
    ├──► harmonized_ferroptosis_GSVA_scores.csv ─────┤
    │                                                │
    ├──► WGCNA_fibrosis_module_genes.csv ────────────┤
    │                                                │
    ▼                                                ▼
    └─────────────► masld_personalized_kg.gexf ◄─────┘
                          │
                          ▼
                    graphsage_pipeline.py
                          │
                          ▼
                    all_holdout_drugs_top_targets.csv
                    + explainer_outputs/
                    + model .pt files
```

## File Formats

- **CSV**: Standard comma-separated values (UTF-8 encoded)
- **TSV**: Tab-separated values
- **RDS**: R serialized object (use `readRDS()` in R)
- **GEXF**: Graph Exchange XML Format (readable by NetworkX, Gephi, Cytoscape)
- **GraphML**: XML-based graph format (readable by igraph, NetworkX, Cytoscape)
- **SIF**: Simple Interaction Format (Cytoscape-compatible)
- **PT**: PyTorch model checkpoint (load with `torch.load()`)
- **PNG**: Publication-quality figures (300 DPI)
