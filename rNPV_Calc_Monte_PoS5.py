import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt

# Set page layout to wide
st.set_page_config(layout="wide", page_title="Drug Dev Portfolio Manager")

st.title("💊 Advanced Drug Development Portfolio Manager")
st.markdown("Set baselines in **Settings**, assess project-specific PoS in **Step 1**, and run financial simulations in **Step 2**.")

PHASES = ["Preclinical", "Phase I", "Phase II", "Phase III", "Approval"]

# ==========================================
# 0. Initialize Session State (Memory)
# ==========================================
if 'app_settings' not in st.session_state:
    st.session_state.app_settings = {
        'modality_pos': {
            "Small Molecule": [60.0, 50.0, 30.0, 60.0, 90.0],
            "Biologics / mAb": [70.0, 60.0, 40.0, 70.0, 95.0],
            "Cell & Gene Therapy": [50.0, 60.0, 50.0, 50.0, 85.0]
        },
        'phase_defaults': {
            "Cost ($M)": [5.0, 10.0, 30.0, 100.0, 2.0],
            "Duration (Yrs)": [2, 1, 2, 3, 1]
        },
        'discount_rate': 10.0,
        'commercial_years': 10,
        'cogs_sgna_rate': 30.0
    }

# Create Tabs
tab_settings, tab_pos, tab_rnpv = st.tabs([
    "⚙️ Settings", 
    "🔍 Step 1: PoS Assessment", 
    "💰 Step 2: rNPV & Simulation"
])

# ==========================================
# TAB 0: Settings
# ==========================================
with tab_settings:
    st.header("⚙️ Global Settings")
    st.markdown("Define the standard baselines applied to Step 1 and Step 2. You can **click and edit the tables directly**.")

    col_set1, col_set2 = st.columns(2)
    
    with col_set1:
        st.subheader("1. Baseline PoS (%) by Modality")
        df_modality = pd.DataFrame(st.session_state.app_settings['modality_pos'], index=PHASES).T
        edited_modality = st.data_editor(df_modality, use_container_width=True)

    with col_set2:
        st.subheader("2. Standard Cost & Duration by Phase")
        df_phase = pd.DataFrame(st.session_state.app_settings['phase_defaults'], index=PHASES)
        edited_phase = st.data_editor(df_phase, use_container_width=True)

    st.subheader("3. Financial & Commercial Settings")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        new_dr = st.number_input("Default Discount Rate (%)", value=float(st.session_state.app_settings['discount_rate']))
    with col_f2:
        new_cy = st.number_input("Default Commercial Duration (Yrs)", value=int(st.session_state.app_settings['commercial_years']))
    with col_f3:
        new_cogs = st.number_input("Default COGS+SG&A Rate (%)", value=float(st.session_state.app_settings['cogs_sgna_rate']))

    if st.button("💾 Save & Apply Settings", type="primary"):
        st.session_state.app_settings['modality_pos'] = edited_modality.T.to_dict('list')
        st.session_state.app_settings['phase_defaults'] = edited_phase.to_dict('list')
        st.session_state.app_settings['discount_rate'] = new_dr
        st.session_state.app_settings['commercial_years'] = new_cy
        st.session_state.app_settings['cogs_sgna_rate'] = new_cogs
        
        # Clear specific memory to force refresh of default values
        keys_to_delete = [k for k in st.session_state.keys() if k.startswith(('c_', 'd_', 'p_')) or k in ['calculated_pos', 'last_settings']]
        for k in keys_to_delete:
            del st.session_state[k]
            
        st.success("✅ Settings updated successfully. Baselines have been applied to Step 1 and Step 2.")


