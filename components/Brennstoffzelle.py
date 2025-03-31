import pandas as pd
import datetime as dt


class FuelCell:
    """
    Class to represent a Fuel Cell in the Miguel simulation.
    This class simulates the energy production and hydrogen consumption of a fuel cell.
    """

    def __init__(self, env, max_power: float, efficiency: float):
        """
        Initialize the Fuel Cell.

        :param env: Environment object from Miguel.
        :param max_power: Maximum output power of the fuel cell (in kW).
        :param efficiency: Efficiency of the fuel cell (fraction, e.g., 0.8 for 80% efficiency).
        """
        self.name = f"FuelCell_{len(env.h2_components) + 1}"
        self.env = env  # Environment object
        self.max_power = max_power  # Maximum power output in kW
        self.efficiency = efficiency  # Efficiency of the fuel cell

        # DataFrame to store simulation data
        self.df_fc = pd.DataFrame(index=self.env.time, columns=['Power Output [W]', 'H2 Consumed [kg]'])


        self.df_fc.fillna(0, inplace=True)

    def fc_operate (self, clock: dt.datetime, hydrogen_used: float):
        """
        Update the fuel cell for a single simulation step.

        :param hydrogen_available: The amount of hydrogen available for the fuel cell (in kg).

        """

        # Calculate maximum power based on available hydrogen
        max_power_produced = (hydrogen_used * 33.33 *1000* self.efficiency)/ 0.25

        # Determine actual power output
        power_output = min(self.max_power, max_power_produced)

        # Calculate hydrogen consumption for this step
        hydrogen_consumed = (power_output * 0.25 ) / (33.33 * 1000 * self.efficiency)

        # Store results in DataFrame
        current_time = self.env.time[self.env.i_step]
        self.df_fc.at[clock, 'Power Output [W]'] = power_output
        self.df_fc.at[clock , 'H2 Consumed [kg]'] = hydrogen_consumed


        return power_output, hydrogen_consumed

