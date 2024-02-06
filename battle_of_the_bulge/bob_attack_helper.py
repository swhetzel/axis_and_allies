# -*- coding: utf-8 -*-
"""
Created on Wed Jan 31 14:54:44 2024

@author: Stephen Whetzel
"""
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
import os
from bob_attack_simulator import BoBAttackSimulator

class BoBAttackHelper:
    """
    Utilizes the base object, BoBAttackSimulator, to perform a number of
    helpful tasks such as:

        1. calculating how the probability of evacuation
           and the expectation of the total power destroyed in a hex increases with
           the available offensive power.
        2. calculating the probability of evacuation and expected destroyed
           defending power when a single hex is attacked multiple times.

    Is able to output and save helpful graphics relating to these outputs.

    This object extends the capability of the BoBAttackSimulator by using the
    output of the simulator to iterate through multiple hypothetical attacks
    on a single defending hex either independently to explore the effects of
    increasing power on our expected results, or consecutively to explore the
    effect of launching multiple attacks on the defending hex.

    Parameters
    ----------
    inf : int, default is 1
        The total number of defending infantry units. Stacking limits dictate
        that this number be 6 or less.
    tnk : int
        The total number of defending tank units. Stacking limits dictate that
        this number be 6 or less.
    art : int
        The total number of defending artillery units. Stacking limits dictate
        that this number be 3 or less.
    supply : int
        The total number of supplies in the defending hex. No stacking limits.
    truck : int
        The total number of trucks in the defending hex. No stacking limits.
    can_retreat : bool, default is True
        True if defending units have a legal avenue of retreat (i.e. into a
        hexagon that is on their side of the battle line and is not in the
        enemy's zone of control). When False, units cannot retreat and they
        will be marked as destroyed if assigned 1 or more hits.
        NOTE: as of now there is no way to indicate that only infantry can
        retreat (i.e. the only legal avenue of retreat is over a river).
        Assumes that the option to retreat applies to all military units.
    save_path : str
        Path that output graphics will be saved to.

    Key Attributes
    --------------
    destroy_data : pd.DataFrame
        Dataframe detailing the expected amount of defending power destroyed
        given the units in the defending hex and all possible attacking power
        from 1 to 12 inclusive
    evacuate_data : pd.DataFrame
        Dataframe detailing the probability of the defending hex evacuating
        given the units in the defending hex and all possible attacking power
        from 1 to 12 inclusive

    Key Methods:
    ------------
    simulate_through_all_power: Given the provided number of unit types
        outputs a dataframe showing the probability of hex evacuation and
        expected number of destroyed defending power given all possible
        offensive firepower from 1 to 12 inclusive.
    simulate_multi_attack : Outputs the probability of a hex evacuation and
        the expected total power destroyed for the specified defending hex
        given multiple consecutive attacks at specified powers.
    """

    def __init__(self, inf=1, tnk=0, art=0, supply=0, truck=0, can_retreat=True, save_path=None):
        # Input attributes
        self.inf = inf
        self.tnk = tnk
        self.art = art
        self.can_retreat = can_retreat
        self.supply_num = supply
        self.truck_num = truck
        self.save_path = save_path

        self.destroy_data = pd.DataFrame()
        self.evacuate_data = pd.DataFrame()
        self.multi_attack_prob_evac = None

        self.sim = BoBAttackSimulator()
        self._reset_sim()

    def simulate_through_all_power(self, plot=True):
        """
        Given the provided number of unit types outputs a dataframe showing
        the probability of hex evacuation and expected number of destroyed
        defending power given all possible offensive firepower from 1 to 12
        inclusive.
        """
        self.destroy_data = pd.DataFrame()
        for retreat in [True,False]:
            p_evacuates = []
            retreats = []
            exp_destroys = []
            for power in range(1,13):
                self.sim.power = power
                self.sim.can_retreat = retreat
                self.sim.process()

                p_evacuates.append(self.sim.prob_evacuate)
                exp_destroys.append(self.sim.exp_power_destroyed)
                retreats.append(retreat)

            if retreat:
                self.evacuate_data = pd.DataFrame({
                        'power':range(1,13),
                        'p_evacuate':p_evacuates
                    })

            self.destroy_data = pd.concat([
                self.destroy_data,
                pd.DataFrame({
                    'power':range(1,13),
                    'exp_power_destroyed':exp_destroys,
                    'retreat':retreats
                })
            ]).reset_index(drop=True)

        if plot:
            self._plot_evac_fig()
            self._plot_destroy_fig()

    def _reset_sim(self):
        self.sim = BoBAttackSimulator(
            inf=self.inf,
            tnk=self.tnk,
            art=self.art,
            supply=self.supply_num,
            truck=self.truck_num,
            can_retreat=self.can_retreat
            )

    def __reset_figure_size(self):
        plt.figure()
        sns.set_theme(rc={'figure.figsize':(12,6)}, style='whitegrid')
        plt.figure()

    def _plot_evac_fig(self):
        """
        Plots and saves the probability of evacuation figure.
        """
        self.__reset_figure_size()
        evac_fig = sns.lineplot(
            data=self.evacuate_data,
            x='power',
            y='p_evacuate'
            )
        evac_fig.set(title="Power v Probability of Total Evacuation")
        self.__save_figure(evac_fig, "evac_plot")

    def _plot_destroy_fig(self):
        """
        Plots and saves the expected destroyed power figure.
        """
        self.__reset_figure_size()
        destroy_fig = sns.lineplot(
            data=self.destroy_data,
            x='power',
            y='exp_power_destroyed',
            hue='retreat'
            )
        destroy_fig.set(title="Power v Expected Power Destroyed")
        self.__save_figure(destroy_fig, "power_destroy")

    def __save_figure(self, fig, name):
        if self.save_path is not None:
            save_path = os.path.join([
                self.save_path,
                f"{name}.png"
                ])
            fig.savefig(save_path)

    def simulate_multi_attack(self, attack_powers):
        """
        Iteratively simulates all possible outcomes that could occur given the
        x attacks specified by the `attack_powers` list. Calculates the total
        probability of hex evacuation given the attack and saves it in the
        `multi_attack_prob_evac` attribute.

        Parameters
        ----------
        attack_powers : list
            List of integers providing the attacking power for consecutive
            attacks in the order in which the attacks will be resolved.

        """
        assert type(attack_powers) == list, "Attack powers must be type list"
        assert len(attack_powers) <= 6, "Cannot specify more than 6 attacks - impossible to do legally"
        for attack in attack_powers:
            assert type(attack) == int, "All attack powers specified must be int type"
            assert attack <= 12, "All attack powers specified must be 12 or less"

        units_left = pd.DataFrame({
            'attack_num':0,
            'inf_left':self.inf,
            'tnk_left':self.tnk,
            'art_left':self.art,
            'supply_left':self.supply_num,
            'truck_left':self.truck_num,
            'outcome_pred':1,
            'evacuate':0
        }, index=[0])

        outcome_df = units_left.copy()
        evac_df = pd.DataFrame()

        for attack_num, power in enumerate(attack_powers):
            for outcome_i in outcome_df[outcome_df.attack_num == attack_num].index:
                outcome = outcome_df.loc[outcome_i]
                inf = int(outcome.inf_left)
                tnk = int(outcome.tnk_left)
                art = int(outcome.art_left)
                supply = int(outcome.supply_left)
                truck = int(outcome.truck_left)
                prior_pred = outcome.outcome_pred

                sim = BoBAttackSimulator(
                    power=attack_powers[attack_num],
                    inf=inf,
                    tnk=tnk,
                    art=art,
                    supply=supply,
                    truck=truck
                    )
                sim.process()

                units_left = sim.units_left_dist.copy()
                units_left.outcome_pred = units_left.outcome_pred*(prior_pred)

                # Update evac and outcome dfs
                evac_df = pd.concat([
                    evac_df,
                    units_left[units_left.evacuate == 1].assign(attack_num = attack_num+1)
                ]).reset_index(drop=True)
                outcome_df = pd.concat([
                    outcome_df,
                    units_left[units_left.evacuate != 1].assign(attack_num = attack_num+1)
                ]).reset_index(drop=True)

        self.multi_attack_prob_evac = evac_df.outcome_pred.sum()






