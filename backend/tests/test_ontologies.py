"""
MASLD DrugScope — Unit Tests: Ontology Mapping
===============================================
Tests for HGNC gene mapping, MONDO disease mapping, DrugBank drug mapping,
and Biolink predicate standardization.
"""

from __future__ import annotations

import pytest
from typing import Dict, List, Optional, Any


# ---------------------------------------------------------------------------
# Standalone implementations mirroring production code.
# Swap imports to `from app.services.ontology_service import …` when available.
# ---------------------------------------------------------------------------

# Simplified HGNC mapping (subset used by the system)
HGNC_REGISTRY: Dict[str, Dict[str, str]] = {
    "PPARG": {"hgnc_id": "HGNC:9238", "entrez_id": "5468", "symbol": "PPARG", "status": "Approved"},
    "FASN": {"hgnc_id": "HGNC:3584", "entrez_id": "2193", "symbol": "FASN", "status": "Approved"},
    "GPX4": {"hgnc_id": "HGNC:4563", "entrez_id": "2879", "symbol": "GPX4", "status": "Approved"},
    "SLC7A11": {"hgnc_id": "HGNC:11068", "entrez_id": "23600", "symbol": "SLC7A11", "status": "Approved"},
    "NFE2L2": {"hgnc_id": "HGNC:7782", "entrez_id": "4780", "symbol": "NFE2L2", "status": "Approved"},
    "THRB": {"hgnc_id": "HGNC:11794", "entrez_id": "7068", "symbol": "THRB", "status": "Approved"},
    "COL1A1": {"hgnc_id": "HGNC:2196", "entrez_id": "1277", "symbol": "COL1A1", "status": "Approved"},
    "NONEXISTENT": {"hgnc_id": "", "entrez_id": "", "symbol": "", "status": "Unknown"},
}

# MONDO disease mapping
MONDO_REGISTRY: Dict[str, Dict[str, str]] = {
    "MASLD": {"mondo_id": "MONDO:0005523", "label": "Metabolic Associated Steatotic Liver Disease", "exact": True},
    "NAFLD": {"mondo_id": "MONDO:0005523", "label": "Metabolic Associated Steatotic Liver Disease", "exact": False, "note": "Obsoleted term, mapped to MASLD"},
    "Liver Fibrosis": {"mondo_id": "MONDO:0002015", "label": "Liver Fibrosis", "exact": True},
    "Cirrhosis": {"mondo_id": "MONDO:0002015", "label": "Liver Fibrosis", "exact": False, "note": "Broad mapping"},
    "Ferroptosis": {"mondo_id": "MONDO:0019028", "label": "Ferroptosis", "exact": True},
}

# DrugBank drug mapping
DRUGBANK_REGISTRY: Dict[str, Dict[str, str]] = {
    "Resmetirom": {"drugbank_id": "DB15452", "name": "Resmetirom", "status": "FDA-Approved (2024)"},
    "Semaglutide": {"drugbank_id": "DB01287", "name": "Semaglutide", "status": "FDA-Approved"},
    "Pioglitazone": {"drugbank_id": "DB01134", "name": "Pioglitazone", "status": "FDA-Approved"},
    "Vitamin E": {"drugbank_id": "DB00153", "name": "Vitamin E", "status": "FDA-Approved (MASLD)"},
    "Obeticholic Acid": {"drugbank_id": "DB05409", "name": "Obeticholic Acid", "status": "FDA-Approved (PBC)"},
    "Disulfiram": {"drugbank_id": "DB00670", "name": "Disulfiram", "status": "Repurposing Candidate"},
    "Lanifibranor": {"drugbank_id": "DB12889", "name": "Lanifibranor", "status": "Investigational (Phase 3)"},
    "Berberine": {"drugbank_id": "DB06668", "name": "Berberine", "status": "Natural Product"},
    "Curcumin": {"drugbank_id": "DB11672", "name": "Curcumin", "status": "Natural Product"},
    "Silymarin": {"drugbank_id": "DB14411", "name": "Silymarin", "status": "Natural Product"},
}

# Biolink predicate standardization mapping
BIOLINK_PREDICATE_MAP: Dict[str, str] = {
    "targets": "biolink:directly_interacts_with",
    "target": "biolink:directly_interacts_with",
    "interacts_with": "biolink:interacts_with",
    "binds": "biolink:binds",
    "inhibits": "biolink:decreases_activity_of",
    "activates": "biolink:increases_activity_of",
    "participates_in": "biolink:participates_in",
    "co-expressed": "biolink:coexpressed_with",
    "pathway-shared": "biolink:participates_in",
    "PPI": "biolink:interacts_with",
    "treats": "biolink:treats",
    "associated_with": "biolink:related_to",
}


def map_gene_symbol(symbol: str) -> Optional[Dict[str, str]]:
    """Map a gene symbol to its HGNC entry."""
    entry = HGNC_REGISTRY.get(symbol)
    if entry and entry["status"] == "Approved":
        return entry
    return None