# ==========================================
# TAB 1: PoS Assessment
# ==========================================
with tab_pos:
    st.header("1. Baseline PoS Settings")
    col_mod, col_info = st.columns([1, 2])
    
    with col_mod:
        modality_dict = st.session_state.app_settings['modality_pos']
        selected_modality = st.selectbox("Select Modality", list(modality_dict.keys()))
        base_pos = modality_dict[selected_modality]
    
    st.divider()
    
    st.header("2. Risk Adjustments")
    st.markdown("Adjust the baseline PoS by evaluating project-specific characteristics.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        moa_status = st.selectbox("MoA / Target Validation", ["Novel (First-in-Class)", "Fast Follower", "Validated Target"])
    with col2:
        biomarker = st.radio("Patient Selection Biomarker?", ["No", "Yes"])
    with col3:
        endpoint = st.selectbox("Primary Endpoint (Phase II/III)", ["Subjective / Novel", "Established Surrogate", "Hard Clinical Outcome"])

    # PoS Adjustment Logic
    adj_pos = base_pos.copy()
    
    if moa_status == "Validated Target":
        adj_pos[0] = min(adj_pos[0] * 1.20, 99.0)
        adj_pos[1] = min(adj_pos[1] * 1.15, 99.0)
        adj_pos[2] = min(adj_pos[2] * 1.10, 99.0)
    elif moa_status == "Fast Follower":
        adj_pos[1] = min(adj_pos[1] * 1.10, 99.0)

    if biomarker == "Yes":
        adj_pos[2] = min(adj_pos[2] * 1.30, 99.0)
        adj_pos[3] = min(adj_pos[3] * 1.20, 99.0)

    if endpoint == "Hard Clinical Outcome":
        adj_pos[2] = min(adj_pos[2] * 1.10, 99.0)
        adj_pos[3] = min(adj_pos[3] * 1.15, 99.0)
        adj_pos[4] = min(adj_pos[4] * 1.05, 99.0)
    elif endpoint == "Subjective / Novel":
        adj_pos[2] = adj_pos[2] * 0.90
        adj_pos[3] = adj_pos[3] * 0.85
        adj_pos[4] = adj_pos[4] * 0.90

    st.session_state['calculated_pos'] = adj_pos

    # Detect changes to update Step 2 inputs automatically
    current_settings = f"{selected_modality}_{moa_status}_{biomarker}_{endpoint}"
    if st.session_state.get('last_settings') != current_settings:
        st.session_state['last_settings'] = current_settings
        for i in range(5):
            st.session_state[f"p_{i}"] = float(adj_pos[i])

    st.subheader("📊 Adjusted PoS Results")
    pos_df = pd.DataFrame({
        "Phase": PHASES,
        "Baseline PoS (%)": base_pos,
        "Adjusted PoS (%)": [round(p, 1) for p in adj_pos]
    })
    st.dataframe(pos_df.T, use_container_width=True)
    st.success("✅ PoS Assessment complete. Please proceed to **Step 2: rNPV & Simulation**.")


# ==========================================
# TAB 2: rNPV & Simulation
# ==========================================
with tab_rnpv:
    current_pos = st.session_state.get('calculated_pos', list(st.session_state.app_settings['modality_pos'].values())[0])
    
    st.header("1. Financial Parameters")
    
    col_fin1, col_fin2, col_fin3 = st.columns(3)
    with col_fin1:
        discount_rate = st.number_input("Discount Rate (%)", value=float(st.session_state.app_settings['discount_rate']), step=1.0) / 100
        n_simulations = st.selectbox("Number of Simulations", [1000, 5000, 10000], index=1)
    with col_fin2:
        commercial_years = st.number_input("Commercial Duration (Years)", value=int(st.session_state.app_settings['commercial_years']), step=1)
        cogs_sgna_rate = st.number_input("COGS + SG&A Rate (%)", value=float(st.session_state.app_settings['cogs_sgna_rate']), step=1.0) / 100
    with col_fin3:
        peak_sales_min = st.number_input("Min Peak Sales ($M/Yr)", value=200, step=10)
        peak_sales_expected = st.number_input("Expected Peak Sales ($M/Yr)", value=500, step=10)
        peak_sales_max = st.number_input("Max Peak Sales ($M/Yr)", value=1000, step=10)

    st.divider()
    st.header("2. Phase Costs & Timelines")
    st.markdown("*Note: The Probability of Success (PoS) is auto-populated from Step 1. You can manually override these values if necessary.*")

    default_costs = st.session_state.app_settings['phase_defaults']['Cost ($M)']
    default_durations = st.session_state.app_settings['phase_defaults']['Duration (Yrs)']
    
    phase_data = []
    cols = st.columns(len(PHASES))
    for i, phase in enumerate(PHASES):
        
        if f"p_{i}" not in st.session_state:
            st.session_state[f"p_{i}"] = float(current_pos[i])
        if f"c_{i}" not in st.session_state:
            st.session_state[f"c_{i}"] = float(default_costs[i])
        if f"d_{i}" not in st.session_state:
            st.session_state[f"d_{i}"] = int(default_durations[i])
            
        with cols[i]:
            st.markdown(f"**{phase}**")
            cost = st.number_input(f"Cost ($M)", key=f"c_{i}")
            duration = st.number_input(f"Duration (Yrs)", key=f"d_{i}")
            pos = st.number_input(f"PoS (%)", key=f"p_{i}") / 100
            
            phase_data.append({"Phase": phase, "Cost": cost, "Duration": duration, "PoS": pos})

    if st.button("🚀 Run rNPV & Monte Carlo Analysis", type="primary", use_container_width=True):
        
        # --- Standard Deterministic rNPV Calculation ---
        cash_flows = []
        year_labels = []
        cumulative_pos = 1.0
        current_year = 1
        
        for p in phase_data:
            for year in range(int(p["Duration"])):
                annual_cost = -(p["Cost"] / p["Duration"])
                r_cf = annual_cost * cumulative_pos
                cash_flows.append(r_cf)
                year_labels.append(f"Y{current_year}\n{p['Phase']}")
                current_year += 1
            cumulative_pos *= p["PoS"]
        
        final_pos = cumulative_pos
        annual_profit = peak_sales_expected * (1 - cogs_sgna_rate)
        
        for year in range(int(commercial_years)):
            r_cf = annual_profit * final_pos
            cash_flows.append(r_cf)
            year_labels.append(f"Y{current_year}\nLaunch")
            current_year += 1

        standard_rnpv = npf.npv(discount_rate, cash_flows)
        
        # --- Monte Carlo Simulation ---
        simulated_npvs = []
        success_count = 0
        annual_costs = [-(p["Cost"] / p["Duration"]) for p in phase_data for _ in range(int(p["Duration"]))]
        phase_durations = [int(p["Duration"]) for p in phase_data]
        phase_probs = [p["PoS"] for p in phase_data]
        
        for _ in range(n_simulations):
            sim_cf = []
            is_active = True
            current_idx = 0
            
            for phase_idx, duration in enumerate(phase_durations):
                if is_active:
                    for _ in range(duration):
                        sim_cf.append(annual_costs[current_idx])
                        current_idx += 1
                    if np.random.rand() > phase_probs[phase_idx]:
                        is_active = False 
                else:
                    for _ in range(duration):
                        sim_cf.append(0)
                        current_idx += 1
                        
            if is_active:
                success_count += 1
                sim_peak_sales = np.random.triangular(peak_sales_min, peak_sales_expected, peak_sales_max)
                sim_annual_profit = sim_peak_sales * (1 - cogs_sgna_rate)
                for _ in range(int(commercial_years)):
                    sim_cf.append(sim_annual_profit)
            else:
                for _ in range(int(commercial_years)):
                    sim_cf.append(0)
                    
            simulated_npvs.append(npf.npv(discount_rate, sim_cf))

        simulated_npvs = np.array(simulated_npvs)
        
        # --- Display Results ---
        st.divider()
        st.header("📊 Final Results")
        
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        col_res1.metric("Cumulative Launch PoS", f"{final_pos * 100:.2f}%")
        col_res2.metric("Total Dev Time", f"{current_year - 1 - commercial_years} Yrs")
        col_res3.metric("Standard rNPV", f"${standard_rnpv:,.1f} M")
        col_res4.metric("Simulated eNPV", f"${np.mean(simulated_npvs):,.1f} M")

        # --- Re-introducing Result Tabs ---
        tab_res_yearly, tab_res_mc = st.tabs(["📅 Yearly Cash Flow", "🎲 Monte Carlo Analysis"])

        with tab_res_yearly:
            st.subheader("Risk-Adjusted Cash Flow Projection")
            fig1, ax1 = plt.subplots(figsize=(12, 5))
            ax1.bar(range(len(cash_flows)), cash_flows, color=['red' if cf < 0 else 'green' for cf in cash_flows])
            ax1.plot(range(len(cash_flows)), np.cumsum(cash_flows), color='blue', marker='o', label='Cumulative rCF')
            
            ax1.set_xticks(range(len(cash_flows)))
            ax1.set_xticklabels(year_labels, rotation=45, ha='right', fontsize=8)
            ax1.axhline(0, color='black', linewidth=1)
            ax1.set_ylabel("Cash Flow ($ Millions)")
            ax1.legend()
            st.pyplot(fig1)

            st.subheader("Detailed Yearly Data")
            df_export = pd.DataFrame({
                "Year & Phase": [label.replace('\n', ' - ') for label in year_labels],
                "Risk-Adjusted CF ($M)": cash_flows,
                "Cumulative rCF ($M)": np.cumsum(cash_flows)
            })
            st.dataframe(df_export.style.format({"Risk-Adjusted CF ($M)": "{:,.2f}", "Cumulative rCF ($M)": "{:,.2f}"}), use_container_width=True)

            st.markdown("<br>", unsafe_allow_html=True)
            csv_data = df_export.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Yearly Data (CSV)",
                data=csv_data,
                file_name='rnpv_yearly_projection.csv',
                mime='text/csv',
                type="primary"
            )

        with tab_res_mc:
            st.subheader(f"Monte Carlo Distribution ({n_simulations} Scenarios)")
            fig2, ax2 = plt.subplots(figsize=(12, 5))
            ax2.hist(simulated_npvs, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
            
            p10, p50, p90 = np.percentile(simulated_npvs, [10, 50, 90])
            ax2.axvline(p10, color='red', linestyle='dashed', linewidth=2, label=f'10th Pctl (Downside): ${p10:,.0f}M')
            ax2.axvline(p50, color='green', linestyle='dashed', linewidth=2, label=f'50th Pctl (Median): ${p50:,.0f}M')
            ax2.axvline(p90, color='purple', linestyle='dashed', linewidth=2, label=f'90th Pctl (Upside): ${p90:,.0f}M')
            
            ax2.set_xlabel("Net Present Value ($ Millions)")
            ax2.set_ylabel("Frequency")
            ax2.legend()
            st.pyplot(fig2)

            st.subheader("Risk Metrics")
            metrics_df = pd.DataFrame({
                "Metric": ["Downside (10th Pctl)", "Median (50th Pctl)", "Upside (90th Pctl)", "Prob. of Positive NPV"],
                "Value": [f"${p10:,.1f} M", f"${p50:,.1f} M", f"${p90:,.1f} M", f"{(np.sum(simulated_npvs > 0) / n_simulations) * 100:.1f}%"]
            })
            st.table(metrics_df)