import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from operation import Operator
from evaluation import Evaluation

class Reporting:
    def __init__(self, operator, evaluation):
        self.operator = operator
        self.evaluation = evaluation

    def run(self):
        report = Reporting(operator=Operator, evaluation=Evaluation)
        report.plot_energy_sankey()
        report.plot_energy_contribution()
        report.show_economic_summary()

    def plot_energy_sankey(self):
        # Daten aus Evaluation (in kWh)^^
        df_eval = self.evaluation.df

        pv_total = df_eval.loc['PV total production [kWh]', 'Value']
        pv_to_load = df_eval.loc['PV to Load [kWh]', 'Value']
        pv_to_storage = df_eval.loc['PV to Battery + Electrolyser [kWh]', 'Value']
        battery_discharge = df_eval.loc['Battery to Load [kWh]', 'Value']
        h2_to_load = df_eval.loc['FuelCell to Load [kWh]', 'Value']
        uncovered = df_eval.loc['Uncovered Load [kWh]', 'Value']
        load_total = df_eval.loc['Total Load [kWh]', 'Value']

        labels = [
            "PV Total", "PV to Load", "PV to Storage",
            "Battery Discharge", "H2 System", "Uncovered Load",
            "Load"
        ]

        sources = [0, 0, 2, 2, 4, 5]
        targets = [1, 2, 3, 4, 6, 6]
        values = [pv_to_load, pv_to_storage, battery_discharge, h2_to_load, h2_to_load, uncovered]

        fig = go.Figure(go.Sankey(
            node=dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=labels),
            link=dict(source=sources, target=targets, value=values)
        ))

        fig.update_layout(title_text="Energy Flow Sankey Diagram", font_size=12)
        fig.show()

    def plot_energy_contribution(self):
        df_eval = self.evaluation.df
        values = {
            "Direct PV to Load": df_eval.loc['PV to Load [kWh]', 'Value'],
            "Battery to Load": df_eval.loc['Battery to Load [kWh]', 'Value'],
            "H2 System to Load": df_eval.loc['FuelCell to Load [kWh]', 'Value'],
            "Uncovered Load": df_eval.loc['Uncovered Load [kWh]', 'Value']
        }

        total = sum(values.values())
        percent = {k: round(v / total * 100, 2) for k, v in values.items()}

        fig, ax = plt.subplots()
        ax.bar(percent.keys(), percent.values(), color='skyblue')
        ax.set_ylabel("Percentage of Total Load [%]")
        ax.set_title("Load Coverage by Component")
        plt.xticks(rotation=20)
        plt.tight_layout()
        plt.show()

    def show_economic_summary(self):
        df_eval = self.evaluation.df
        economic = df_eval[df_eval.index.str.contains("\[\$", regex=True)]
        print("Economic Summary:")
        print(economic)

    def export_summary_pdf(self):
        print("[TODO] PDF Export not yet implemented.")
