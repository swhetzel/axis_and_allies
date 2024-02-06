# -*- coding: utf-8 -*-
"""
Created on Thu Jan 25 16:55:54 2024

@author: Stephen Whetzel
"""
import pandas as pd
import numpy as np
from copy import copy
from scipy.special import factorial

class BoBAttackSimulator:
    """
    Simulator for Axis and Allies: Battle of the Bulge combat mechanic. One
    instance simulates a single attack upon a single defending hex and stores
    as attributes helpful information such as the total expected defending
    power destroyed in the attack, the probability of clearing the defending
    hex via the attack, and a distribution of of all possible posterior states
    for the defending hex.

    Parameters
    ----------
    power : int, default is 1
        The total attacking power for the battle. Must be between 1 and 12
        inclusive.
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

    Key Attributes
    --------------
    prob_evacuate : float
        The calculated probability of the defending hexagon being evacuated
        given the parameters of the attack.
    exp_power_destroyed : float
        The calculated expected defending power that will be completely
        destroyed rather than remaining in the hex or retreating to an
        adjacent hex.
    outcome_preds : pd.DataFrame
        The raw distribution of all possible unit outcomes given the attack.
        Shows the probabilities of every possible combination of units being
        forced to retreat or being destroyed in the attack.
    unit_destroyed_dist : pd.DataFrame
        The aggregated distribution containing the probabilities of all
        possible combinations of defending units being destroyed.
    total_power_destroyed_dist : pd.DataFrame
        The aggregated distribution containing the probability of all possible
        defending power amounts that could be destroyed.
    power_left_dist : pd.DataFrame
        The aggregated distribution containing the probability of all possible
        numbers of defending power that could be left in the hex following
        the attack.

    Key Methods
    -----------
    process : Processes and populates all the key attributes outlined above.
        If this is not run then all these key attributes will be empty.
    report_key_findings : Prints out simple summary metrics: probability of
        total evacuation following the attack, and the expected amount of
        defending power destroyed by the attack.

    """
    def __init__(self, power=1, inf=1, tnk=0, art=0, supply=0, truck=0, can_retreat=True):

        # Input attributes
        self.power = power
        self.inf = inf
        self.tnk = tnk
        self.art = art
        self.total_defending_units = inf + tnk + art
        self.can_retreat = can_retreat
        self.supply_num = supply
        self.truck_num = truck

        # Generated attributes
        self.def_power = inf + tnk*2 + art*3
        self.supply = supply > 0
        self.truck = truck > 0
        self._create_unit_dict()
        self.hit_slots = sum(self.unit_dict.values())
        self.hit_nums = 6 if self.hit_slots < 7 else 12
        self.hit_slots = sum(self.unit_dict.values())
        self.hit_nums = 6 if self.hit_slots < 7 else 12
        self._verify_attributes()

        # Empty attributes
        self.prob_evacuate = None
        self.exp_power_destroyed = None
        self.hit_slot_dict = {}
        self.hit_probs = pd.DataFrame()
        self.outcome_preds = pd.DataFrame()
        self.unit_destroyed_dist = pd.DataFrame()
        self.total_power_destroyed_dist = pd.DataFrame()

    def process(self):
        """
        Calculates all possible outcomes of the battle and outputs to
        attributes given the initialized attributes. Verifies that all
        attributes adhere to the rules of the game in case they have been
        changed after initialization.
        """
        self._create_unit_dict()
        self._verify_attributes()
        self._get_raw_hit_distr()
        self._calc_unit_hit_slots()
        self._calc_unit_hit_dists()
        self._aggregate_outcomes()

    def report_key_findings(self):
        """
        Prints out simple summary metrics: probability of
        total evacuation following the attack, and the expected amount of
        defending power destroyed by the attack.
        """
        print("EVACUATION PROBABILITY:", round(self.prob_evacuate, 3))
        print("EXPECTED POWER DESTROYED:", round(self.exp_power_destroyed, 3))

    def _verify_attributes(self):
        """
        Verifies that all provided attributes adhere to the rules of the game.
        Includes checking that the offensive power is between 1 and 12
        inclusive, that all defensive units adhere to hex stacking limits
        (no more than 6 infantry, 6 tanks, 3 artillery, or 12 defensive power
         in the defending hex), and that there is at least 1 defending unit.
        """

        assert self.power <= 12, f"Power must be 12 or less. You have input {self.power} offensive power"
        assert self.power > 0, "Must have at least 1 attacking power."
        assert self.inf < 7, f"Infantry number must be 6 or less for stacking limits. You have indicated {self.inf} infantry units"
        assert self.tnk < 7, f"Tank number must 6 or less for stacking limits. You have indicated {self.tnk} tank units"
        assert self.art < 4, f"Artillery number must be 3 or less for stacking limits. You have indicated {self.art} artillery units"
        assert self.def_power < 13, f"Total defending power must be 12 or less. You have indicated {self.def_power} power"
        assert self.inf + self.art + self.tnk > 0, "Cannot attack an unoccupied hex, you have indicated 0 defending units"
        assert self.inf > -1 and self.tnk > -1 and self.art > -1 and self.supply > -1 and self.truck > -1, "All inputs must be 0 or greater"

        for unit in self.unit_dict:
            if unit in ['inf','tnk','art']:
                check_num = self.unit_dict[unit]
            elif unit == 'supply':
                check_num = self.supply
            elif unit == 'truck':
                check_num == self.truck
            assert type(check_num == int), f"All parameters must be of int type. {unit.capitalize()} is not type int."

        assert self.hit_nums in [6,12], f"self.hit_nums must either be 6 or 12. You have set this to {self.hit_nums}"


    def _create_unit_dict(self):
        """
        Updates the unit_dict object which provides a convenient way to access
        the numbers of each unit type that were provided via keyword.
        """
        self.unit_dict = {
            'inf':self.inf,
            'tnk':self.tnk,
            'art':self.art,
            'supply':self.supply,
            'truck':self.truck
        }

    def _get_raw_hit_distr(self):
        """
        Creates the self.hit_probs attribute which contains the distribution
        of rolled hits given the offensive power provided (self.power). Simple
        Binomial distribution using a 50% chance of each die rolling a 6 or
        less for a hit.
        """
        self.hit_probs = pd.DataFrame({
            'hits':range(0,self.power+1),
        })
        self.hit_probs = self.hit_probs.assign(
            permutations = factorial(self.power)/(factorial(self.hit_probs.hits)*factorial(self.power-self.hit_probs.hits))
            )
        self.hit_probs = self.hit_probs.assign(prob_total_hits = self.hit_probs.permutations*(.5**self.power))

    def _calc_unit_hit_slots(self):
        """
        Each hit slot will be assigned at least 1 number that corresponds to
        that slot taking a hit. If there are less than 5 hit slots, or more
        than 6 slots then at least 1 slot will be assigned more than 1 number.
        Here we create an object `self.unit_hit_slots` which keeps track of
        the amount of numbers that can be assigned as hits to each slot. (This
        obviously makes much more sense if you know the rules of the game and
        if you're reading this far and don't know the rules, then maybe you
        need another hobby)
        """
        hit_nums = copy(self.hit_nums)
        self.unit_hit_slots = pd.DataFrame()
        for unit in self.unit_dict:
            self.unit_hit_slots = pd.concat([
                self.unit_hit_slots,
                pd.DataFrame({
                    'unit_type':unit,
                    'unit_num':range(self.unit_dict[unit])
                })
            ]).reset_index(drop=True)

        self.unit_hit_slots = self.unit_hit_slots.assign(unit_hit_slots = 0)

        while hit_nums > len(self.unit_hit_slots):
            hits_to_add = np.min([hit_nums, len(self.unit_hit_slots)])
            hit_nums -= hits_to_add
            add_series = pd.Series(np.full(hits_to_add,1))
            self.unit_hit_slots.unit_hit_slots = self.unit_hit_slots.unit_hit_slots + add_series
        hits_to_add = np.min([hit_nums, len(self.unit_hit_slots)])
        add_series = pd.Series(np.full(hits_to_add,1))
        add_series = pd.concat([add_series, pd.Series(np.full(len(self.unit_hit_slots)-len(add_series),0))]).reset_index(drop=True)
        self.unit_hit_slots.unit_hit_slots = self.unit_hit_slots.unit_hit_slots + add_series
        self.unit_hit_slots = self.unit_hit_slots.assign(unit_name = self.unit_hit_slots.unit_type + '_' + self.unit_hit_slots.unit_num.astype(str))

    def _calc_unit_hit_dists(self):
        """
        Here we calculate the distribution of all possible outcomes from the
        attack. We start with the distribution of all possible hits that could
        be rolled given the attacking power. We then calculate the
        distribution of hits that could be assigned to the first unit given
        all possible amounts of rolled hits. By multiplying the distributions
        together you are left with a distribution of the joint probabilities
        of any number of hits being assigned to the first unit and the number
        of hits that are left available to be assigned to the other units. We
        then repeat this process for all available units and then take 1 as
        the probability that any leftover hits will be assigned to the final
        unit. This delivers the final distribution of the probabilities of all
        possible combinations of hits being assigned to each unit. We then
        apply the relevant rules concerning how many hits will cause a unit
        to retreat or be destroyed to calculate the distribution of all
        possible final states of the defending hexagon.
        """

        # There will be a finite number of distributions that describe the
        # relative likelihood of the number of hits a unit will take given
        # the number of hits available.
        self.hit_slot_dict = {}
        for slots in self.unit_hit_slots.unit_hit_slots.drop_duplicates().sort_values():
            slot_df = pd.DataFrame()
            for hits in range(self.power+1):
                slot_df = pd.concat([
                    slot_df,
                    self.__calc_single_unit_hit_slots(
                        total_available_hits=hits, unit_hit_slots=slots
                        )
                ]).reset_index(drop=True)
            self.hit_slot_dict[slots] = slot_df

        # Process the first unit to get our initial probabilities of unit hits
        # and hits that are left for the other units.
        # Join probabilities of total available hits to initial unit hit distribution
        first_unit_data = copy(self.hit_slot_dict[self.unit_hit_slots.loc[0].unit_hit_slots])
        first_unit_data = pd.merge(
            left=first_unit_data,
            right=self.hit_probs.drop(columns='permutations'),
            how='left',
            left_on='total_available_hits',
            right_on='hits'
        ).drop(columns='hits')
        first_unit_data.unit_hits_pred = first_unit_data.unit_hits_pred*first_unit_data.prob_total_hits

        unit_type = self.unit_hit_slots.loc[0].unit_type

        # Define the columns that define the number of units retreating or
        # destroyed. These will be updated iteratively as we work through all
        # available units.
        unit_outcome_cols = []
        for unit in self.unit_dict:
            retreat_col = f"{unit}_retreat"
            destroy_col = f"{unit}_destroyed"

            # Only combat units can retreat
            if unit in ['inf','tnk','art']:
                first_unit_data.insert(len(first_unit_data.columns), retreat_col, 0)
            first_unit_data.insert(len(first_unit_data.columns), destroy_col, 0)
            unit_outcome_cols.extend([col for col in [retreat_col, destroy_col] if col in first_unit_data.columns])
        if self.can_retreat:
            first_unit_data[f"{unit_type}_retreat"] = (first_unit_data.unit_hits == 1).astype(int)
            first_unit_data[f"{unit_type}_destroyed"] = (first_unit_data.unit_hits > 1).astype(int)
        else:
            first_unit_data[f"{unit_type}_destroyed"] = (first_unit_data.unit_hits > 0).astype(int)

        self.outcome_preds = first_unit_data.groupby(['hits_left']+unit_outcome_cols).unit_hits_pred.sum().reset_index()
        self.outcome_preds = self.outcome_preds.rename({'unit_hits_pred':'outcome_pred'}, axis=1)

        # Update the probabilities of units retreating or being destroyed as
        # we work through all available units.
        for unit_i in range(1,len(self.unit_hit_slots)):
            unit_hit_slots = self.unit_hit_slots.loc[unit_i].unit_hit_slots
            unit_type = self.unit_hit_slots.loc[unit_i].unit_type
            unit_hit_probs = copy(self.hit_slot_dict[unit_hit_slots])

            if unit_i == len(self.unit_hit_slots)-1:
                unit_hit_probs.unit_hits = unit_hit_probs.total_available_hits
                unit_hit_probs.unit_hits_pred = 1
                unit_hit_probs.hits_left = 0
                unit_hit_probs = unit_hit_probs.drop_duplicates()

            # Add new hit cols
            if unit_type in ['inf','tnk','art'] and self.can_retreat:
                new_retreat_col = f"{unit_type}_retreat_new"
                unit_hit_probs[new_retreat_col] = (unit_hit_probs.unit_hits == 1).astype(int)
            new_destroyed_col = f"{unit_type}_destroyed_new"
            if unit_type in ['supply','truck']:
                unit_hit_probs[new_destroyed_col] = unit_hit_probs.unit_hits
            elif unit_type in ['inf','tnk','art']:
                if self.can_retreat:
                    unit_hit_probs[new_destroyed_col] = (unit_hit_probs.unit_hits > 1).astype(int)
                else:
                    unit_hit_probs[new_destroyed_col] = (unit_hit_probs.unit_hits > 0).astype(int)

            # rename columns in our outcome_preds to join to the new data and
            # and redefine this object once we've updated the data for this
            # unit.
            prior_df = self.outcome_preds.rename({
                'hits_left':'total_available_hits'
            }, axis=1)
            unit_hit_probs = pd.merge(
                left=prior_df,
                right=unit_hit_probs,
                on='total_available_hits',
                how='left'
            )

            # Update outcome probability
            unit_hit_probs.outcome_pred = unit_hit_probs.outcome_pred * unit_hit_probs.unit_hits_pred

            # Update unit outcome counts
            if unit_type in ['inf','tnk','art'] and self.can_retreat:
                unit_retreat_col = f"{unit_type}_retreat"
                unit_hit_probs[unit_retreat_col] = unit_hit_probs[unit_retreat_col]+unit_hit_probs[new_retreat_col]
            unit_destroyed_col = f"{unit_type}_destroyed"
            unit_hit_probs[unit_destroyed_col] = unit_hit_probs[unit_destroyed_col]+unit_hit_probs[new_destroyed_col]
            self.outcome_preds = unit_hit_probs.groupby(['hits_left']+unit_outcome_cols).outcome_pred.sum().reset_index()

        # Set a ceiling for the number of supplies and trucks destroyed equal
        # to the number of units we started with
        self.outcome_preds.loc[self.outcome_preds.supply_destroyed > self.supply_num, 'supply_destroyed'] = self.supply_num
        self.outcome_preds.loc[self.outcome_preds.truck_destroyed > self.truck_num, 'truck_destroyed'] = self.truck_num
        self.outcome_preds = self.outcome_preds.groupby(unit_outcome_cols).outcome_pred.sum().reset_index()

    def __calc_single_unit_hit_slots(self, total_available_hits, unit_hit_slots):
        """
        Calculates the distribution of probability of number of hits assigned
        to any unit given the number of hit slots that they have and the total
        number of hits that are available to be assigned.
        """
        single_unit_hit_slots = pd.DataFrame()
        for unit_hits in range(total_available_hits+1):
            perms = factorial(total_available_hits)/(factorial(unit_hits)*factorial(total_available_hits-unit_hits))
            p_unit_hits = (
                ((unit_hit_slots/self.hit_nums)**unit_hits)
                *(1-(unit_hit_slots/self.hit_nums))**(total_available_hits-unit_hits)
                *(perms)
             )
            if total_available_hits == 0:
                if unit_hits == 0:
                    p_unit_hits = 1
                else:
                    p_unit_hits = 0

            single_unit_hit_slots = pd.concat([
                single_unit_hit_slots,
                pd.DataFrame({
                    'hit_slots':unit_hit_slots,
                    'total_available_hits':total_available_hits,
                    'unit_hits':unit_hits,
                    'unit_hits_pred':p_unit_hits
                }, index=[0])
            ]).reset_index(drop=True)
        single_unit_hit_slots = single_unit_hit_slots.assign(
            hits_left = single_unit_hit_slots.total_available_hits - single_unit_hit_slots.unit_hits
            )
        return single_unit_hit_slots

    def _aggregate_outcomes(self):
        """
        Aggregates the final distribution of all outcomes to various levels
        and groupings including a distribution of the power leftover in the
        defending hex after the attack, the probability of total evacuation,
        the expectation of the total power that will be destroyed by the
        attack, and the distribution of the number of units left in the hex.
        """
        self.__calculate_power_left_dist()
        self.__calculate_unit_destroyed_dist()

    def __calculate_power_left_dist(self):
        """
        Find power left distribution (power_left = 0 is chance of retreat)
        """
        self.power_left_dist = self.outcome_preds.copy()
        self.power_left_dist = self.power_left_dist.assign(
            inf_left = self.inf - (self.power_left_dist.inf_retreat + self.power_left_dist.inf_destroyed),
            tnk_left = self.tnk - (self.power_left_dist.tnk_retreat + self.power_left_dist.tnk_destroyed),
            art_left = self.art - (self.power_left_dist.art_retreat + self.power_left_dist.art_destroyed),
            supply_left = self.supply_num - self.power_left_dist.supply_destroyed,
            truck_left = self.truck_num - self.power_left_dist.truck_destroyed
        )

        # Use the interim state of this data to branch off a distribution of
        # the units left
        units_left_cols = ['inf_left','tnk_left','art_left','supply_left','truck_left']
        self.units_left_dist = self.power_left_dist[units_left_cols + ['outcome_pred']]
        self.units_left_dist = self.units_left_dist.groupby(units_left_cols).outcome_pred.sum().reset_index()
        self.units_left_dist = self.units_left_dist.assign(
            evacuate = (self.units_left_dist[['inf_left','tnk_left','art_left']].sum(axis=1) == 0).astype(int)
            )

        self.power_left_dist = self.power_left_dist.assign(
            power_left = self.power_left_dist.inf_left + self.power_left_dist.tnk_left*2 + self.power_left_dist.art_left*3
        )
        self.power_left_dist = self.power_left_dist.groupby('power_left').outcome_pred.sum().reset_index()
        if self.power_left_dist.power_left.min() == 0:
            self.prob_evacuate = self.power_left_dist[self.power_left_dist.power_left == 0].reset_index().outcome_pred.loc[0]
        else:
            self.prob_evacuate = 0

    def __calculate_unit_destroyed_dist(self):
        """
        Find the unit destroyed distribution along with the expectation of
        how much defending power will be destroyed
        """
        destroyed_cols = ['inf_destroyed','tnk_destroyed','art_destroyed']
        self.unit_destroyed_dist = self.outcome_preds[destroyed_cols + ['outcome_pred']]
        self.unit_destroyed_dist = self.unit_destroyed_dist.groupby(destroyed_cols).outcome_pred.sum().reset_index()
        self.unit_destroyed_dist['total_units_destroyed'] = self.unit_destroyed_dist[destroyed_cols].sum(axis=1)
        self.unit_destroyed_dist['total_units_survived'] = self.total_defending_units - self.unit_destroyed_dist.total_units_destroyed
        self.unit_destroyed_dist['total_power_destroyed'] = (
            self.unit_destroyed_dist.inf_destroyed
            + self.unit_destroyed_dist.tnk_destroyed*2
            + self.unit_destroyed_dist.art_destroyed*3
        )

        self.total_power_destroyed_dist = self.unit_destroyed_dist.groupby('total_power_destroyed').outcome_pred.sum().reset_index()

        self.total_power_destroyed_dist = self.total_power_destroyed_dist.sort_values('total_power_destroyed', ignore_index=True, ascending=False)
        self.total_power_destroyed_dist['or_more_prob'] = self.total_power_destroyed_dist.outcome_pred.cumsum()

        self.total_power_destroyed_dist = self.total_power_destroyed_dist.sort_values('total_power_destroyed', ignore_index=True)
        self.total_power_destroyed_dist['or_less_prob'] = self.total_power_destroyed_dist.outcome_pred.cumsum()
        self.exp_power_destroyed = (self.total_power_destroyed_dist.total_power_destroyed*self.total_power_destroyed_dist.outcome_pred).sum()
