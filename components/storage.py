import datetime as dt
import numpy as np
import pandas as pd

# TODO: Add Bleach-Acid, LiIon and Redox-Flow parameters (soc-boarders, efficiency, specific cost and co2 emissions)


class Storage:
    """
    Class to represent Energy Storages with a simplified Storage model
    """

    def __init__(self,
                 env,
                 name: str = None,
                 storage_type: str = 'Default',
                 p_n: float = None,
                 c: float = None,
                 soc: float = 0,
                 soc_max: float = 0.95,
                 soc_min: float = 0.1,
                 n_charge: float = 0.8,
                 n_discharge: float = 0.8,
                 lifetime: int = 10,
                 c_invest_n: float =550,
                 c_op_main_n: float = 10,
                 c_var_n: float = 0,
                 co2_init: float = 103,
                 c_invest: float = None,
                 c_op_main: float = None):
        """
        :param env: environment.Environment
            storage Environment
        :param name: str
            storage name
        :param p_n: float
            nominal power [W]
        :param c: float
            nominal capacity [W]
        :param soc: float
            initial state of charge (between 0-1)
        :param soc_max: float
            maximum state of charge
        :param soc_min: float
            minimum state of charge
        :param n_charge: float
            charging efficiency
        :param n_discharge: float
            discharging efficiency
        :param lifetime: int
            calendrical lifetime [a]
        :param c_invest_n: float
            specific investment cost [US$/kWh]
        :param c_op_main_n: float
            operation and maintenance cost [US$/kWh/a]
        :param c_var_n: float
            variable cost [US$/kWh]
        :param co2_init: float
            initial CO2-emissions during production [US$/kW]
        """
        self.env = env
        self.name = name
        self.storage_type = storage_type
        self.p_n = p_n  # W
        self.c = c  # Wh
        self.soc = soc
        self.soc_max = soc_max
        self.soc_min = soc_min
        if self.storage_type == 'Default':
            self.n_charge = n_charge
            self.n_discharge = n_discharge
        # Economical and ecological parameters
        self.c_invest_n = c_invest_n  # US$/kWh
        self.c_op_main_n = c_op_main_n  # US$/kWh
        self.c_var_n = c_var_n  # US$/kWh
        self.co2_init = co2_init * self.c / 1000 # kg/kWh
        if c_invest is None:
            self.c_invest = self.c_invest_n * self.c / 1000
        else:
            self.c_invest = c_invest
        if c_op_main is None:
            self.c_op_main = self.c_op_main_n * self.c / 1000
        else:
            self.c_op_main = c_op_main
        self.lifetime = lifetime  # a
        self.replacements = self.env.lifetime / self.lifetime - 1
        self.replacement_parameters = self.calc_replacements()
        self.replacement_cost = sum(self.replacement_parameters[0].values())
        self.replacement_co2 = sum(self.replacement_parameters[1].values())

        self.df = pd.DataFrame(columns=['P [W]', 'Q [Wh]', 'SOC'],
                               dtype='float64',
                               index=self.env.time)
        self.set_initial_values()

        # Dict with technical data
        self.technical_data = {'Component': 'Energy Storage',
                               'Name': self.name,
                               'Nominal Power [kW]': round(self.p_n / 1000, 3),
                               'Capacity [kWh]': self.c,
                               f'Specific investment cost [{self.env.currency}/kWh]': int(self.c_invest_n),
                               f'Investment cost [{self.env.currency}]': int(self.c_invest_n * self.p_n / 1000),
                               f'Specific operation maintenance cost [{self.env.currency}/kWh]': int(self.c_op_main_n),
                               f'Operation maintenance cost [{self.env.currency}/a]': int(self.c_op_main_n * self.c / 1000)}

    def set_initial_values(self):
        """
        Set initial values for ES
        :return: None
        """
        initial_time = self.df.index[0]
        self.df.at[initial_time, 'SOC'] = self.soc
        self.df.at[initial_time, 'Q [Wh]'] = self.c * self.df.at[initial_time, 'SOC']
        self.df['P [W]'] = 0

    def charge(self, clock: dt.datetime, power: float):
        """
        :param clock: dt.datetime
            time stamp
        :param power: float
            charging power
        :return: None
        """

        t_step = self.env.i_step
        if clock == self.env.t_start:
            return 0
        # Check charging power
        if power <= self.p_n:
            power = power
        else:
            power = self.p_n
        # Calculate charging energy
        q_charge = power * self.n_charge * (t_step / 60)
        if self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]'] + q_charge < self.c * self.soc_max:
            self.df.at[clock, 'P [W]'] = power
            self.df.at[clock, 'Q [Wh]'] = self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]'] + q_charge
            self.df.at[clock, 'SOC'] = self.df.at[clock, 'Q [Wh]'] / self.c

            return power
        else:
            # Calculate remaining energy to charge storage
            self.q_remain = (self.c * self.soc_max) - self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]']
            power = (60 * self.q_remain) / (t_step * self.n_charge)
            if power == 0:
                self.df.at[clock, 'P [W]'] = 0
                self.df.at[clock, 'Q [Wh]'] = self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]']
                self.df.at[clock, 'SOC'] = self.soc_max

                return 0
            else:
                self.df.at[clock, 'P [W]'] = power
                self.df.at[clock, 'Q [Wh]'] = self.df.at[
                                                  clock - dt.timedelta(minutes=self.env.i_step), 'Q [Wh]'] +\
                                              self.q_remain
                self.df.at[clock, 'SOC'] = self.df.at[clock, 'Q [Wh]'] / self.c


                return power

    def constant_values(self, clock):
        if clock != self.env.t_start:
            self.df.at[clock, 'P [W]'] = self.df.at[clock - self.env.t_step, 'P [W]']
            self.df.at[clock, 'Q [Wh]'] = self.df.at[clock - self.env.t_step, 'Q [Wh]']
            self.df.at[clock, 'SOC'] = self.df.at[clock - self.env.t_step, 'SOC']

    def discharge(self, clock: dt.datetime, power: float):
        """
        Discharge Storage
        :param clock: dt.datetime
            time stamp
        :param power: float
            discharge power
        :return: power
        """
        t_step = self.env.i_step

        if clock == self.env.t_start:
            return 0
        # Check charging power
        if power <= self.p_n:
            power = -power
        else:
            power = -self.p_n
        q_discharge = power * self.n_discharge * (t_step / 60)
        # Check if SOC after discharge > soc_min
        if self.soc_min < self.df.at[clock, 'SOC'] + (q_discharge/self.c):
            self.df.at[clock, 'P [W]'] = power
            self.df.at[clock, 'Q [Wh]'] = self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]'] + q_discharge

            self.df.at[clock, 'SOC'] = self.df.at[clock, 'Q [Wh]'] / self.c
            return power
        else:
            # Calculate remaining energy to discharge storage
            q_remain = self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]'] - (self.c * self.soc_min)
            power = -(60 * q_remain) / (t_step * self.n_charge)
            if power == 0:
                self.df.at[clock, 'P [W]'] = 0
                self.df.at[clock, 'Q [Wh]'] = self.df.at[clock - dt.timedelta(minutes=t_step), 'Q [Wh]']
                self.df.at[clock, 'SOC'] = self.soc_min
                return 0
            else:
                self.df.at[clock, 'P [W]'] = power
                self.df.at[clock, 'Q [Wh]'] = self.df.at[clock - dt.timedelta(minutes=self.env.i_step), 'Q [Wh]'] - q_remain
                self.df.at[clock, 'SOC'] = self.df.at[clock, 'Q [Wh]'] / self.c

            return power
        print(" storage nach entladen", self.df.at[clock, 'Q [Wh]'])


    def calc_replacements(self):
        """
        Calculate energy storage replacement cost
        :return: dict
            replacement years + cost in US$
        """
        c_invest_replacement = {}
        co2_replacement = {}
        replacements = self.env.lifetime / self.lifetime
        interval = self.env.lifetime / replacements
        for year in range(int(interval), int(replacements*interval)-1, int(interval)):
            c_invest_replacement[year] = (self.c_invest_n * self.c/1000) / ((1 + self.env.d_rate) ** year)
            co2_replacement[year] = (self.co2_init  ) / ((1 + self.env.d_rate) ** year)

        return c_invest_replacement, co2_replacement





