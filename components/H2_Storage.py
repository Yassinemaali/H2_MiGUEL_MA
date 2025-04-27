import pandas as pd
import datetime as dt
from components.Electrolyser import Electrolyser




class H2Storage:
    """
    Class to simulate hydrogen storage in a standalone manner.
    This class manages hydrogen inflow, outflow, and storage levels without environment integration.

    1) Der Speicher wird initialisiert auf soc_min
    2) Wenn die Update Methode mit INFLOW aufgerufen wird, wird der Speicher aufgeladen und der Speicher Niveau aktualisiert
    3) Wenn die Update Methode mit Outflow aufgerufen wird, wird der Speicher entgeladen und der Speicher Niveau aktualisiert
    """

    def __init__(self,
                 env,
                 co2_init: float = 48,      # 48 kg/ kg H2
                 capacity: float= None ,     #[kg]
                 initial_level: float = None,  #[%]
                 name: str = None,
                 c_invest : float = None,  # [USD]
                 c_invest_n: float = 534.94,   #[Euro/kg oder kwh]
                 c_op_main: float = None,  # [USD/a]
                 c_op_main_n: float = 0,    #[USD/kg]
                 c_var_n: float = 0,
                 lifetime:int = 25
                 ):
        """
        Initialize the hydrogen storage.

        :param capacity: Total storage capacity in kilograms (kg).
        :param initial_level: Initial hydrogen level in the storage (kg).
        """
        self.env = env
        self.soc_min = 0.1
        self.soc_max = 0.95
        self.name = name
        self.capacity = capacity  # Maximum storage capacity in kg
        self.current_level = initial_level*capacity  # Current storage level in kg
        self.lifetime= lifetime

        # Emissionsdaten
        self.co2_init = co2_init * self.capacity  # kg CO₂


        # Kosten
        # Investement cost [USD]
        self.invest_cost =c_invest
        if c_invest is None:
           self.c_invest = c_invest_n * self.capacity
        else:
            self.c_invest = c_invest
        #Operation Cost
        self.c_op_main = c_op_main     # USD /a
        self.c_op_main_n = c_op_main_n   #USD /KG ODER kw

        if c_op_main is None:
            self.c_op_main = self.c_op_main_n * self.capacity
        else:
            self.c_op_main = c_op_main

        #variable COST
        self.c_var_n = c_var_n
        self.c_var = self.c_var_n * self.capacity

        # If initial_level is not given, start at 50% capacity
        self.current_level = initial_level if initial_level is not None else 0.25 * self.capacity


        # DataFrame to track storage levels and flows over time
        self.hstorage_df = pd.DataFrame(columns=['H2 Inflow [kg]',
                                                'H2 Outflow [kg]',
                                                'Storage Level [kg]',
                                                 'SOC [%]',
                                                 'Q[Wh]'], index= self.env.time)
        #self.set_initial_values()

        # Set initial values in dataframe
        initial_soc = self.current_level / self.capacity
        start_time = self.env.time[0]
        self.hstorage_df.at[start_time, 'Storage Level [kg]'] = self.current_level
        self.hstorage_df.at[start_time, 'SOC'] = initial_soc

        self.technical_data = {
            'Component': 'Hydrogen Storage',
            'Name': f'H2Storage_{id(self)}',  # Unique identifier for each instance
            'Capacity [kg]': self.capacity,
            'Initial Level [kg]': self.current_level,

        }



    def charge(self, clock: dt.datetime, inflow: float, el: Electrolyser):
        """
        Charge the hydrogen storage.

        :param clock: Current timestamp.
        :param inflow: Amount of hydrogen added to the storage (kg).
        """
        time_step = self.env.i_step / 60

        if inflow < 0:
            inflow = 0 # Kein Ladevorgang, falls kein Inflow vorhanden

        if inflow == 0:
            new_level = self.current_level
        else:
            new_level = self.current_level + inflow

        if new_level > self.capacity:
            inflow = self.capacity - self.current_level  # Anpassung, um Überlauf zu verhindern
            new_level = self.capacity

        self.current_level = new_level

        soc = (self.current_level / self.capacity)*100
        charge = 33.33 * inflow * 1000 * time_step   #[W]

        # Logging ins DataFrame
        self.hstorage_df.at[clock, 'H2 Inflow [kg]'] = inflow
        self.hstorage_df.at[clock, 'H2 Outflow [kg]'] = 0
        self.hstorage_df.at[clock, 'Storage Level [kg]'] = new_level
        self.hstorage_df.at[clock, 'SOC [%]'] = soc
        self.hstorage_df.at[clock, 'Q[Wh]'] += charge
        #self.storage_df.at[clock, 'H2 Production [kg]'] = el.df_electrolyser.at[clock, 'H2_Production [kg]']


        return

    def discharge(self, clock: dt.datetime, outflow: float):
        """
        Discharge hydrogen from the storage.

        :param clock: Current timestamp.
        :param outflow: Amount of hydrogen withdrawn from the storage (kg).
        """
        time_step = self.env.i_step / 60
        if outflow <= 0:
            return   # Kein Entladevorgang, falls kein Outflow vorhanden

        new_level = self.current_level - outflow

        if new_level < 0:
            outflow = self.current_level  # Anpassung, um Unterlauf zu verhindern
            new_level = 0

        self.current_level = new_level

        soc = (self.current_level / self.capacity)*100
        discharge = 33.33 * outflow * 1000 * time_step

        # Logging ins DataFrame
        self.hstorage_df.at[clock, 'H2 Inflow [kg]'] = 0
        self.hstorage_df.at[clock, 'H2 Outflow [kg]'] = outflow
        self.hstorage_df.at[clock, 'Storage Level [kg]'] = new_level
        self.hstorage_df.at[clock, 'SOC [%]'] = soc
        self.hstorage_df.at[clock, 'Q[Wh]'] -= discharge


        return
