NQ DIRECTION PHASE 1B — OUTPUT GUIDE

Primary tables:
  yearly_horizon_model_threshold_metrics.csv
  aggregate_horizon_model_threshold_metrics.csv
  nested_selected_configurations_by_year.csv
  nested_policy_summary.csv

Primary plots:
  01_short_model_comparison.png
  02_short_directional_edge.png
  03_long_calendar_state_decomposition.png
  04_long_winrate_heatmap_with_N.png
  05_long_selection_gain_heatmap.png
  06_nested_policy_summary.png
  07_nested_short_yearly.png
  08_nested_long_yearly.png
  09_long_up_down_reliability.png
  10_target_availability.png

Interpretation order:
  1. Does the short Full model beat the majority baseline?
  2. At long horizons, does Full beat Calendar-only?
  3. Do confidence filters improve win rate with adequate N?
  4. Does prior-year configuration selection survive in the next year?
  5. Are long-horizon gains predominantly predicted-UP signals?

Do not promote a configuration to a trading strategy solely because it
looks best in aggregate exploratory OOS plots. The nested summary is the
more important estimate for model/horizon/threshold selection.
