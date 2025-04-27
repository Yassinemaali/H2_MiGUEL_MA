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
                 c_invest_n: float=1854.6,  # Euro/kw
                 c_invest: float= None,
                 c_op_main_n: float=18.55,  #Euro/kw
                 c_op_main: float = None,
                 co2_init: float = 36.95, # kg co2/kW für einen PEM Electrolyser
                 c_var_n: float = 0,
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
        self.c_var_n = c_var_n          #USD/kW
        if c_invest is None:
           self.c_invest = c_invest_n * self.p_n / 1000
        else:
            self.c_invest = c_invest
        if c_op_main_n is not None:
            self.c_op_main_n = c_op_main_n
        else:
            self.c_op_main_n = self.c_invest_n * 0.03  # USD/kW
        #Operation Cost
        self.c_op_main_n= c_op_main_n
        if c_op_main is None:
            self. c_op_main = self.c_op_main_n * self.p_n / 1000
        else:
            self.c_op_main = c_op_main
        #Co2 Cost
        self.co2_init = co2_init * self.p_n/1000   # kg

        self.life_time=life_time

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
        if power <= self.p_n:
            power = power
        else:
            power = self.p_n

        p_relative = round(((power/self.p_n) * 100),2)

        self.df_electrolyser.at[clock, 'P[%]'] = p_relative

        if p_relative >= self.p_min:      # Bedingung minimale Leisteung
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
        data = pd.read_csv(r'C:\Users\yessi\OneDrive\Documents\MasterEE\Masterarbeit\Code\Miguel_H2_PV\miguel-master_V4\H2_MiGUEL_MA\data\elektrolyseur_data .csv',
                           sep=';', decimal='.')

        return data

    def calc_H2_production(self,clock:dt.datetime,power: float):
        """

        :param power:
        :return:
        """

        spez_verbrauch = self.spez_elec_cons_interpolator(self.df_electrolyser.at[clock, 'P[%]'])   # [kWh/Nm3]

        power = round((power/1000) * (self.env.i_step / 60),2)                                  # kWh
        h2_production = round((power/spez_verbrauch)/11.89, 2)if spez_verbrauch > 0 else 0

        if h2_production > 0:
            self.df_electrolyser.at[clock, 'H2_Production [kg]'] = h2_production
        else:
            self.df_electrolyser.at[clock, 'H2_Production [kg]'] = 0

        return h2_production














































