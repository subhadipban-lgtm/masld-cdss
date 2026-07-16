"""Ontology mapping for the MASLD DrugScope knowledge graph.

Maps gene symbols → HGNC/Ensembl/Entrez, diseases → MONDO/DOID/UMLS,
drugs → DrugBank/ChEMBL, and pathways → GO/Reactome.  Uses Biolink
Model predicates for standardised relationships.

An inline fallback mapping is provided for the 10 canonical drugs and
key genes so the system functions even without external mapping files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


class OntologyMapper:
    """Biomedical ontology mapper for MASLD entities.

    Parameters
    ----------
    data_dir:
        Path to the reference data directory containing mapping files.
        Falls back to inline defaults if files are missing.
    """

    # ── Biolink Model Predicates ────────────────────────────────────────
    PRED_TARGETS = "biolink:targets"
    PRED_TREATS = "biolink:treats"
    PRED_CORRELATES = "biolink:correlates_with"
    PRED_PARTICIPATES_IN = "biolink:participates_in"

    def __init__(self, data_dir: str = "") -> None:
        self._data_dir = Path(data_dir) if data_dir else Path("")
        self._gene_map: dict[str, dict[str, str]] = {}
        self._drug_map: dict[str, dict[str, str]] = {}
        self._disease_map: dict[str, dict[str, str]] = {}
        self._pathway_map: dict[str, dict[str, str]] = {}

        if self._data_dir.exists():
            self.load_mappings(str(self._data_dir))
        else:
            logger.info("Reference data dir not found; using inline ontology mappings")
            self._load_inline_mappings()

    # ── File-based Loading ──────────────────────────────────────────────

    def load_mappings(self, data_dir: str) -> None:
        """Load all ontology mapping files from *data_dir*.

        Expects the following TSV files (two columns, no header):
        - ``gene_mappings.tsv``  → gene_symbol, HGNC_ID, Ensembl_ID, Entrez_ID
        - ``drug_mappings.tsv``  → drug_name, DrugBank_ID, ChEMBL_ID
        - ``disease_mappings.tsv`` → disease_name, MONDO_ID, DOID_ID, UMLS_ID
        - ``pathway_mappings.tsv`` → pathway_name, GO_ID, Reactome_ID
        """
        d = Path(data_dir)

        # Gene mappings.
        gene_path = d / "gene_mappings.tsv"
        if gene_path.exists():
            self._gene_map = self._load_tsv_mapping(
                gene_path, ["HGNC_ID", "Ensembl_ID", "Entrez_ID"]
            )
            logger.info(f"Loaded {len(self._gene_map)} gene mappings")

        # Drug mappings.
        drug_path = d / "drug_mappings.tsv"
        if drug_path.exists():
            self._drug_map = self._load_tsv_mapping(
                drug_path, ["DrugBank_ID", "ChEMBL_ID"]
            )
            logger.info(f"Loaded {len(self._drug_map)} drug mappings")

        # Disease mappings.
        disease_path = d / "disease_mappings.tsv"
        if disease_path.exists():
            self._disease_map = self._load_tsv_mapping(
                disease_path, ["MONDO_ID", "DOID_ID", "UMLS_ID"]
            )
            logger.info(f"Loaded {len(self._disease_map)} disease mappings")

        # Pathway mappings.
        pathway_path = d / "pathway_mappings.tsv"
        if pathway_path.exists():
            self._pathway_map = self._load_tsv_mapping(
                pathway_path, ["GO_ID", "Reactome_ID"]
            )
            logger.info(f"Loaded {len(self._pathway_map)} pathway mappings")

        # Merge any remaining with inline defaults.
        self._load_inline_mappings()

    @staticmethod
    def _load_tsv_mapping(
        path: Path, field_names: list[str]
    ) -> dict[str, dict[str, str]]:
        """Load a TSV mapping file into a nested dict."""
        mappings: dict[str, dict[str, str]] = {}
        with open(path) as fh:
            for line in fh:
                parts = line.strip().split("\t")
                if not parts or not parts[0]:
                    continue
                key = parts[0]
                values: dict[str, str] = {}
                for i, name in enumerate(field_names, start=1):
                    if i < len(parts) and parts[i]:
                        values[name] = parts[i]
                mappings[key] = values
        return mappings

    # ── Inline Fallback Mappings ────────────────────────────────────────

    def _load_inline_mappings(self) -> None:
        """Populate inline mappings for canonical MASLD entities."""
        # Only add entries that are not already loaded from files.
        _gene_defaults: dict[str, dict[str, str]] = {
            "PPARG": {"HGNC_ID": "HGNC:9236", "Ensembl_ID": "ENSG00000132170", "Entrez_ID": "5468"},
            "FASN": {"HGNC_ID": "HGNC:3584", "Ensembl_ID": "ENSG00000169710", "Entrez_ID": "2194"},
            "SCD": {"HGNC_ID": "HGNC:10525", "Ensembl_ID": "ENSG00000119888", "Entrez_ID": "6319"},
            "DGAT2": {"HGNC_ID": "HGNC:26953", "Ensembl_ID": "ENSG00000145174", "Entrez_ID": "84648"},
            "PNPLA3": {"HGNC_ID": "HGNC:26599", "Ensembl_ID": "ENSG00000172334", "Entrez_ID": "80339"},
            "TM6SF2": {"HGNC_ID": "HGNC:32284", "Ensembl_ID": "ENSG00000155722", "Entrez_ID": "55902"},
            "MBOAT7": {"HGNC_ID": "HGNC:25090", "Ensembl_ID": "ENSG00000164928", "Entrez_ID": "80282"},
            "GCKR": {"HGNC_ID": "HGNC:4197", "Ensembl_ID": "ENSG00000120885", "Entrez_ID": "2646"},
            "THRB": {"HGNC_ID": "HGNC:11794", "Ensembl_ID": "ENSG00000142208", "Entrez_ID": "7068"},
            "SREBF1": {"HGNC_ID": "HGNC:11289", "Ensembl_ID": "ENSG00000169821", "Entrez_ID": "6720"},
            "GPX4": {"HGNC_ID": "HGNC:4523", "Ensembl_ID": "ENSG00000167468", "Entrez_ID": "2879"},
            "SLC7A11": {"HGNC_ID": "HGNC:11088", "Ensembl_ID": "ENSG00000166804", "Entrez_ID": "23657"},
            "NFE2L2": {"HGNC_ID": "HGNC:7782", "Ensembl_ID": "ENSG00000116044", "Entrez_ID": "4780"},
            "HMOX1": {"HGNC_ID": "HGNC:4974", "Ensembl_ID": "ENSG00000100179", "Entrez_ID": "3162"},
            "SOD2": {"HGNC_ID": "HGNC:11136", "Ensembl_ID": "ENSG00000112062", "Entrez_ID": "6648"},
            "MTTP": {"HGNC_ID": "HGNC:7437", "Ensembl_ID": "ENSG00000090235", "Entrez_ID": "4547"},
            "APOB": {"HGNC_ID": "HGNC:603", "Ensembl_ID": "ENSG00000182192", "Entrez_ID": "338"},
            "COL1A1": {"HGNC_ID": "HGNC:2195", "Ensembl_ID": "ENSG00000108821", "Entrez_ID": "1277"},
            "NR1H4": {"HGNC_ID": "HGNC:14338", "Ensembl_ID": "ENSG00000184571", "Entrez_ID": "9971"},
            "GLP1R": {"HGNC_ID": "HGNC:5562", "Ensembl_ID": "ENSG00000105501", "Entrez_ID": "2740"},
        }

        _drug_defaults: dict[str, dict[str, str]] = {
            "Resmetirom": {"DrugBank_ID": "DB16548", "ChEMBL_ID": "CHEMBL2366148"},
            "Semaglutide": {"DrugBank_ID": "DB13964", "ChEMBL_ID": "CHEMBL2366321"},
            "Pioglitazone": {"DrugBank_ID": "DB01134", "ChEMBL_ID": "CHEMBL1674"},
            "Vitamin E": {"DrugBank_ID": "DB00163", "ChEMBL_ID": "CHEMBEL14446"},
            "Obeticholic Acid": {"DrugBank_ID": "DB05404", "ChEMBL_ID": "CHEMBL374276"},
            "Disulfiram": {"DrugBank_ID": "DB00822", "ChEMBL_ID": "CHEMBL699"},
            "Lanifibranor": {"DrugBank_ID": "DB15518", "ChEMBL_ID": "CHEMBL2348665"},
            "Berberine": {"DrugBank_ID": "DB06696", "ChEMBL_ID": "CHEMBL2348370"},
            "Curcumin": {"DrugBank_ID": "DB11672", "ChEMBL_ID": "CHEMBL2110978"},
            "Silymarin": {"DrugBank_ID": "DB01604", "ChEMBL_ID": "CHEMBL449709"},
        }

        _disease_defaults: dict[str, dict[str, str]] = {
            "MASLD": {"MONDO_ID": "MONDO:0002486", "DOID_ID": "DOID:0050701", "UMLS_ID": "C1442460"},
            "MASH": {"MONDO_ID": "MONDO:0004480", "DOID_ID": "DOID:0080560", "UMLS_ID": "C1442459"},
            "Liver Fibrosis": {"MONDO_ID": "MONDO:0005305", "DOID_ID": "DOID:5473", "UMLS_ID": "C0015693"},
            "Cirrhosis": {"MONDO_ID": "MONDO:0002084", "DOID_ID": "DOID:5082", "UMLS_ID": "C0008577"},
        }

        _pathway_defaults: dict[str, dict[str, str]] = {
            "Ferroptosis": {"GO_ID": "GO:0097310", "Reactome_ID": "R-HSA-109582"},
            "Lipid Metabolism": {"GO_ID": "GO:0006629", "Reactome_ID": "R-HSA-556833"},
            "PPAR Signalling": {"GO_ID": "GO:0035357", "Reactome_ID": "R-HSA-556833"},
            "Fibrosis": {"GO_ID": "GO:0090090", "Reactome_ID": "R-HSA-1500931"},
            "Oxidative Stress Response": {"GO_ID": "GO:0006979", "Reactome_ID": "R-HSA-5686139"},
        }

        for k, v in _gene_defaults.items():
            self._gene_map.setdefault(k, v)
        for k, v in _drug_defaults.items():
            self._drug_map.setdefault(k, v)
        for k, v in _disease_defaults.items():
            self._disease_map.setdefault(k, v)
        for k, v in _pathway_defaults.items():
            self._pathway_map.setdefault(k, v)

    # ── Public API ──────────────────────────────────────────────────────

    def enrich_node(self, node_id: str, node_type: str) -> dict[str, Any]:
        """Add ontology annotations to a node.

        Parameters
        ----------
        node_id:
            The node identifier (e.g. ``"PPARG"``, ``"Resmetirom"``).
        node_type:
            One of ``"gene"``, ``"drug"``, ``"disease"``, ``"pathway"``.

        Returns
        -------
        dict
            The original annotations plus any ontology IDs found.
        """
        result: dict[str, Any] = {"node_id": node_id, "node_type": node_type}

        if node_type == "gene":
            mapping = self._gene_map.get(node_id, {})
            result.update(mapping)
        elif node_type == "drug":
            mapping = self._drug_map.get(node_id, {})
            result.update(mapping)
        elif node_type == "disease":
            mapping = self._disease_map.get(node_id, {})
            result.update(mapping)
        elif node_type == "pathway":
            mapping = self._pathway_map.get(node_id, {})
            result.update(mapping)

        return result

    def get_biolink_predicate(self, edge_type: str) -> str:
        """Map an edge type string to a Biolink Model predicate.

        Parameters
        ----------
        edge_type:
            A descriptive edge type (e.g. ``"targets"``, ``"PPI"``).

        Returns
        -------
        str
            A Biolink Model predicate URI.
        """
        mapping = {
            "targets": self.PRED_TARGETS,
            "treats": self.PRED_TREATS,
            "co-expressed": self.PRED_CORRELATES,
            "correlates_with": self.PRED_CORRELATES,
            "pathway-shared": self.PRED_PARTICIPATES_IN,
            "PPI": self.PRED_CORRELATES,
        }
        return mapping.get(edge_type, f"biolink:{edge_type}")

    @property
    def gene_count(self) -> int:
        """Number of genes in the mapping."""
        return len(self._gene_map)

    @property
    def drug_count(self) -> int:
        """Number of drugs in the mapping."""
        return len(self._drug_map)