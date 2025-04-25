import streamlit as st
import pandas as pd
import numpy as np

# print(pd.describe_option()) 
# pd.options.mode.dtype_backend = "numpy_nullable"


st.title("📊 DataFrame Analyzer Dashboard")

# Load a local DataFrame (you can replace this with your own DataFrame)
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("### Preview of Data", df.head())

    df_clean = df.copy()

    # Remove NaNs temporarily for type analysis
    non_na_df = df_clean.dropna()

    string_cols = []
    numeric_cols = []
    int_cols = []
    float_cols = []
    convertible_to_numeric = []

    for col in df_clean.columns:
        col_no_na = df_clean[col].dropna()

        if col_no_na.empty:
            continue

        try:
            # Try to convert to numeric
            converted = pd.to_numeric(col_no_na)
            numeric_cols.append(col)

            if pd.api.types.is_integer_dtype(converted):
                int_cols.append(col)
            elif pd.api.types.is_float_dtype(converted):
                float_cols.append(col)
            else:
                convertible_to_numeric.append(col)
        except:
            if pd.api.types.is_string_dtype(col_no_na):
                string_cols.append(col)
            else:
                # Check if it's string but convertible
                try:
                    pd.to_numeric(col_no_na)
                    convertible_to_numeric.append(col)
                except:
                    string_cols.append(col)

    st.markdown("## 🧠 Column Type Summary")
    st.write("**String columns:**", string_cols)
    st.write("**Convertible to numeric (string to number):**", convertible_to_numeric)
    st.write("**Numeric columns:**", numeric_cols)
    st.write("→ **Integer columns:**", int_cols)
    st.write("→ **Float columns:**", float_cols)

    st.markdown("## ❓ Missing Values")
    nan_counts = df_clean.isna().sum().reset_index()
    nan_counts.columns = ["Column", "NaNs"]
    nan_counts["NaNs"] = nan_counts["NaNs"].astype(int)  # Ensure safe dtype for JS rendering
    st.table(nan_counts)

    st.markdown("## 🔢 Numeric Column Stats")
    if numeric_cols:
        numeric_df = df_clean[numeric_cols].apply(pd.to_numeric, errors='coerce')
        numeric_stats = numeric_df.agg(['min', 'max', 'mean', 'std']).T
        st.dataframe(numeric_stats)
    else:
        st.info("No numeric columns found.")

    st.markdown("## 🏷️ Categorical Column Summary")
    if string_cols:
        summary_data = []

        for col in string_cols:
            value_counts = df_clean[col].value_counts(normalize=True, dropna=True).head(5)
            top_values = {str(k): round(v*100,2) for k,v in value_counts.items()}
            summary_data.append({
                "Column": col,
                "Unique Values": df_clean[col].nunique(dropna=True),
                "Top 5 Values (%)": ", ".join([f"{k}: {v}%" for k, v in top_values.items()]),

            })
        st.dataframe(summary_data)

    else:
        st.info("No categorical columns found.")

    st.markdown("## 🔢 Integer Column Summary")
    if int_cols:
        int_summary_data = []

        for col in int_cols:
            unique_count = df_clean[col].nunique(dropna=True)

            if unique_count > 10:
                # Bin the data into 10 equal-width bins
                binned_series = pd.cut(df_clean[col], bins=10)
                value_counts = binned_series.value_counts(normalize=True, dropna=True).sort_index().head(5)
                top_values = {str(k): round(v * 100, 2) for k, v in value_counts.items()}
                top_values_str = ", ".join([f"{k}: {v}%" for k, v in top_values.items()])
                label = f"{col} (binned)"
            else:
                value_counts = df_clean[col].value_counts(normalize=True, dropna=True).head(5)
                top_values = {str(k): round(v * 100, 2) for k, v in value_counts.items()}
                top_values_str = ", ".join([f"{k}: {v}%" for k, v in top_values.items()])
                label = col

            int_summary_data.append({
                "Column": label,
                "Unique Values": unique_count,
                "Top 5 Values (%)": top_values_str
            })

        int_summary_df = pd.DataFrame(int_summary_data)
        st.dataframe(int_summary_df)

    else:
        st.info("No integer columns found.")




# for the integer values wuth unique value more than 10, I want to devide them into bins (10 bins)
# then instead of having the dictionary on the unique values, i wanna have that on bins, on the name of the col add (bined) for the cases this happens. 


#userids

#dates and times