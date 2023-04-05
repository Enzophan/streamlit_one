"""
# Jira analysis
Here's our first attempt at using data to create a table:
"""
from mimetypes import init
from operator import index
import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import plotly_express as px # pip install plotly-express
from io import StringIO


st.set_page_config(
    page_title="Jira analysis",
    page_icon=":bar_chart:",
    layout="wide"
)

st.title('Jira analysis')

uploaded_file = st.file_uploader("Upload a CSV")

def load_data(uploaded_file):
        # Can be used wherever a "file-like" object is accepted:
        dataframe = pd.read_csv(uploaded_file)
        return dataframe

if uploaded_file is not None:
    data = load_data(uploaded_file)
    data.set_index('Issue key', inplace=True)
      
    # filling a null values using fillna() 
    data["Sprint"].fillna("No Sprint", inplace = True)
    data["Custom field (Bug Type)"].fillna("No Bug Type", inplace = True)
    # replace column name 
    data.rename(columns = {'Custom field (Root Cause)':'Root Cause'}, inplace = True)

    # st.write(data)

    #---Sidebar ---
    st.sidebar.header("Please filter here:")
    sprint = st.sidebar.multiselect(
        "Select the Sprint:",
        options=data["Sprint"].unique(),
        default=data["Sprint"].unique()
    )

    issueType = st.sidebar.multiselect(
        "Select the Type:",
        options=data["Issue Type"].unique(),
        default=data["Issue Type"].unique()
    )

    status = st.sidebar.multiselect(
        "Select the Status:",
        options=data["Status"].unique(),
        default=data["Status"].unique()
    )

    df_selection = data.query("Sprint == @sprint & `Issue Type` == @issueType & Status == @status")

    # --- Mainpage ---

    st.title(":bar_chart: Dashboard")
    st.markdown("##")
    # st.write(df_selection)

    # & `Status` in ('', 'AVAILABLE FOR RETEST','DEPLOYED TO STG', 'IN PRODUCTION', 'Done')
    # df_count_point = df_selection.query("`Issue Type` in ('Story', 'Task', 'Enhancement', 'Bug', 'Legacy Bug') & `Status` not in ('Cancelled')")
    # st.write(df_count_point)
    # totalPoint = int(sum(df_count_point['Custom field (Story Points)'] != ''))

    # totalPoint = init(sum(df_selection['Custom field (Story Points)'] if df_selection['Custom field (Story Points)'] != '' else "0"))
    totalPoint = int(sum(df_selection['Custom field (Story Points)'] != ''))

    values=['Sub-Bug', 'IT Bug']
    totalSubBugs = df_selection.query("`Issue Type` in @values & `Status` not in ('Cancelled')").count()[0]
    totalBugs = df_selection.query("`Issue Type` in ('Bug') & `Status` not in ('Cancelled')").count()[0]
    totalLegacyBugs = df_selection.query("`Issue Type` in ('Legacy Bug') & `Status` not in ('Cancelled')").count()[0]
    # st.subheader(f'totalSubBugs: {totalSubBugs}')
    # st.subheader(f'totalBugs: {totalBugs}')
    # st.subheader(f'totalLegacyBugs: {totalLegacyBugs}')

    bugsPerPoint = round((totalSubBugs /totalPoint)* 100, 2) if totalPoint else 0


    left_column, middle_column, right_column = st.columns(3)
    with left_column:
        st.subheader("Total Point (Stories & Bugs):")
        st.subheader(f"{totalPoint:,}")

    with middle_column:
        st.subheader("Sub-Bug(s) per story point:")
        st.subheader(f"{bugsPerPoint:,} %")

    with right_column:
        st.subheader("Total Bugs (all):")
        st.subheader(f"{totalBugs + totalLegacyBugs + totalSubBugs:,}")


    st.markdown("---")
    # Sub-Bugs by Sprint [Bar Chart]
    bugs_by_sprint =  (
        df_selection.query("`Issue Type` in ('Sub-Bug', 'IT Bug')").groupby(by=["Sprint"]).size().reset_index(name='Total')
    )

    fig_sub_bugs = px.bar(
        bugs_by_sprint,
        x="Total",
        y=bugs_by_sprint['Sprint'],
        orientation="h",
        title="<b>Sub-Bugs by Sprint</b>",
        color_discrete_sequence=["#0083B8"] * len(bugs_by_sprint),
        template="plotly_white",
    )

    fig_sub_bugs.update_layout(
        plot_bgcolor = "rgba(0,0,0,0)",
        xaxis=(dict(showgrid=False))
    )

   # Bugs by Sprint [Bar Chart]
    bugs_by_priority = df_selection.query("`Issue Type` in ('Bug', 'Legacy Bug')").groupby(by=["Priority"]).size().reset_index(name='Total')
    fig_bugs_priority = px.bar(
        bugs_by_priority,
        x=bugs_by_priority['Priority'],
        y="Total",
        title="<b>Bugs & Legacy Bugs by priority</b>",
        color_discrete_sequence=["#0083B8"] * len(bugs_by_priority),
        template="plotly_white",
    )

    fig_bugs_priority.update_layout(
        plot_bgcolor = "rgba(0,0,0,0)",
        xaxis=(dict(tickmode="linear")),
        yaxis=(dict(showgrid=False))
    )

    left_column, right_column = st.columns(2)
    left_column.plotly_chart(fig_sub_bugs, use_container_width=True)
    right_column.plotly_chart(fig_bugs_priority, use_container_width=True)

    st.markdown("---")
    st.subheader("Defect:")
    values_leakage=['Sub-Bug', 'IT Bug', 'Bug', 'Legacy Bug']

    totalBugsBeforceUAT = df_selection.query("`Issue Type` in @values_leakage & `Custom field (Development phase)` not in ('UAT', 'PROD')").count()[0]
    totalBugsAfterUAT = df_selection.query("`Issue Type` in @values_leakage & `Custom field (Development phase)` in ('UAT', 'PROD')").count()[0]

    totalBugsResolved = df_selection.query("`Issue Type` in @values_leakage & `Status` in ('Cancelled', 'DEPLOYED TO STG', 'IN PRODUCTION', 'Done')").count()[0]
    # totalBugsRemaining = df_selection.query("`Issue Type` in @values_leakage & `Status` not in ('Cancelled', 'DEPLOYED TO STG', 'IN PRODUCTION', 'Done')").count()[0]

    defectLeakage = round((totalBugsAfterUAT /totalBugsBeforceUAT)* 100, 2) if totalBugsBeforceUAT else 0
    defectResolved = round((totalBugsResolved/(totalBugs + totalLegacyBugs + totalSubBugs))*100,2) if (totalBugs + totalLegacyBugs + totalSubBugs) else 0

    df_add_severity = df_selection.query("`Issue Type` in @values_leakage").groupby(by=["Priority"]).size().reset_index(name='Total_Bug')
    def severity_index (row):
        if row["Priority"] == "Low":
            return 2
        if row["Priority"] == "Medium":
            return 3
        if row["Priority"] == "High":
            return 4
        if row["Priority"] == "Critical":
            return 5
        return 1

    df_add_severity['Severity'] = df_add_severity.apply(lambda row : severity_index(row), axis=1)
    df_add_severity['Severity Index'] = df_add_severity['Total_Bug'] * df_add_severity['Severity']
    defectSeverityIndex = round(int(sum(df_add_severity['Severity Index'])) / (totalBugs + totalLegacyBugs + totalSubBugs), 2)

    col1, col2, col3 = st.columns(3)
    col1.metric("Defect Leakage", f"{defectLeakage:,} %")
    col2.metric("Defect Resolved", f"{defectResolved:,} %")
    col3.metric("Defect Severity Index", f"{defectSeverityIndex:,}")



    st.markdown("---")
    # Bug by Category [Pie Chart]
    df_bug_by_category = df_selection.query("`Issue Type` in ('Sub-Bug', 'IT Bug', 'Bug', 'Legacy Bug')").groupby(by=["Custom field (Bug Type)"]).size().reset_index(name='Total_Bug')
    df_bug_by_category['Total %'] = round((df_bug_by_category['Total_Bug'] / (totalBugs + totalLegacyBugs + totalSubBugs))  *100, 2)
    fig_bugs_by_category = px.pie(df_bug_by_category, values='Total %', names='Custom field (Bug Type)', title='Bug by Category')

    # Bugs by Root Cause [Bar Chart]
    bugs_by_root_cause = df_selection.query("`Issue Type` in ('Sub-Bug', 'IT Bug', 'Bug', 'Legacy Bug')").groupby(by=["Root Cause"]).size().reset_index(name='Total')
    fig_bugs_by_root_cause = px.pie(bugs_by_root_cause, values='Total', names='Root Cause', title='Bug by Root Cause')

    # st.write(bugs_by_root_cause)
    # fig_bugs_by_root_cause = px.bar(
    #     bugs_by_root_cause,
    #     x=bugs_by_root_cause['Root Cause'],
    #     y="Total",
    #     title="<b>Bugs by Root Cause</b>",
    #     color_discrete_sequence=["#0083B8"] * len(df_bug_by_category),
    #     template="plotly_white",
    # )

    # fig_bugs_by_root_cause.update_layout(
    #     plot_bgcolor = "rgba(0,0,0,0)",
    #     xaxis=(dict(tickmode="linear")),
    #     yaxis=(dict(showgrid=False))
    # )


    left_column, right_column = st.columns(2)
    left_column.plotly_chart(fig_bugs_by_category, use_container_width=True)
    right_column.plotly_chart(fig_bugs_by_root_cause, use_container_width=True)


    # df_find = df_selection.query("`Issue Type` in @values_leakage & `Issue key` in ('TSO-4280' , 'TSO-4388')")
    # st.write(df_find)

#--- Hide streamlit style ---
hide_st_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""

st.markdown(hide_st_style, unsafe_allow_html=True)

