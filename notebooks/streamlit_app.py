# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pycountry

# --- Page Config ---
st.set_page_config(page_title="UK International Student Visa Dashboard", layout="wide", page_icon="🎓")
st.title("UK International Student & Dependent Visa Dashboard (2019-2023)")

# --- File Upload ---
uploaded_file = st.file_uploader("Upload Excel File", type="xlsx")
if uploaded_file:
    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    
    # Sidebar: Sheet Overview
    st.sidebar.header("Sheets Overview")
    st.sidebar.write(list(sheets.keys()))
    
    # Sidebar: Visualization Options
    st.sidebar.header("Visualization Options")
    sheet_option = st.sidebar.selectbox("Choose a sheet for preview", list(sheets.keys()))
    
    st.subheader(f"Preview of '{sheet_option}'")
    st.dataframe(sheets[sheet_option].head())

    # --- Utility Functions ---
    def melt_wide_to_long(df):
        """Convert wide year-columns to long format"""
        year_cols = [c for c in df.columns if "20" in str(c) or "YE" in str(c)]
        long_df = df.melt(
            id_vars=[c for c in df.columns if c not in year_cols],
            value_vars=year_cols,
            var_name="Year",
            value_name="Count"
        )
        long_df["Count"] = pd.to_numeric(long_df["Count"], errors="coerce").fillna(0)
        return long_df

    # --- Plot 1: Visa Type Trends Over Time ---
    if all(col in sheets[sheet_option].columns for col in ["Cohort", "Visa"]):
        df_long = melt_wide_to_long(sheets[sheet_option])
        df_long['Year'] = df_long['Year'].astype(str).str.extract('(\d{4})')[0]
        visa_yearly = df_long.groupby(['Year', 'Visa'])['Count'].sum().reset_index()
        fig1 = px.area(
            visa_yearly, x='Year', y='Count', color='Visa',
            title="Visa Type Trends Over Time", line_group='Visa'
        )
        st.plotly_chart(fig1, use_container_width=True)

    # --- Plot 2: Sankey Diagram (Status -> Visa) ---
    if all(col in sheets[sheet_option].columns for col in ['Status', 'Visa']):
        df_sankey = melt_wide_to_long(sheets[sheet_option])
        df_sankey = df_sankey.groupby(['Status', 'Visa'])['Count'].sum().reset_index()
        df_sankey = df_sankey[df_sankey['Count'] > 0]
        statuses = df_sankey['Status'].unique().tolist()
        visas = df_sankey['Visa'].unique().tolist()
        labels = statuses + visas
        label_idx = {label: i for i, label in enumerate(labels)}
        fig2 = go.Figure(data=[go.Sankey(
            node=dict(label=labels, pad=20, thickness=20),
            link=dict(
                source=df_sankey['Status'].map(label_idx),
                target=df_sankey['Visa'].map(label_idx),
                value=df_sankey['Count']
            )
        )])
        fig2.update_layout(title_text="Status to Visa Flow", height=550)
        st.plotly_chart(fig2, use_container_width=True)

    # --- Plot 3: Top 10 Nationalities ---
    nationality_sheets = [
        "Study-related Nationality", "Study only Nationality",
        "Study Dep Nationality", "Status by Nationality",
        "Study and Dependant Nationality"
    ]
    found_sheet = next((s for s in nationality_sheets if s in sheets), None)
    if found_sheet:
        df_nat = sheets[found_sheet].copy()
        if "Nationality" in df_nat.columns and "Counts" in df_nat.columns:
            top_df = df_nat.groupby('Nationality')['Counts'].sum().sort_values(ascending=False).head(10).reset_index()
            fig3 = px.bar(top_df, x='Nationality', y='Counts', title="Top 10 Nationalities of Students")
            st.plotly_chart(fig3, use_container_width=True)

    # --- Plot 4: Choropleth Map (2023) ---
    if found_sheet and 'Cohort' in df_nat.columns:
        df_map_2023 = df_nat[df_nat['Cohort'] == 'YE June 2023'].copy()
        demonym_to_country = {
            'Chinese': 'China','Indian': 'India','USA':'United States','Nigerian':'Nigeria',
            'Saudi':'Saudi Arabia','Malaysian':'Malaysia','Pakistani':'Pakistan','Thai':'Thailand',
            'South Korean':'South Korea','Canadian':'Canada','Bangladeshi':'Bangladesh','Kuwaiti':'Kuwait',
            'Sri Lankan':'Sri Lanka','Nepali':'Nepal','Ghanaian':'Ghana'
        }
        df_map_2023['Country'] = df_map_2023['Nationality'].map(demonym_to_country)
        df_map_2023 = df_map_2023.dropna(subset=['Country'])
        df_map_2023['iso_alpha'] = df_map_2023['Country'].apply(lambda x: pycountry.countries.lookup(x).alpha_3)
        fig4 = px.choropleth(
            df_map_2023, locations='iso_alpha', color='Counts', hover_name='Country',
            color_continuous_scale=px.colors.sequential.Viridis
        )
        fig4.update_layout(title_text="Geographic Spread of Students (2023)", title_x=0.5)
        st.plotly_chart(fig4, use_container_width=True)

    # --- Plot 5: Study vs Dependent Visa Nationality Differences (Dumbbell) ---
    if "Study and Dependant Nationality" in sheets:
        df_sd = sheets["Study and Dependant Nationality"].copy()
        df_sd_2023 = df_sd[df_sd['Visa'].isin(['Study','Study dependant'])].copy()
        df_pivot = df_sd_2023.pivot(index='Nationality', columns='Visa', values='YE June 2023').reset_index()
        if 'Study' in df_pivot.columns and 'Study dependant' in df_pivot.columns:
            df_pivot['Gap'] = df_pivot['Study dependant'] - df_pivot['Study']
            df_pivot = df_pivot.sort_values(by='Gap', ascending=False)
            fig5 = go.Figure()
            for _, row in df_pivot.iterrows():
                fig5.add_trace(go.Scatter(
                    x=[row['Study'], row['Study dependant']],
                    y=[row['Nationality'], row['Nationality']],
                    mode='lines',
                    line=dict(color='lightgrey', width=2),
                    showlegend=False
                ))
            fig5.add_trace(go.Scatter(
                x=df_pivot['Study'], y=df_pivot['Nationality'],
                mode='markers', name='Study', marker=dict(color='green', size=10)
            ))
            fig5.add_trace(go.Scatter(
                x=df_pivot['Study dependant'], y=df_pivot['Nationality'],
                mode='markers', name='Dependants', marker=dict(color='orange', size=10)
            ))
            fig5.update_layout(title="Study vs Dependent Visa Nationality Differences", height=700)
            st.plotly_chart(fig5, use_container_width=True)

    # --- Plot 6: Dependent Visa Status Trends Over Time ---
    if "Study Dep Status and Visa" in sheets:
        df_dep = sheets["Study Dep Status and Visa"].copy()
        dep_types = ['Study Dependant','Work Dependant','Family']
        df_plot = df_dep[df_dep['Visa'].isin(dep_types)].copy()
        year_cols = [c for c in df_plot.columns if "20" in str(c) or "YE" in str(c)]
        df_long = df_plot.melt(id_vars=['Visa'], value_vars=year_cols, var_name='Year', value_name='Counts')
        df_long = df_long[pd.to_numeric(df_long['Counts'], errors='coerce').notna()]
        df_long['Counts'] = df_long['Counts'].astype(int)
        df_long['Year'] = df_long['Year'].astype(str).str.extract('(\d{4})')[0]
        fig6 = go.Figure()
        colors = {'Study Dependant':'royalblue','Work Dependant':'forestgreen','Family':'darkorange'}
        for vt in dep_types:
            df_vt = df_long[df_long['Visa']==vt].sort_values('Year')
            fig6.add_trace(go.Scatter(
                x=df_vt['Year'], y=df_vt['Counts'], mode='lines+markers',
                name=vt, line=dict(color=colors[vt])
            ))
        fig6.update_layout(title="Dependent Visa Status Trends Over Time", height=500)
        st.plotly_chart(fig6, use_container_width=True)

else:
    st.info("Please upload an Excel file to see the dashboard.")
