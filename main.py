
import datetime as dt
import pandas as pd
from pathlib import Path
from environment import Environment
from operation import Operator
from evaluation import Evaluation
from Reporting import Reporting
from Sizing import Sizing
import matplotlib.pyplot as plt
import math
from scipy.optimize import minimize

from report.report import Report
from multiprocessing import Pool, cpu_count
from itertools import product
import seaborn as sns
import os
print("Aktueller Arbeitsordner:", os.getcwd())


def demonstration(grid_connection=False, n_modul=None,H2_stor= None, Bat_cap=None, el= None):
    """
    Create an Off grid system with the following system components
        - PV: 60 kWp
        - Electrolyser : 30 kW
        - Hydrogen Storage : 500 KG
        - Battery storage: 10 kW/30kWh
        - Fuel Cell:30kW
    :return: environment
    """
    if grid_connection:
        name = 'Grid connected system'
    else:
        name = 'Off grid system'

    # Add parameters to create environment
    environment = Environment(name="Caiambé-Tefé AM",
                              location={'latitude': -3.532906,
                                        'longitude': -64.410861,
                                        'terrain': 'Villages, small towns, agricultural buildings with many or high '
                                                   'hedges, woods and very rough and uneven terrain'},
                              time={'start': dt.datetime(year=2024,
                                                         month=1,
                                                         day=1,
                                                         hour=0,
                                                         minute=0),
                                    'end': dt.datetime(year=2024,
                                                       month=12,
                                                       day=30,
                                                       hour=23,
                                                       minute=59),
                                    'step': dt.timedelta(hours=1),
                                    'timezone': 'Etc/GMT-4'},
                              economy={'d_rate': 0.03,
                                       'lifetime': 20,
                                       'electricity_price': 0.152,
                                       'pv_feed_in_tariff': 0,
                                       'wt_feed_in_tariff': 0,
                                       'co2_price': 0,
                                       'currency': 'US$'},
                              ecology={'co2_diesel': 0.2665,
                                       'co2_grid': 0.098},
                              grid_connection=grid_connection,
                              feed_in=False,
                              blackout=False,
                              blackout_data=None,
                              csv_decimal=',',
                              csv_sep=';')



    # 1. Excel einlesen
    df = pd.read_csv("Caiambe-Data.csv", sep=";", decimal=",", index_col=0)

    # 2. Index in datetime umwandeln
    df.index = pd.to_datetime(df.index, dayfirst=True)
    df = df.iloc[:8760]  # Kürzen auf 365 Tage

  
    environment.add_load(load_profile="Caiambe-Data-CLEAN.csv")

    #Num_module = math.ceil(cap_pv / 100)

    for pv in range (n_modul):
        environment.add_pv(p_n=100000, pv_profile=df["PV [W]"],
                           pv_data={'surface_tilt': 20, 'surface_azimuth': 90, 'min_module_power': 300,
                                    'max_module_power': 400, 'inverter_power_range': 2500})

    if not grid_connection:
        environment.add_storage(p_n=550_000,
                                c=Bat_cap,
                                soc=0.25)
        # **Wasserstoffkomponenten hinzufügen**
        # elektrolyseur mit p_n Leistung [W]
        environment.add_electrolyser(p_n=el,
                                     c_op_main_n= 21.16,
                                     c_invest_n=2115.19,
                                     lifetime=20)
        # Wasserstoffspeicher, Kapazität [kg]
        environment.add_H2_Storage(capacity=H2_stor,
                                   initial_level=0.05,
                                   c_invest_n=610.10,
                                   c_op_main_n=0
                                   )
        # Brennstoffzelle, maximale Leistung [W]
        environment.add_fuel_cell(max_power=550_000,
                                  c_invest_n=3421.53,
                                  c_op_main_n=0,
                                  lifetime=10)

    return environment

results_block2 = []
PV=[25,35,45,30,40,50]
#PV=[25,35,45]
#El_leistung= [500_000,750_000,1_000_000]
El_leistung= [500_000,750_000,1_000_000,1_500_000,2_000_000,3_000_000]
H2_STOR = [1000,2000,3000,4000,5000,6000]
#batterie= [3_000_000,4_000_000,5_000_000]
batterie= [1_000_000,2_000_000,6_000_000]

  # fix: 1.3 MW
for n in PV:
    for el in El_leistung:
        for bat in batterie:
            for h2 in H2_STOR :
                env = demonstration(grid_connection=False, Bat_cap=bat, H2_stor=h2, el=el, n_modul=n)
                operator = Operator(env=env)
                evaluation = Evaluation(env=env, operator=operator)

                lcoe = evaluation.evaluation_df.loc['System', 'LCOE [US$/kWh]']
                co2 = evaluation.evaluation_df.loc['System', 'Lifetime CO2 emissions [t]']
                H2_Anteil = (
                    evaluation.evaluation_df.loc['FuelCell_1', 'Annual energy supply [kWh/a]']
                    / evaluation.evaluation_df.loc['System', 'Annual energy supply [kWh/a]']
                ) * 100

                p_res = operator.df['P_Res [W]'].sum() / 1_000_000
                total = operator.df['Load [W]'].sum() / 1_000_000
                coverage = round((1 - p_res / total) * 100, 2)

                results_block2.append({
                    "Batterie [kWh]": bat / 1000,
                    "H2 Storage [kg]":h2,
                    "Coverage [%]": coverage,
                    "Uncovered_Load [MWh]": round(p_res, 2),
                    "H2-Anteil [%]": round(H2_Anteil, 2),
                    "LCOE [US$/kWh]": round(lcoe, 2),
                    "CO2_emissions [t]": round(co2, 2),
                    "El_Power [kW]": el / 1000,
                    "PV [kWp]": n*100
                })

# ✅ Speichern
df = pd.DataFrame(results_block2)
filename = "sensitivitaet_komplett4.xlsx"
df.to_excel(filename, index=False)
print(f"✅ Ergebnisse gespeichert in: {filename}")


