import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go

st.set_page_config(page_title="BASF Heat Reuse Sensitivity Dashboard", layout="wide")

# -------------------------

# CONSTANTS

# -------------------------

AVAILABLE_HEAT = 1596
EMISSION_FACTOR = 0.202
BOILER_EFF = 0.9
WACC = 0.06
CAPEX = 250000

years = list(range(2024,2034))

electricity_price = [126,126,127,117,116,111,114,110,104,102]
gas_price = [48,45,53,48,48,46,44,40,35,32]
co2_price = [84,94,101,98,101,103,106,109,111,114]

# -------------------------

# PAGE STYLE

# -------------------------

st.markdown("""

<style>
.stApp {
    background-color: #f7f7f5;
}
h1, h2, h3, h4, h5, h6, p, label, span {
    color: #1f2d3d !important;
}
</style>

""", unsafe_allow_html=True)

# -------------------------

# HEADER

# -------------------------

col1,col2 = st.columns([1,6])

with col1:
    st.image("BASF-LOGO.jpg", width=110)

with col2:
    st.title("Heat Reuse Sensitivity Analysis Dashboard")


st.markdown("---")

# -------------------------

# FILTERS

# -------------------------

st.subheader("Sensitivity Inputs")

col1,col2,col3 = st.columns(3)

with col1:
    cop = st.slider("COP",2.5,4.0,3.0,0.1)

with col2:
    util = st.slider("Utilization %",0.85,1.0,0.925,0.005)

with col3:
    maint = st.slider("Maintenance %",0.01,0.05,0.03,0.005)


# -------------------------

# CALCULATION FUNCTION

# -------------------------

def calculate(cop,util,maint):
    reused_heat = AVAILABLE_HEAT * util
    electricity_consumption = reused_heat/(cop-1)
    total_heat_delivered = electricity_consumption + reused_heat
    gas_avoided = total_heat_delivered/BOILER_EFF
    co2_avoided = EMISSION_FACTOR*gas_avoided

    rows=[]

    for i,y in enumerate(years):

        electricity_cost = -electricity_consumption*electricity_price[i]
        gas_savings = gas_avoided*gas_price[i]
        co2_savings = co2_avoided*co2_price[i]
        maintenance_cost = -CAPEX*maint

        ncf = electricity_cost + gas_savings + co2_savings + maintenance_cost
        dcf = ncf/((1+WACC)**(i+1))

        rows.append([y,ncf,dcf])

    df = pd.DataFrame(rows,columns=["Year","NCF","DCF"])

    df["CumNCF"] = df["NCF"].cumsum() - CAPEX
    df["CumDCF"] = df["DCF"].cumsum() - CAPEX

    npv = df["DCF"].sum() - CAPEX

    irr = npf.irr([-CAPEX] + df["NCF"].tolist())

    payback = next((i+1 for i,v in enumerate(df["CumNCF"]) if v>0),None)
    dpayback = next((i+1 for i,v in enumerate(df["CumDCF"]) if v>0),None)

    return df,npv,irr,payback,dpayback

# -------------------------

# SCENARIOS

# -------------------------

worst = calculate(2.5,0.85,0.05)
base = calculate(3.0,0.925,0.03)
best = calculate(4.0,1.0,0.01)

current = calculate(cop,util,maint)

# -------------------------

# KPI CARDS

# -------------------------

st.subheader("Key Financial Results")

col1,col2,col3,col4 = st.columns(4)

with col1:
    st.metric("NPV", f"{round(current[1]/1000,1)} k€")

with col2:
    st.metric("IRR", f"{round(current[2]*100,2)} %")

with col3:
    st.metric("Payback Period", f"{current[3]} years")

with col4:
    st.metric("Discounted Payback", f"{current[4]} years")

st.markdown("---")

# -------------------------

# FIXED VISUALS

# -------------------------

st.subheader("Scenario Comparison")

col1,col2 = st.columns(2)

# NPV + IRR chart

npv_values=[worst[1],base[1],best[1]]
irr_values=[worst[2],base[2],best[2]]

fig = go.Figure()

fig.add_bar(
x=["Worst Case","Base Case","Best Case"],
y=npv_values,
text=[round(v/1000,1) for v in npv_values],
textposition="outside",
name="NPV"
)

fig.add_scatter(
x=["Worst Case","Base Case","Best Case"],
y=irr_values,
mode="lines+markers+text",
text=[round(v*100,1) for v in irr_values],
textposition="top center",
name="IRR",
yaxis="y2"
)

fig.update_layout(
title="NPV and IRR Comparison Across Scenarios",
yaxis_title="NPV (k€)",
yaxis2=dict(overlaying="y",side="right",title="IRR (%)")
)

