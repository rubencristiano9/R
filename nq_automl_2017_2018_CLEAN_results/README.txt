NQ AutoML Persistence — CLEAN build

BIG-PICTURE RESEARCH GOAL:
Execution-valid alpha -> transitory/adaptive predictability -> trade geometry -> prop optimization.

Chronology:
Jan-Jul 2017 = model fitting
Aug-Sep 2017 = H2O validation AND H2O leaderboard frame
Oct-Dec 2017 = custom directional-win-rate discovery selection
2018 = untouched OOS test

Important:
H2O's internal leaderboard is NOT the trading objective.
Every model is rescored on Oct-Dec 2017 using directional win rate.
Exact flat outcomes remain in discovery/test and count as non-wins.
H2O-native XGBoost is excluded on Windows.

Primary output:
strict_champion_2018_results.csv

If you reselect among top strategies after seeing 2018, 2018 becomes validation
and 2019 must become the next untouched test.
