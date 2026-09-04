from pathlib import Path

import pandas as pd
import streamlit as st
import json


# Project root = folder that contains csv/ and env/
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIR = BASE_DIR / "config"


@st.cache_data
def load_csv(filename: str, **kwargs) -> pd.DataFrame:
    """Load a CSV file from the csv/ folder and remove completely empty rows."""
    path = DATA_DIR / filename
    df = pd.read_csv(path, **kwargs)
    return df.dropna(how="all")


@st.cache_data
def load_excel(filename: str, **kwargs) -> pd.DataFrame:
    """Load an Excel file from the csv/ folder and remove completely empty rows."""
    path = DATA_DIR / filename
    df = pd.read_excel(path, **kwargs)
    return df.dropna(how="all")


def load_json(filename: str) -> dict:
    """Load a JSON configuration file from the env/ folder."""
    path = CONFIG_DIR / filename
    with path.open("r", encoding="utf-8") as file:
        return __import__("json").load(file)


def clean_dataframe(
    df: pd.DataFrame,
    columns_to_remove: list[str],
) -> pd.DataFrame:
    """Remove optional columns without failing when a column is absent."""
    existing = [col for col in columns_to_remove if col in df.columns]
    return df.drop(columns=existing, errors="ignore")


def load_datasets() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and clean all datasets used by the chatbot."""
    travel_df = load_csv(
        "Travel details dataset.csv",
        encoding="utf-8",
        index_col=0,
    )

    travel_df = clean_dataframe(
        travel_df,
        [
            "Start date",
            "End date",
            "Duration (days)",
            "Traveler name",
            "Traveler gender",
            "Traveler age",
            "Traveler nationality",
            "Accommodation type",
            "Accommodation cost",
            "Transportation type",
        ],
    )

    hotel_df = load_csv(
        "Yerevan-Hotels.csv",
        encoding="utf-8",
        index_col=0,
    )

    plane_df = load_excel(
        "Data_Train.xlsx",
        index_col=0,
    )

    return travel_df, hotel_df, plane_df