def map_disease(name: str) -> Optional[Dict[str, str]]:
    """Map a disease name to its MONDO entry."""
    entry = MONDO_REGISTRY.get(name)
    if entry:
        return entry
    # Case-insensitive fallback
    name_lower = name.lower()
    for key, val in MONDO_REGISTRY.items():
        if key.lower() == name_lower:
            return val
    return None


def map_drug(name: str) -> Optional[Dict[str, str]]:
    """Map a drug name to its DrugBank entry."""
    entry = DRUGBANK_REGISTRY.get(name)
    if entry:
        return entry
    # Case-insensitive fallback
    name_lower = name.lower()
    for key, val in DRUGBANK_REGISTRY.items():
        if key.lower() == name_lower:
            return val
    return None


def standardize_predicate(predicate: str) -> str:
    """Standardize a relationship predicate to its Biolink Model URI."""
    return BIOLINK_PREDICATE_MAP.get(predicate, f"biolink:{predicate}")


# =========================================================================
# Tests
# =========================================================================

class TestOntologyMapping:
    """Unit tests for ontology and identifier mapping."""

    @pytest.mark.unit
    def test_gene_symbol_maps_to_hgnc(self):
        """Approved gene symbols should resolve to HGNC entries."""
        result = map_gene_symbol("PPARG")
        assert result is not None
        assert result["hgnc_id"] == "HGNC:9238"
        assert result["entrez_id"] == "5468"
        assert result["symbol"] == "PPARG"

    @pytest.mark.unit
    def test_gene_symbol_all_known_genes(self):
        """All registered genes should map successfully."""
        known_genes = ["FASN", "GPX4", "SLC7A11", "NFE2L2", "THRB", "COL1A1"]
        for gene in known_genes:
            result = map_gene_symbol(gene)
            assert result is not None, f"Gene {gene} should map to HGNC"
            assert result["hgnc_id"].startswith("HGNC:")
            assert result["entrez_id"].isdigit()

    @pytest.mark.unit
    def test_unknown_gene_returns_none(self):
        """Unknown or unapproved gene symbols should return None."""
        # "NONEXISTENT" exists but has status "Unknown"
        assert map_gene_symbol("NONEXISTENT") is None
        # Completely absent gene
        assert map_gene_symbol("ZZZ999_FAKE") is None

    @pytest.mark.unit
    def test_disease_maps_to_mondo(self):
        """Known disease names should resolve to MONDO IDs."""
        result = map_disease("MASLD")
        assert result is not None
        assert result["mondo_id"] == "MONDO:0005523"
        assert "Metabolic Associated Steatotic Liver Disease" in result["label"]

    @pytest.mark.unit
    def test_disease_obsoleted_term_mapping(self):
        """Obsoleted terms (NAFLD) should map to current MONDO ID."""
        result = map_disease("NAFLD")
        assert result is not None
        assert result["mondo_id"] == "MONDO:0005523"
        assert result["exact"] is False

    @pytest.mark.unit
    def test_disease_case_insensitive(self):
        """Disease mapping should be case-insensitive."""
        result = map_disease("liver fibrosis")
        assert result is not None
        assert result["mondo_id"] == "MONDO:0002015"

    @pytest.mark.unit
    def test_unknown_disease_returns_none(self):
        """Unknown disease names should return None."""
        assert map_disease("FakeDisease123") is None

    @pytest.mark.unit
    def test_drug_maps_to_drugbank(self):
        """Known drug names should resolve to DrugBank IDs."""
        result = map_drug("Resmetirom")
        assert result is not None
        assert result["drugbank_id"] == "DB15452"

    @pytest.mark.unit
    def test_all_ten_drugs_map(self):
        """All 10 drugs in the system should have DrugBank entries."""
        for drug in DRUGBANK_REGISTRY:
            result = map_drug(drug)
            assert result is not None, f"Drug {drug} should map to DrugBank"
            assert result["drugbank_id"].startswith("DB")
            assert result["name"] == drug

    @pytest.mark.unit
    def test_drug_case_insensitive(self):
        """Drug mapping should be case-insensitive."""
        result = map_drug("semaglutide")
        assert result is not None
        assert result["drugbank_id"] == "DB01287"

    @pytest.mark.unit
    def test_biolink_predicate_standardization(self):
        """Various predicate aliases should map to standard Biolink URIs."""
        assert standardize_predicate("targets") == "biolink:directly_interacts_with"
        assert standardize_predicate("inhibits") == "biolink:decreases_activity_of"
        assert standardize_predicate("activates") == "biolink:increases_activity_of"
        assert standardize_predicate("co-expressed") == "biolink:coexpressed_with"
        assert standardize_predicate("PPI") == "biolink:interacts_with"

    @pytest.mark.unit
    def test_biolink_unknown_predicate_prefixed(self):
        """Unknown predicates should get a biolink: prefix."""
        result = standardize_predicate("some_custom_relation")
        assert result == "biolink:some_custom_relation"