col1.plotly_chart(fig,width="stretch")

# PAYBACK COMPARISON

pb=[worst[3],base[3],best[3]]
dpb=[worst[4],base[4],best[4]]

fig2 = go.Figure()

fig2.add_bar(
x=["Worst Case","Base Case","Best Case"],
y=pb,
text=pb,
textposition="outside",
name="Payback Period"
)

fig2.add_bar(
x=["Worst Case","Base Case","Best Case"],
y=dpb,
text=dpb,
textposition="outside",
name="Discounted Payback"
)

fig2.update_layout(
title="Payback vs Discounted Payback Across Scenarios",
yaxis_title="Years"
)

col2.plotly_chart(fig2,width="stretch")

st.markdown("---")

# -------------------------

# FILTER BASED VISUALS

# -------------------------

st.subheader("Scenario Results")

df=current[0]

col1,col2 = st.columns(2)

# CUMULATIVE DCF

fig3 = go.Figure()

fig3.add_scatter(
x=df["Year"],
y=df["CumDCF"],
mode="lines+markers+text",
text=[round(v/1000,1) for v in df["CumDCF"]],
textposition="top center"
)

fig3.update_layout(
title="Cumulative Discounted Cash Flow (2024–2033)",
yaxis_title="€"
)

col1.plotly_chart(fig3,width="stretch")

# ANNUAL NCF

fig4 = go.Figure()

fig4.add_bar(
x=df["Year"],
y=df["NCF"],
text=[round(v/1000,1) for v in df["NCF"]],
textposition="outside"
)

fig4.update_layout(
title="Annual Net Cash Flow by Year",
yaxis_title="€"
)

col2.plotly_chart(fig4,width="stretch")

# -------------------------

# PAYBACK SENSITIVITY

# -------------------------

col1,col2 = st.columns(2)

# Payback vs COP

cop_range = np.arange(2.5,4.1,0.1)
pb_values=[calculate(c,util,maint)[3] for c in cop_range]

fig5 = go.Figure()

fig5.add_scatter(
x=cop_range,
y=pb_values,
mode="lines+markers+text",
text=pb_values,
textposition="top center"
)

fig5.update_layout(
title="Payback Sensitivity to COP",
xaxis_title="COP",
yaxis_title="Years"
)

col1.plotly_chart(fig5,width="stretch")

# Payback vs Utilization

util_range = np.arange(0.85,1.01,0.01)
pb2=[calculate(cop,u,maint)[3] for u in util_range]

fig6 = go.Figure()

fig6.add_scatter(
x=util_range,
y=pb2,
mode="lines+markers+text",
text=pb2,
textposition="top center"
)

fig6.update_layout(
title="Payback Sensitivity to Utilization",
xaxis_title="Utilization %",
yaxis_title="Years"
)

col2.plotly_chart(fig6,width="stretch")

st.markdown("---")

# -------------------------

# SENSITIVITY INFO

# -------------------------

st.subheader("Sensitivity Ranges")

st.write("COP range: **2.5 – 4.0**")
st.write("Utilization range: **85% – 100%**")
st.write("Maintenance range: **1% – 5%**")

# -------------------------
# TORNADO SENSITIVITY CHART
# -------------------------

st.markdown("---")
st.subheader("Sensitivity Impact on NPV (Tornado Chart)")

# Calculate NPV sensitivity for each variable

base_npv = base[1]

cop_low = calculate(2.5, util, maint)[1]
cop_high = calculate(4.0, util, maint)[1]

util_low = calculate(cop, 0.85, maint)[1]
util_high = calculate(cop, 1.0, maint)[1]

maint_low = calculate(cop, util, 0.01)[1]
maint_high = calculate(cop, util, 0.05)[1]

variables = ["COP", "Utilization", "Maintenance"]

low_values = [
    (cop_low - base_npv)/1000,
    (util_low - base_npv)/1000,
    (maint_low - base_npv)/1000
]

high_values = [
    (cop_high - base_npv)/1000,
    (util_high - base_npv)/1000,
    (maint_high - base_npv)/1000
]

fig_tornado = go.Figure()

fig_tornado.add_bar(
    y=variables,
    x=low_values,
    orientation="h",
    name="Low Case"
)

fig_tornado.add_bar(
    y=variables,
    x=high_values,
    orientation="h",
    name="High Case"
)

fig_tornado.update_layout(
    title="NPV Sensitivity to Key Variables",
    xaxis_title="Impact on NPV (k€)",
    barmode="relative"
)

st.plotly_chart(fig_tornado, width="stretch")
