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

    def __init__(self, env, capacity: float, initial_level: float = 0, name: str = None, energy: float = None):
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
        self.energy = energy
        self.current_level = initial_level  # Current storage level in kg

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
        print(f"DEBUG: Wasserstoffspeicher wird geladen mit {inflow} kg um {clock}")

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

        soc = self.current_level / self.capacity
        charge = 33.33 * inflow * 1000 * 0.25   #[W]

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
        print(f"DEBUG: Wasserstoffspeicher wird entladen mit {outflow} kg um {clock}")

        if outflow <= 0:
            return   # Kein Entladevorgang, falls kein Outflow vorhanden

        new_level = self.current_level - outflow

        if new_level < 0:
            outflow = self.current_level  # Anpassung, um Unterlauf zu verhindern
            new_level = 0

        self.current_level = new_level

        soc = self.current_level / self.capacity
        discharge = 33.33 * outflow * 1000 * 0.25

        # Logging ins DataFrame
        self.hstorage_df.at[clock, 'H2 Inflow [kg]'] = 0
        self.hstorage_df.at[clock, 'H2 Outflow [kg]'] = outflow
        self.hstorage_df.at[clock, 'Storage Level [kg]'] = new_level
        self.hstorage_df.at[clock, 'SOC [%]'] = soc
        self.hstorage_df.at[clock, 'Q[Wh]'] -= discharge


        return
    '''

    def update(self, clock: dt.datetime, inflow: float, outflow: float):
        """
        Update the storage state for a given simulation step.

        :param inflow: Amount of hydrogen added to the storage (kg).
        :param outflow: Amount of hydrogen withdrawn from the storage (kg).
        :param current_time: The timestamp or time index for this update.
        """
        print(f"Die Methode Update wird aufgerufen")

        if clock == self.env.t_start:
            self.storage_df['Storage Level [kg]'] = self.capacity * self.soc_min

        # Calculate the net inflow to the storage
        net_inflow = inflow - outflow

        # Update the current level, ensuring it stays within capacity
        new_level = self.current_level + net_inflow
        print (f"current level H2 Storage beträgt ")

        if new_level > self.capacity:
            inflow = self.capacity - self.current_level  # Adjust inflow to prevent overflow
            new_level = self.capacity
        elif new_level < 0:
            outflow = self.current_level  # Adjust outflow to prevent underflow
            new_level = 0

        # Update the storage level
        self.current_level = new_level

        # Log data for the current step

        self.storage_df['H2 Inflow [kg]'] = inflow
        self.storage_df['H2 Outflow [kg]'] = outflow
        self.storage_df['Storage Level [kg]'] = self.current_level

        return inflow, outflow
    '''


    def get_storage_level(self, clock):
        """
        Retrieve the current storage level.

        :return: Current storage level in kg.
        """


        return
