import pandas as pd
import numpy as np
import datetime as dt
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt


class Electrolyser:
    def __init__(self,
                 env= None,
                 name: str= None,
                 p_n: float = None,
                 c_invest_n: float=None,
                 c_invest: float=None,
                 c_op_main_n: float=None,
                 c_op_main: float = None,
                 life_time: float = None):

        self.env = env
        self.p_n = p_n
        self.name = name
        self.p_min = 10
        self.efficiency_electrolyser = None

        self.df_electrolyser = pd.DataFrame(columns=['P[W]',
                                        'P[%]',
                                        'H2_Production [kg]',
                                        'LCOH [$/kg]'], index=self. env.time)
        self.efficiency_data = self. load_efficiency_curve()


        self.spez_elec_cons_interpolator = interp1d (self.efficiency_data["BOP [%]"],
                                                     self.efficiency_data["Spez.Energieverbrauch [kWh/Nm3]"],
                                                     kind='linear',
                                                     fill_value="extrapolate")


        # Economic parameters
        self.c_invest_n = c_invest_n    #USD/kw
        if c_invest is None:
           self.c_invest = c_invest_n * self.p_n / 1000
        else:
            self.c_invest = c_invest
        if c_op_main_n is not None:
            self.c_op_main_n = c_op_main_n
        else:
            self.c_op_main_n = self.c_invest_n * 0.03  # USD/kW
        if c_op_main is None:
            self. c_op_main = self.c_op_main_n * self.p_n / 1000
        else:
            self.c_op_main = c_op_main


        # Technical data
        self.technical_data = { 'component': 'Elektrolyseur',
                               'Name': self.name,
                               'Nominal power [kW]': round ( self.p_n/1000, 3),
                               f'specific investment cost [US$/kW]': int(self.c_invest_n),
                               f'investment cost [US$]': int(self.c_invest),
                               f'specific operation maintenance cost[US $/ kW]': int(self.c_op_main_n),
                               f'operation maintenance cost [US$/a]': int(self.c_op_main_n * self.p_n / 1000)}

    def run (self,
             clock,
             power: float):
        """
        Run Electrolyser
        :param clock: dt.datetime
               time stamp
        :param power: float
               power[W]
        :return: clock power
        """
        print(f"DEBUG: run() aufgerufen für clock={clock}, power={round(power,2)}")
        if power <= self.p_n:
            power = power
        else:
            power = self.p_n

        p_relative = round(((power/self.p_n) * 100),2)

        self.df_electrolyser.at[clock, 'P[%]'] = p_relative
        #print(self.df_electrolyser.tail(5))  # Letzte 5 Zeilen anzeigen

        print(f"DEBUG: um {clock} ist die P_relativ {p_relative} %")
        if p_relative >= self.p_min:                                                # Bedingung minimale Leisteung
            h2_production = self. calc_H2_production(clock, power=power)

            #set values
            self.df_electrolyser.at[clock, 'P[W]'] = round(power,2)
            self.df_electrolyser.at[clock, 'P[%]'] = p_relative
            self.df_electrolyser.at[clock, 'H2_Production [kg]'] = h2_production

        else:
            self.df_electrolyser.at[clock, 'P[W]'] = 0
            self.df_electrolyser.at[clock, 'P[%]'] = 0
            self.df_electrolyser.at[clock, 'H2_Production [kg]'] = 0
        #self.df_electrolyser.at[clock, 'LCOH [$/kg]'] = lcoh

        return

    def load_efficiency_curve (self):
        """
        load efficiency curve form CSV  file

        """
        data = pd.read_csv(r'C:\Users\yessi\OneDrive\Documents\MasterEE\Masterarbeit\Code\Miguel_H2_PV\miguel-master - Kopie\data\elektrolyseur_data .csv', sep=';', decimal='.')

        return data

    def calc_H2_production(self,clock:dt.datetime,power: float):
        """

        :param power:
        :return:
        """

        print(f"DEBUG: P_relativ für Interpolation: {self.df_electrolyser.at[clock, 'P[%]']}")
        print(self.df_electrolyser.head(10))
        spez_verbrauch = self.spez_elec_cons_interpolator(self.df_electrolyser.at[clock, 'P[%]'])  # W/kg  # [kWh/Nm3]
        print(f"DEBBUG: der spezifische Verbrauch liegt um {clock} bei {spez_verbrauch} [kWh/Nm3]")
        power = round((power/1000) * (self.env.i_step / 60),2) # W
        h2_production = round((power/spez_verbrauch)/11.89, 2)if spez_verbrauch > 0 else 0                   # kg   1KG = 11,126 Nm3
        print(f"DEBBUG: H2 Produktion in calc H2 Methode um {clock} ist {h2_production} kg ")



        if h2_production > 0:
           self.df_electrolyser.at[clock, 'H2_Production [kg]'] = h2_production
           #print(f"DEBBUG: H2 production um {clock} wird gespeichert in Dataframe {self.df_electrolyser.at[clock, 'H2_Production [kg]']}")
        else:
            self.df_electrolyser.at[clock, 'H2_Production [kg]'] = 0

        return h2_production


    def calc_lcoh (self):
        """
        calculate LCOH
        :return:

        """
        annual_h2_production = self.df_electrolyser['H2_Production [kg]'].sum()

        if annual_h2_production <= 0:
            return float ('inf')

        lcoh = (self.c_invest + self.c_op_main)/annual_h2_production

        #self.df_electrolyser.at[clock, 'LCOH [$/kg]'] = lcoh

        return lcoh



    def plot_electrolyser_power(self):
        plt.figure(figsize=(12, 6))
        plt.plot(self.df_electrolyser.index, self.df_electrolyser["P[W]"], label="Elektrolyser Power [W]", linewidth=1)
        plt.xlabel("Zeit")
        plt.ylabel("Leistung [W]")
        plt.title("Elektrolyseur Eingangsleistung über die Zeit")
        plt.legend()
        plt.grid()
        plt.show()



    # Funktion zum Plotten des Diagramms
    def plot_dual_axis(dates, power, h2, season):
        fig, ax1 = plt.subplots(figsize=(10, 5))
        # Beispielhafte simulierte Daten
        # Ersetze diese Daten mit deinen echten Werten
        dates = pd.date_range(start="2024-06-01", periods=24, freq="H")  # Sommer: 1 Tag stündlich
        power_summer = [5000 + i * 100 for i in range(24)]  # Eingangsleistung steigt
        h2_summer = [p / 5000 for p in power_summer]  # Wasserstoffproduktion skaliert

        dates_winter = pd.date_range(start="2024-12-01", periods=24, freq="H")  # Winter: 1 Tag stündlich
        power_winter = [3000 + i * 50 for i in range(24)]  # Geringere Eingangsleistung
        h2_winter = [p / 5000 for p in power_winter]  # Geringere H₂-Produktion

        # Linke Achse (Eingangsleistung)
        ax1.set_xlabel("Zeit")
        ax1.set_ylabel("Eingangsleistung (W)", color="tab:blue")
        ax1.plot(dates, power, label="Eingangsleistung", color="tab:blue")
        ax1.tick_params(axis="y", labelcolor="tab:blue")

        # Rechte Achse (H₂-Produktion)
        ax2 = ax1.twinx()
        ax2.set_ylabel("Wasserstoffproduktion (kg)", color="tab:green")
        ax2.plot(dates, h2, label="H₂-Produktion", color="tab:green", linestyle="dashed")
        ax2.tick_params(axis="y", labelcolor="tab:green")

        plt.title(f"Simulation für {season}")
        fig.tight_layout()
        plt.show()








































