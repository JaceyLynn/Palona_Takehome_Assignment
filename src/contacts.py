"""Contact CSV helpers — load, filter, branch mapping, and merge."""

import os
import pandas as pd

_CSV_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "data", "hubspot_mock_contacts_100.csv")

# Map the UI basis label → CSV column name
BRANCH_BASIS_MAP: dict[str, str] = {
    "Demographic": "Demographic Branch",
    "Behavioral": "Behavior Branch",
    "Engagement": "Engagement Branch",
    "Lifecycle Stage": "Lifecycle Branch",
    "Interest": "Interest Branch",
}

# Columns shown in the Step 3 recipient table
DISPLAY_COLUMNS = [
    "First Name",
    "Last Name",
    "Email",
    "Company Name",
    "Job Title",
    "Priority Level",
    "Primary Need",
    "Preferred Send Time",
]

# Extra per-contact fields preserved for downstream personalization
PERSONALIZATION_FIELDS = [
    "Preferred CTA Text",
    "Preferred CTA Link",
    "Tone Notes",
    "Primary Need",
    "Client Notes",
    "Priority Level",
]


def load_contacts_csv(path: str | None = None) -> pd.DataFrame:
    """Load the master contact CSV.  Returns an empty DataFrame on failure."""
    p = path or _CSV_PATH
    if not os.path.exists(p):
        return pd.DataFrame()
    return pd.read_csv(p)


def get_branch_column(basis: str) -> str:
    """Return the CSV column name for a given branch basis."""
    return BRANCH_BASIS_MAP[basis]


def get_branch_options(df: pd.DataFrame, basis: str) -> list[str]:
    """Return the sorted unique branch values for a basis."""
    col = get_branch_column(basis)
    if col not in df.columns:
        return []
    return sorted(df[col].dropna().unique().tolist())


def filter_contacts_by_branch(
    df: pd.DataFrame, basis: str, branch_option: str
) -> pd.DataFrame:
    """Return rows matching *branch_option* in the column for *basis*."""
    col = get_branch_column(basis)
    return df[df[col] == branch_option].copy()


def merge_uploaded_contacts(
    base_df: pd.DataFrame, uploaded_df: pd.DataFrame
) -> pd.DataFrame:
    """Merge uploaded contacts into the working dataframe.

    Deduplicates by Email (keeps the base row).
    Missing columns in the uploaded frame are filled with empty strings.
    """
    # Align columns: add any missing columns from the base schema
    for c in base_df.columns:
        if c not in uploaded_df.columns:
            uploaded_df[c] = ""

    # Keep only columns that exist in base
    uploaded_df = uploaded_df[[c for c in base_df.columns if c in uploaded_df.columns]]

    combined = pd.concat([base_df, uploaded_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["Email"], keep="first")
    return combined
