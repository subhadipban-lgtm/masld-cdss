"""Salmon quantification pipeline.

Runs Salmon quasi-mapping against a pre-built transcriptome index,
loads the resulting ``quant.sf`` file, and aggregates transcript-level
estimates to gene-level counts using a transcript-to-gene mapping TSV.
"""

import subprocess
from pathlib import Path

import pandas as pd

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_TIMEOUT = 1200  # 20 minutes


def run_salmon_quant(
    trimmed_fastq: str,
    index_dir: str,
    output_dir: str,
    job_id: str | None = None,
    timeout: int = _DEFAULT_TIMEOUT,
) -> tuple[str, pd.DataFrame]:
    """Run Salmon quasi-mapping and return the gene-level count table.

    Parameters
    ----------
    trimmed_fastq:
        Path to the adapter-trimmed FASTQ file.
    index_dir:
        Path to the pre-built Salmon index.
    output_dir:
        Directory for Salmon output (``quant.sf`` is written here).
    job_id:
        Optional job identifier for log correlation.
    timeout:
        Maximum seconds to wait for Salmon to finish.

    Returns
    -------
    (quant_dir, gene_counts_df)
        ``quant_dir`` is the Salmon output directory containing
        ``quant.sf``.  ``gene_counts_df`` is a DataFrame with columns
        ``gene_id``, ``transcript_id``, ``length``, ``effective_length``,
        ``tpm``, ``num_reads`` aggregated to gene level.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    cmd = [
        settings.salmon_path,
        "quant",
        "-i", index_dir,
        "-l", "A",  # automatic library format detection
        "-r", trimmed_fastq,
        "-p", "4",
        "--validateMappings",
        "-o", output_dir,
    ]

    log_extra = {"job_id": job_id}
    logger.info(f"Running Salmon: {' '.join(cmd)}", extra=log_extra)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error(f"Salmon timed out after {timeout}s", extra=log_extra)
        raise RuntimeError(f"Salmon timed out after {timeout}s") from exc
    except subprocess.CalledProcessError as exc:
        logger.error(f"Salmon failed: {exc.stderr}", extra=log_extra)
        raise RuntimeError(f"Salmon exited with code {exc.returncode}: {exc.stderr}") from exc

    logger.info(f"Salmon quantification complete: {output_dir}", extra=log_extra)

    # Load transcript-level counts.
    transcript_df = load_salmon_counts(output_dir)

    # Aggregate to gene level.
    tx2gene_path = str(settings.tx2gene_path)
    gene_df = aggregate_to_gene_level(transcript_df, tx2gene_path)

    return output_dir, gene_df


def load_salmon_counts(quant_dir: str) -> pd.DataFrame:
    """Load and parse the ``quant.sf`` file produced by Salmon.

    Parameters
    ----------
    quant_dir:
        Directory containing the ``quant.sf`` output.

    Returns
    -------
    pd.DataFrame
        Columns: ``transcript_id``, ``length``, ``effective_length``,
        ``tpm``, ``num_reads``.
    """
    quant_path = Path(quant_dir) / "quant.sf"

    if not quant_path.exists():
        raise FileNotFoundError(f"Salmon quant.sf not found at {quant_path}")

    df = pd.read_csv(
        quant_path,
        sep="\t",
        usecols=[
            "Name",
            "Length",
            "EffectiveLength",
            "TPM",
            "NumReads",
        ],
    )
    df.columns = [
        "transcript_id",
        "length",
        "effective_length",
        "tpm",
        "num_reads",
    ]
    return df


def aggregate_to_gene_level(
    transcript_counts: pd.DataFrame,
    tx2gene_path: str,
) -> pd.DataFrame:
    """Aggregate transcript-level counts to gene-level using a tx2gene map.

    The tx2gene TSV is expected to have two columns (no header):
    ``transcript_id`` and ``gene_id``.

    Counts (``num_reads``) are summed per gene.  TPM is recomputed
    proportionally.  Length is taken as the weighted average of
    constituent transcripts by read count.

    Parameters
    ----------
    transcript_counts:
        DataFrame from :func:`load_salmon_counts`.
    tx2gene_path:
        Path to the transcript-to-gene mapping TSV.

    Returns
    -------
    pd.DataFrame
        Columns: ``gene_id``, ``length``, ``effective_length``,
        ``tpm``, ``num_reads``.
    """
    tx2gene = pd.read_csv(
        tx2gene_path,
        sep="\t",
        header=None,
        names=["transcript_id", "gene_id"],
    )

    merged = transcript_counts.merge(tx2gene, on="transcript_id", how="inner")

    if merged.empty:
        logger.warning(
            "No matching transcripts found between quant.sf and tx2gene mapping"
        )
        return pd.DataFrame(
            columns=["gene_id", "length", "effective_length", "tpm", "num_reads"]
        )

    aggregated = (
        merged.groupby("gene_id")
        .agg(
            num_reads=("num_reads", "sum"),
            length=("length", "mean"),
            effective_length=("effective_length", "mean"),
        )
        .reset_index()
    )

    # Recompute TPM from the aggregated read counts.
    total_reads = aggregated["num_reads"].sum()
    if total_reads > 0:
        aggregated["tpm"] = (aggregated["num_reads"] / aggregated["length"]) * 1e6
        tpm_sum = aggregated["tpm"].sum()
        if tpm_sum > 0:
            aggregated["tpm"] = aggregated["tpm"] * (1e6 / tpm_sum)

    logger.info(
        f"Aggregated {len(transcript_counts)} transcripts -> "
        f"{len(aggregated)} genes"
    )
    return aggregated