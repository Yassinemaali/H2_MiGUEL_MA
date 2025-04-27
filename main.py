
import datetime as dt
import pandas as pd
from pathlib import Path
from environment import Environment
from operation import Operator
from evaluation import Evaluation
from Reporting import Reporting
print("Evaluation-Klasse geladen aus:", Evaluation.__module__)

from report.report import Report
from multiprocessing import Pool, cpu_count
from itertools import product

import os
print("Aktueller Arbeitsordner:", os.getcwd())


def demonstration(grid_connection=False, n_pv_modules= None, el_power= None, capacity= None, storage_cap = None ):
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

    # Kürzen auf die ersten 8760 Zeilen (365 Tage)
    df = df.iloc[:8760]

    # 2. Speichern als saubere Version für Load-Klasse
    df.to_csv("Caiambe-Data-CLEAN.csv", sep=";", decimal=",") # Pfad kann beliebig sein

    environment.add_load(load_profile="Caiambe-Data-CLEAN.csv")

    for _ in range(n_pv_modules):
        environment.add_pv(p_n=100000, pv_profile=df["PV [W]"],
                           pv_data={'surface_tilt': 20, 'surface_azimuth': 90, 'min_module_power': 300,
                                    'max_module_power': 400, 'inverter_power_range': 2500})

    if not grid_connection:
        environment.add_storage(p_n=700000,
                                c=storage_cap,
                                soc=0.25)
        # **Wasserstoffkomponenten hinzufügen**
        # elektrolyseur mit p_n Leistung [W]
        environment.add_electrolyser(p_n=el_power,
                                     c_op_main_n= 21.16,
                                     c_invest_n=2115.19,
                                     lifetime=20)
        # Wasserstoffspeicher, Kapazität [kg]
        environment.add_H2_Storage(capacity= capacity,
                                   initial_level=0.1,
                                   c_invest_n=610.10,
                                   c_op_main_n=0
                                   )

        # Brennstoffzelle, maximale Leistung [W]
        environment.add_fuel_cell(max_power=700000,
                                  efficiency=0.6,
                                  c_invest_n=3421.53,
                                  c_op_main_n=0,
                                  lifetime= 50000)

    return environment

pv_modules = [30,35,40,50,60,70]
electrolyser_sizes = [2000000,2500000,3000000,3500000,4000000,5000000,6000000]
capacity=[500,1000,1500,2000,2500,3000]
storage= [1000000, 1500000,2000000]
all_results = []
for storage_size in storage:
    for h2_cap in capacity:
        results_block=[]
        for pv_factor in pv_modules:
            for el_p in electrolyser_sizes:
                print(f"▶️ Running: PV={pv_factor}, EL={el_p}, H2={h2_cap}, Storage={storage_size}")
                # Umgebung erzeugen
                env= demonstration(grid_connection=False, n_pv_modules= pv_factor, el_power=el_p, capacity=h2_cap, storage_cap=storage_size)

                operator = Operator(env=env)
                evaluation = Evaluation(env=env, operator=operator)

                lcoe = evaluation.evaluation_df.loc['System', 'LCOE [US$/kWh]']
                co2 = evaluation.evaluation_df.loc['System', 'Lifetime CO2 emissions [t]']

                p_res = operator.df['P_Res [W]'].sum() / 1000000
                total = operator.df['Load [W]'].sum() / 1000000
                coverage = round((1 - p_res / total) * 100, 2)

                results_block.append({
                    "El_Power [W]": el_p,
                    "PV_Modules": pv_factor,
                    "Uncovered_Load [MWh]": round(p_res, 2),
                    "Coverage [%]": coverage,
                    "H2 Storage [kg]" : h2_cap,
                    'LCOE [US$/kWh]': lcoe,
                    'CO2_emissions [t]': co2,
                    'Storage capacity [Wh]': storage_size
                })

        # ✅ Speichern nach jedem Speicherblock
        filename = f"sensitivity_H2_{h2_cap}kg_storage_{storage_size}Wh.xlsx"
        pd.DataFrame(results_block).to_excel(filename, index=False)



