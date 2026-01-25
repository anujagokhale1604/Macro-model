# 🏛️ Quantitative Policy Lab: Monetary Policy Simulator

An interactive macroeconomic research terminal designed to simulate Central Bank interest rate decisions using the **Taylor Rule** framework. This tool allows researchers and students to visualize the impact of inflation shocks, growth gaps, and differing banking philosophies on terminal interest rates.

## 🌟 Key Features
* **Multi-Market Analysis:** Real-time simulations for India, UK, and Singapore.
* **Macro Scenario Toggles:** Instantly simulate "Stagflation," "Soft Landings," or "Global Recessions."
* **Custom Policy Calibration:** Manually adjust Neutral Real Rates ($r^*$), Inflation Targets, and Smoothing factors.
* **Visual Intelligence:** High-fidelity Plotly charts comparing historical policy rates against model fair-value projections.

## 🛠️ The Framework
The core engine utilizes the Taylor Rule equation:
$$i = r^* + \pi + \lambda_{\pi}(\pi - \pi^*) + \lambda_{y}(y - y^*)$$

Where:
* $i$: Suggested Nominal Policy Rate
* $r^*$: Neutral Real Interest Rate
* $\pi$: Current Inflation
* $\pi^*$: Inflation Target
* $y - y^*$: The Output Gap



## 🚀 Getting Started

### Prerequisites
* Python 3.8+
* Streamlit
* Plotly
* Pandas

### Installation
1. Clone the repository:
   ```bash
   git clone [https://github.com/your-username/policy-lab.git](https://github.com/your-username/policy-lab.git)
