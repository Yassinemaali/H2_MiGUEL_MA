import math
import sys
import numpy as np
import pandas as pd
from lcoe.lcoe import lcoe as py_lcoe
from environment import Environment
from operation import Operator
from components.grid import Grid
from components.pv import PV
from components.windturbine import WindTurbine
from components.storage import Storage
from components.H2_Storage import H2Storage
from components.Electrolyser import Electrolyser
from components.Brennstoffzelle import FuelCell

class Evaluation:
    """
    Class to evaluate the energy system
    """

    def __init__(self,
                 env: Environment = None,
                 operator: Operator = None):
        self.env = env
        self.op = operator
        # Evaluation df
        self.evaluation_df = self.build_evaluation_df()
        # System  parameters
        self.energy_consumption_annual = self.calc_energy_consumption_annual()  # kWh
        self.peak_load = self.calc_peak_load()  # kW
        if self.env.grid_connection:
            self.grid_cost_comparison_annual = self.calc_grid_energy_annual_cost()
            self.grid_cost_comparison_lifetime = self.calc_lifetime_value(initial_value=0,
                                                                          annual_value=self.grid_cost_comparison_annual)
        else:
            self.grid_cost_comparison_annual = None
            self.grid_cost_comparison_lifetime = None

        # Components evaluation parameters
        self.pv_energy_supply = {}
        self.wt_energy_supply = {}
        self.H2_energy_supply = {}
        self.grid_energy_supply = {}
        self.storage_energy_supply = {}
        #Berechnung der Speicherenergie (inkl. H2)
        self.calc_storage_energy_supply()

        for component in self.env.supply_components:
            self.calc_component_energy_supply(component=component)
            self.calc_co2_emissions(component=component)
            self.calc_cost(component=component)
        #Bewertung der Speicher (Batterie & H2-System)
        for es in self.env.storage:
            self.calc_co2_emissions(component=es)
            self.calc_cost(component=es)
        for fc in self.env.fuel_cell:
            self.calc_co2_emissions(component=fc)
            self.calc_cost(component=fc)
        for el in self.env.electrolyser:
            self.calc_co2_emissions(component=el)
            self.calc_cost(component=el)
        for hstr in self.env.H2Storage:
            self.calc_co2_emissions(component=hstr)
            self.calc_cost(component=hstr)
        self.calc_lifetime_energy_supply()
        self.calc_system_values()
        self.calc_lcoe()
        self.evaluation_df.to_csv(sys.path[1] + '/export/system_evaluation.csv',
                                  sep=self.env.csv_sep,
                                  decimal=self.env.csv_decimal)

    def build_evaluation_df(self):
        """
        Create dataframe for system evaluation
        :return: pd.DataFrame
        """
        col = ['Annual energy supply [kWh/a]', 'Lifetime energy supply [kWh]', f'Lifetime cost [US$]',
               f'Investment cost [{self.env.currency}]', f'Annual cost [US$/a]',
               f'LCOE [{self.env.currency}/kWh]', 'Lifetime CO2 emissions [t]', 'Initial CO2 emissions [t]',
               'Annual CO2 emissions [t/a]']
        evaluation_df = pd.DataFrame(columns=col)
        for supply_comp in self.env.supply_components:
            evaluation_df.loc[supply_comp.name] = np.nan
        for es in self.env.storage:
                evaluation_df.loc[es.name] = np.nan
                evaluation_df.loc[es.name + '_charge'] = np.nan
                evaluation_df.loc[es.name + '_discharge'] = np.nan

        for el in self.env.electrolyser:
            evaluation_df.loc[el.name] = np.nan
            evaluation_df.loc[el.name + '_Power'] = np.nan
        for hstr  in self.env.H2Storage:
            evaluation_df.loc[hstr.name] = np.nan
            evaluation_df.loc[hstr.name + '_Power'] = np.nan
        for fc in self.env.fuel_cell:
            evaluation_df.loc[fc.name] = np.nan
            evaluation_df.loc[fc.name + '_Power'] = np.nan

        evaluation_df.loc['System'] = np.nan

        return evaluation_df

    def calc_energy_consumption_annual(self):
        """
        Calculate annual energy consumption
        :return: float
            energy_consumption [kWh]
        """
        energy_consumption = self.env.df['P_Res [W]'].sum() * self.env.i_step / 60 / 1000

        self.evaluation_df.loc['System', 'Annual energy supply [kWh/a]'] = int(energy_consumption)

        return energy_consumption

    def calc_grid_energy_annual_cost(self):
        """
        Calculate grid cost to meet annual consumption
        :return: float
        """
        cost = self.energy_consumption_annual * self.env.electricity_price  # US$

        return cost


    def calc_lifetime_energy_supply(self):
        """
        Calculate lifetime energy supply
        :return:
        """
        for row in self.evaluation_df.index:
            annual_energy_supply = self.evaluation_df.loc[row, 'Annual energy supply [kWh/a]']
            self.evaluation_df.loc[row, 'Lifetime energy supply [kWh]'] \
                = int(self.calc_lifetime_value(initial_value=0,
                                               annual_value=annual_energy_supply))

    def calc_peak_load(self):
        """
        Calculate peak load
        :return: float
            peak load [kW]
        """
        peak_load = self.env.df['P_Res [W]'].max() / 1000

        return peak_load

    def calc_component_energy_supply(self,
                                     component: PV or WindTurbine or Grid):
        """
        Calculate annual energy supply of energy supply components
        :param component:
        :return: None
        """
        col = f'{component.name} [W]'
        energy_supply = self.op.df[col].sum() * self.env.i_step / 60 / 1000
        if isinstance(component, PV):
            if len(self.env.storage) == 0 and len (self.env.h2_components) == 0:
                charge = 0
            else:
                charge = self.op.df[f'{component.name}_charge [W]'].sum() * self.env.i_step / 60 / 1000

            self.pv_energy_supply[component.name] = energy_supply + charge

        elif isinstance(component, WindTurbine):
            if len(self.env.storage) == 0 and len(self.env.h2_components) == 0:
               charge = 0
            else:
                 charge = self.op.df[f'{component.name}_charge [W]'].sum() * self.env.i_step / 60 / 1000
                 if charge == 0:
                    charge= self.op.df.get('FuelCell_Discharge [W]', pd.Series(0)).sum() * self.env.i_step / 60 / 1000

            self.wt_energy_supply[component.name] = energy_supply + charge

        elif isinstance(component, Grid):
            charge = 0
            self.grid_energy_supply[component.name] = energy_supply

            return
        self.evaluation_df.loc[component.name, 'Annual energy supply [kWh/a]'] = int(energy_supply + charge)

    def calc_storage_energy_supply(self):
        """
        Calculate annual energy supply of energy storage
        :return: None
        """
        for es in self.env.storage:
            col = es.name + ' [W]'
            es_charge = int(sum(np.where(self.op.df[col] > 0,
                                         self.op.df[col],
                                         0).tolist()) * self.env.i_step / 60 / 1000)
            es_discharge = int(sum(np.where(self.op.df[col] < 0,
                                            self.op.df[col],
                                            0).tolist()) * self.env.i_step / 60 / 1000)
            self.evaluation_df.loc[es.name, 'Annual energy supply [kWh/a]'] = -es_discharge
            self.storage_energy_supply[f'{es.name}_charge'] = es_charge
            self.storage_energy_supply[f'{es.name}_discharge'] = es_discharge
            self.evaluation_df.loc[f'{es.name}_discharge', 'Annual energy supply [kWh/a]'] = -es_discharge
            self.evaluation_df.loc[f'{es.name}_charge', 'Annual energy supply [kWh/a]'] = -es_charge

    def calc_H2_energy_supply(self):

        for fc in self.env.fuel_cell:
            col = fc.name + ' [W]'
            fc_power = int(sum(np.where(self.op.df[col] > 0,
                                         self.op.df[col],
                                         0).tolist()) * self.env.i_step / 60 / 1000)
            self.H2_energy_supply[f'{fc.name}_charge'] = fc_power
            self.evaluation_df.loc[f'{fc.name}_charge', 'Annual energy supply [kWh/a]'] = -fc_power


    def calc_co2_emissions(self, component):
        """
        Calculate total CO2 emissions of component
        :param component:
        :return:
        """
        # Initial CO2 emissions
        co2_init = self.calc_co2_initial(component=component)
        # Operating CO2 emissions
        co2_annual = self.calc_co2_annual_operation(component=component)
        # Lifetime CO2 emissions
        co2_lifetime = self.calc_lifetime_value(initial_value=co2_init,
                                                annual_value=co2_annual)
        self.evaluation_df.loc[component.name, 'Lifetime CO2 emissions [t]'] = round(co2_lifetime, 3)

    def calc_co2_initial(self, component):
        """
        Calculate initial CO2 emissions
        :param component: object
        :return: None
        """
        if isinstance(component, Storage):
            co2_init = (component.co2_init + component.replacement_co2) / 1000
        elif isinstance(component, Grid):
            co2_init = 0
        else:
            co2_init = component.co2_init / 1000

        self.evaluation_df.loc[component.name, 'Initial CO2 emissions [t]'] = round(co2_init, 3)

        return co2_init

    
    def calc_co2_annual_operation(self,
                                  component):
        """
        Calculate annual CO2 emissions emitted during operation
        :param component: object
        :return: float
        """
        #if isinstance(component,Electrolyser):
            #co2_annual = self.evaluation_df.loc[
                             #component.name, 'Annual energy supply [kWh/a]'] * self.env.co2_diesel / 1000
        if isinstance(component, Grid):
            co2_annual = self.evaluation_df.loc[
                             component.name, 'Annual energy supply [kWh/a]'] * self.env.co2_grid / 1000
        else:
            co2_annual = 0
        self.evaluation_df.loc[component.name, 'Annual CO2 emissions [t/a]'] = round(co2_annual, 3)

        return co2_annual


    def calc_cost(self, component: object):
        """
        :param component:
        :return: None
        """
        # Investment cost
        investment_cost = self.calc_investment_cost(component=component)
        # Annual cost
        annual_cost = self.calc_annual_cost(component=component)
        # Lifetime cost
        lifetime_cost = self.calc_lifetime_value(initial_value=investment_cost,
                                                 annual_value=annual_cost)

        self.evaluation_df.loc[component.name, f'Lifetime cost [US$]'] = int(lifetime_cost)

    def calc_investment_cost(self,
                             component: object):
        """
        Calculate component investment cost
        :param component: object
            energy system component
        :return: float
            component investment cost
        """
        if isinstance(component, Grid):
            investment_cost = 0
        elif isinstance(component, Storage):
            investment_cost = component.c_invest + component.replacement_cost
        else:
            investment_cost = component.c_invest

        self.evaluation_df.loc[component.name, f'Investment cost [US$]'] = int(investment_cost)

        return investment_cost

    def calc_annual_cost(self,
                         component: object):
        """
        Calculate component annual cost
        :param component: object
            energy system component
        :return: float
            annual_cost
        """
        annual_output = self.evaluation_df.loc[component.name, 'Annual energy supply [kWh/a]']
        co2 = self.evaluation_df.loc[component.name, 'Annual CO2 emissions [t/a]']
        co2_cost = co2 * self.env.avg_co2_price
        if isinstance(component, Storage ):
            additional_variable_cost = annual_output * component.c_var_n
            annual_cost = component.c_op_main + co2_cost + additional_variable_cost

        elif isinstance(component, Grid):
            electricity_cost = self.evaluation_df.loc[
                                   component.name, 'Annual energy supply [kWh/a]'] * self.env.electricity_price
            additional_variable_cost = annual_output * component.c_var_n
            annual_cost = electricity_cost + co2_cost + additional_variable_cost
        elif isinstance(component, Electrolyser):
            additional_variable_cost = annual_output * component.c_var_n
            annual_cost = component.c_op_main + co2_cost + additional_variable_cost
        elif isinstance(component, FuelCell):
            h2_consumed = self.op.df.get(f'{component.name}: H2 Consumption [kg]', pd.Series(0)).sum()
            h2_cost = h2_consumed * self.env.h2_price
            annual_cost = h2_cost + component.c_op_main + co2_cost

        elif isinstance (component, H2Storage):
            additional_variable_cost = annual_output * component.c_var_n
            annual_cost = component.c_op_main + co2_cost + additional_variable_cost

        else:
            if self.env.grid_connection:
                if self.env.feed_in:
                    annual_revenues = self.op.df[f'{component.name} Feed in [US$]'].sum()
                else:
                    annual_revenues = 0
            else:
                annual_revenues = 0
            additional_variable_cost = annual_output * component.c_var_n
            annual_cost = component.c_op_main + co2_cost - annual_revenues + additional_variable_cost

        self.evaluation_df.loc[component.name, f'Annual cost [US$/a]'] = int(annual_cost)

        return annual_cost
    def calc_system_values(self):
        columns = [f'Lifetime cost [US$]',
                   f'Investment cost [US$]', f'Annual cost [US$/a]',
                   'Lifetime CO2 emissions [t]', 'Initial CO2 emissions [t]', 'Annual CO2 emissions [t/a]']
        for col in columns:
            self.evaluation_df.loc['System', col] = self.evaluation_df[col].sum()

    def calc_lcoe(self):
        """
        Calculate LCOE with given parameters
        :return: float
            LCOE
        """
        df = self.evaluation_df
        rows = [x for x in df.index if "charge" not in x]
        for row in rows:
            annual_energy_supply = df.loc[row, 'Annual energy supply [kWh/a]']
            annual_cost = df.loc[row, f'Annual cost [US$/a]']
            investment_cost = df.loc[row, f'Investment cost [US$]']
            lcoe = py_lcoe(annual_output=annual_energy_supply,
                           annual_operating_cost=annual_cost,
                           capital_cost=investment_cost,
                           discount_rate=self.env.d_rate,
                           lifetime=self.env.lifetime)
            df.loc[row, f'LCOE [US$/kWh]'] = round(lcoe, 2)

    def calc_lifetime_value(self,
                            initial_value: float,
                            annual_value: float):
        """
        Calculate lifetime CO2 emissions
        :param initial_value: float
        :param annual_value: float
        :return: float
        """
        lifetime_lifetime_value = 0
        for i in range(self.env.lifetime):
            if i == 0:
                lifetime_lifetime_value += (initial_value + annual_value) / ((1 + self.env.d_rate) ** i)
            else:
                lifetime_lifetime_value += annual_value / ((1 + self.env.d_rate) ** i)

        lifetime_lifetime_value = int(lifetime_lifetime_value)


        return lifetime_lifetime_value
