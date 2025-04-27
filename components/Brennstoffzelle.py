import pandas as pd
import datetime as dt



class FuelCell:
    """
    Class to represent a Fuel Cell in the Miguel simulation.
    This class simulates the energy production and hydrogen consumption of a fuel cell.
    """

    def __init__(self, env,
                 max_power: float,
                 efficiency: float,
                 co2_init_per_kw: float = 24.2,
                 c_invest: float = None,
                 c_invest_n: float = 2500,  #Euro/kW
                 c_var_n: float = 0,
                 c_op_main_n: float = 0,
                 c_op_main: float = None,
                 lifetime: float= None #Hours
                 ):
        """
       Initialize the Fuel Cell including economic and emission parameters.

    :param env: Simulation environment
    :param max_power: Max output power [kW]
    :param efficiency: Efficiency (0–1)
    :param co2_init_per_kw: Initial CO2 [kg/kW]
    :param invest_cost: CAPEX [EUR]
    :param opex_annual: Annual OPEX [EUR/year]
    :param var_cost: Variable cost per kWh [EUR/kWh]
    :param co2_opex: CO2 emission during operation [g/kWh]
        """
        self.name = f"FuelCell_{len(env.fuel_cell) + 1}"
        self.env = env  # Environment object
        self.max_power = max_power  # Maximum power output in kW
        self.efficiency = efficiency  # Efficiency of the fuel cell
        self.lifetime= lifetime
        self.operating_hours = 0.0  # Betriebsstunden-Tracker

        #economic and environment Data
        self.co2_init = co2_init_per_kw * (self.max_power/1000)  # [kg]
        self.invest_cost = c_invest # [US$]
        #variable Cost
        self.c_var_n = c_var_n  # US$/kWh
        #Operation Cost
        self.c_op_main_n = c_op_main_n
        if c_op_main is None:
            self.c_op_main = self.c_op_main_n * self.max_power/ 1000
        else:
            self.c_op_main = c_op_main
        if c_invest is None:
           self.c_invest = c_invest_n * self.max_power / 1000
        else:
            self.c_invest = c_invest

        # DataFrame to store simulation data
        self.df_fc = pd.DataFrame(index=self.env.time, columns=['Power Output [W]', 'H2 Consumed [kg]'])


        self.df_fc.fillna(0, inplace=True)

    def fc_operate (self, clock: dt.datetime, hydrogen_used: float):
        """
        Update the fuel cell for a single simulation step.

        :param hydrogen_available: The amount of hydrogen available for the fuel cell (in kg).

        """
        time_step = self.env.i_step / 60
        self.operating_hours += time_step

        # Calculate maximum power based on available hydrogen
        max_power_produced = (hydrogen_used * 33.33 *1000* self.efficiency)/ time_step

        # Determine actual power output
        power_output = min(self.max_power, max_power_produced)

        # Calculate hydrogen consumption for this step
        hydrogen_consumed = (power_output * time_step) / (33.33 * 1000 * self.efficiency)

        # Store results in DataFrame
        current_time = self.env.time[self.env.i_step]
        self.df_fc.at[clock, 'Power Output [W]'] = power_output
        self.df_fc.at[clock , 'H2 Consumed [kg]'] = hydrogen_consumed


        return power_output, hydrogen_consumed


    def replacement_cost(self):
        """
        Calculate energy storage replacement cost
        :return: dict
            replacement years + cost in US$
        """
        c_invest_replacement = {}
        co2_replacement = {}

        replacements = int (self.operating_hours/ self.lifetime)
        interval = self.env.lifetime / replacements
        for year in range(int(interval), int(replacements*interval)-1, int(interval)):
            c_invest_replacement[year] = (self.c_invest_n * self.max_power) / ((1 + self.env.d_rate) ** year)
            co2_replacement[year] = (self.co2_init  ) / ((1 + self.env.d_rate) ** year)

        return c_invest_replacement, co2_replacement


