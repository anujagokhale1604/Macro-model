# 🏛️ Quantitative Policy Lab
### *A Monetary Policy Simulation & Teaching Tool*

This laboratory provides an interactive interface for analyzing Central Bank behavior across different economic regimes. Developed as a graduate-level research tool, it utilizes the **Taylor Rule** framework to bridge the gap between macroeconomic theory and real-world policy application.



## 🕊️ Design Philosophy
Unlike typical high-contrast financial terminals, this lab is built with a **"Gentle Research"** aesthetic—utilizing a parchment-and-slate palette to focus on clarity, readability, and academic rigor.

## 🧠 Interactive Teaching Modules

### 1. Macro Scenario Simulator
Allows users to instantly observe how different economic shocks force policy trade-offs:
* **Stagflation Shock:** High inflation + Negative output gap.
* **Global Recession:** Deflationary pressure + Deep output gap.
* **Soft Landing:** Inflation convergence with minimal growth disruption.

### 2. Behavioral Calibration
Users can toggle between central banking philosophies:
* **Inflation Hawk:** Prioritizes price stability with high sensitivity to CPI deviations.
* **Dual Mandate:** Balances inflation targets with economic growth (Output Gap).
* **Standard:** A balanced historical Taylor approach.

### 3. Structural Parameters
* **Neutral Rate ($r^*$):** Adjust the "anchor" rate where the economy is in equilibrium.
* **Policy Inertia:** Demonstrates "Smoothing," showing why banks move in small increments (e.g., 25bps) rather than jumping to fair value instantly.

## 🛠️ Technical Implementation
* **Language:** Python
* **Interface:** Streamlit (Custom CSS for Parchment UI)
* **Visuals:** Plotly (High-visibility academic styling)
* **Framework:** Taylor Rule Monetary Model

## 📊 Analytical Indicators
The terminal calculates a **Policy Gap** in **Basis Points (bps)**—the industry standard for JPMC, Goldman Sachs, and BCG—indicating whether a market is "over-tightened" or "behind the curve."

---
**Developed by:** [Your Name]  
**Focus:** Macroeconomics & Financial Policy Research
