# axis_and_allies
Repository for tools that I've created to help understand the expected outcomes of player actions in the Axis and Allies game series.

## 1. `battle_of_the_bulge`
Modules pertaining to the [Axis and Allies: Battle of the Bulge](https://boardgamegeek.com/boardgame/22457/axis-allies-battle-bulge) board game. Functionality runs through two main objects contained in separate modules. Main object is an attack simulator (`BoBAttackSimulator`) that calculates the probability of all possible outcomes given a single attack scenario (one hexagon attacking another). This object is leveraged by a helper object (`BoBAttackHelper`) to explore the outcomes of hypothetical scenarios and simulate through multiple attacks on a single defending hexagon. 

### `BoBAttackSimulator`
Simulator for Axis and Allies: Battle of the Bulge's combat mechanic. One instance simulates a single attack upon a single defending hex and stores as attributes helpful information such as the total expected defending power destroyed in the attack, the probability of clearing the defending hex via the attack, and a distribution of of all possible posterior states for the defending hex.

#### Examples:
---------
**Getting key outputs from a single simulation**
```
>>> from battle_of_the_bulge.bob_attack_simulator import BoBAttackSimulator
>>> sim = BoBAttackSimulator(power=10, inf=2, tnk=1, art=0, supply=3, truck=0)
>>> sim.process()
>>> sim.report_key_findings()
EVACUATION PROBABILITY:    0.164
EXPECTED POWER DESTROYED:  0.924
```

### `BoBAttackHelper`
Utilizes the base object, BoBAttackSimulator, to perform a number of
helpful tasks such as:
1. calculating how the probability of evacuation and the expectation of the total power destroyed in a hex increases with the available offensive power.
2. calculating the probability of evacuation and expected destroyed defending power when a single hex is attacked multiple times.

Is able to output and save helpful graphics relating to these outputs.

This object extends the capability of the BoBAttackSimulator by using the output of the simulator to iterate through multiple hypothetical attacks on a single defending hex either independently to explore the effects of increasing power on our expected results, or consecutively to explore the effect of launching multiple attacks on the defending hex.

#### Examples: 
---------
**Exploring how an increasing amount of attacking power changes the probability of defending hex evacuation and expected material to be destroyed.**
```
>>> from battle_of_the_bulge.bob_attack_helper import BoBAttackHelper
>>> helper = BoBAttackHelper(inf=2, tnk=1, art=1, supply=3, truck=1)
>>> helper.simulate_through_all_power()
```
![image](https://github.com/swhetzel/axis_and_allies/assets/79474788/9223a71f-ca83-451e-9a50-8286811bcd50)
![image](https://github.com/swhetzel/axis_and_allies/assets/79474788/d696a708-2ab7-4567-a5e9-28f1395a8245)

**Calculating the probability of hexagon evacuation following multiple attacks.**
```
>>> from battle_of_the_bulge.bob_attack_helper import BoBAttackHelper
>>> helper = BoBAttackHelper(inf=4, tnk=2, supply=3)
>>> attacks = [12,10,10]
>>> helper.simulate_multi_attack(attack_powers=attacks, verbose=True)
PROBABILITY OF EVAC FOR MULTI ATTACK: 0.89
```

### Future Work:
1. Provide expected power destroyed for multi-attacks
2. Provide expected outcomes for multi-attacks where defending hexe(s) may attack back.
    - Process should reason through the best order of attack for each side and provide the expected outcomes for a suite of attacks and counterattacks for multiple hexes. 

