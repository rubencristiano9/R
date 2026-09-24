
# ==============================================================================
# V5 PROP-FIRM STRATEGY DIAGNOSTIC PLOTS
# ==============================================================================
#
# Run AFTER V5 has completed.
#
# Choose:
#   09_walkforward_aggregate_all_candidates.csv
#
# The script automatically loads the other V5 result files from that folder.
#
# Purpose:
#   Compare directional candidates for eventual prop-firm implementation.
#
# Important:
#   These plots assess predictive quality and robustness.
#   They do NOT yet include P&L, commissions, slippage, stop/target geometry,
#   max daily loss, trailing drawdown, or prop-firm pass probability.
# ==============================================================================

needed <- c("data.table", "ggplot2")

missing <- needed[
  !vapply(needed, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing)) {
  stop(
    "Missing package(s): ",
    paste(missing, collapse = ", "),
    "\nInstall with install.packages()."
  )
}

message("Choose 09_walkforward_aggregate_all_candidates.csv")
AGG_FILE <- file.choose()

OUT <- dirname(AGG_FILE)
PLOT_DIR <- file.path(OUT, "prop_firm_plots")
dir.create(PLOT_DIR, recursive = TRUE, showWarnings = FALSE)

files <- c(
  aggregate = "09_walkforward_aggregate_all_candidates.csv",
  folds = "08_walkforward_fold_results.csv",
  champion = "11_DEVELOPMENT_CHAMPION.csv",
  champion_folds = "15_champion_fold_results.csv",
  ablation = "20_ablation_aggregate.csv",
  ledger_2026 = "21_2026_strategy_ledger.csv"
)

paths <- file.path(OUT, files)

if (any(!file.exists(paths))) {
  stop(
    "Missing V5 output file(s): ",
    paste(names(paths)[!file.exists(paths)], collapse = ", ")
  )
}

AGG <- data.table::fread(paths["aggregate"])
FOLDS <- data.table::fread(paths["folds"])
CHAMPION <- data.table::fread(paths["champion"])
CHAMP_FOLDS <- data.table::fread(paths["champion_folds"])
ABLATION <- data.table::fread(paths["ablation"])
LEDGER26 <- data.table::fread(paths["ledger_2026"])

pct1 <- function(x) {
  ifelse(is.na(x), NA_character_, sprintf("%.1f%%", 100*x))
}

model_label <- function(x) {
  out <- x
  out[x == "logit"] <- "Logit"
  out[x == "ranger"] <- "Ranger"
  out[x == "xgb_d2"] <- "XGB d2"
  out[x == "xgb_d3"] <- "XGB d3"
  out[x == "xgb_d4"] <- "XGB d4"
  out[x == "xgb_d5"] <- "XGB d5"
  out
}

feature_label <- function(x) {
  out <- x
  out[x == "NQ_ONLY"] <- "NQ only"
  out[x == "NQ_ES"] <- "NQ + ES"
  out
}

strategy_label <- function(horizon, feature_set, model_id, coverage) {
  paste0(
    horizon, "m | ",
    model_label(model_id), " | ",
    feature_label(feature_set), " | ",
    sprintf("%.1f%%", 100*coverage)
  )
}

base_theme <- ggplot2::theme_minimal(base_size = 12) +
  ggplot2::theme(
    panel.grid.minor = ggplot2::element_blank(),
    plot.title = ggplot2::element_text(face = "bold", size = 15),
    plot.subtitle = ggplot2::element_text(size = 10.5),
    plot.caption = ggplot2::element_text(size = 9, hjust = 0),
    axis.title = ggplot2::element_text(face = "bold"),
    strip.text = ggplot2::element_text(face = "bold"),
    legend.position = "bottom"
  )

save_plot <- function(p, name, width, height) {
  ggplot2::ggsave(
    filename = paste0(name, ".png"),
    plot = p,
    path = PLOT_DIR,
    width = width,
    height = height,
    units = "in",
    dpi = 320,
    bg = "white"
  )
  ggplot2::ggsave(
    filename = paste0(name, ".pdf"),
    plot = p,
    path = PLOT_DIR,
    width = width,
    height = height,
    units = "in",
    bg = "white"
  )
}

AGG[, v5_rank := .I]
AGG[, model_display := model_label(model_id)]
AGG[, feature_display := feature_label(feature_set)]
AGG[, strategy := strategy_label(
  horizon, feature_set, model_id, target_coverage
)]

FOLDS[, strategy := strategy_label(
  horizon, feature_set, model_id, target_coverage
)]

ROBUST <- AGG[
  temporal_ok == TRUE &
  persistence_ok == TRUE &
  is.finite(wr_block_lower)
]

if (!nrow(ROBUST)) ROBUST <- AGG[1:min(.N,100)]

TOP20 <- AGG[1:min(.N,20)]
TOP12 <- AGG[1:min(.N,12)]
TOP10 <- AGG[1:min(.N,10)]


# ==============================================================================
# 1. Robustness frontier
# ==============================================================================

P1 <- ROBUST[
  is.finite(overall_wr) &
  is.finite(wr_block_lower)
]

if (nrow(P1)) {

  LABEL <- P1[v5_rank <= 10]

  p <- ggplot2::ggplot(
    P1,
    ggplot2::aes(
      x = overall_wr,
      y = wr_block_lower,
      size = selected_n,
      colour = model_display,
      shape = feature_display
    )
  ) +
    ggplot2::geom_hline(
      yintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_vline(
      xintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_point(alpha = 0.80) +
    ggplot2::geom_text(
      data = LABEL,
      ggplot2::aes(label = v5_rank),
      nudge_y = 0.0015,
      size = 3,
      check_overlap = TRUE,
      show.legend = FALSE
    ) +
    ggplot2::scale_x_continuous(labels = pct1) +
    ggplot2::scale_y_continuous(labels = pct1) +
    ggplot2::scale_size_continuous(range = c(2.5,9)) +
    ggplot2::labs(
      title = "Strategy robustness frontier",
      subtitle = "Observed repeated-OOS accuracy versus the week-block 95% lower bound",
      x = "Aggregate OOS win rate",
      y = "Week-block 95% lower bound",
      size = "Selected signals",
      colour = "Model",
      shape = "Features",
      caption = "Numbers are V5 ranks. Upper-right is stronger."
    ) +
    base_theme

  save_plot(p, "01_robustness_frontier", 10.5, 7.5)
}


# ==============================================================================
# 2. Accuracy versus opportunity
# ==============================================================================

P2 <- ROBUST[
  is.finite(overall_wr) &
  is.finite(mean_actual_coverage)
]

if (nrow(P2)) {

  p <- ggplot2::ggplot(
    P2,
    ggplot2::aes(
      x = mean_actual_coverage,
      y = overall_wr,
      size = total_nonoverlap_n,
      colour = model_display,
      shape = feature_display
    )
  ) +
    ggplot2::geom_hline(
      yintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_point(alpha = 0.78) +
    ggplot2::facet_wrap(
      ~ horizon,
      ncol = 4,
      labeller = ggplot2::labeller(
        horizon = function(x) paste0(x, " min")
      )
    ) +
    ggplot2::scale_x_continuous(labels = pct1) +
    ggplot2::scale_y_continuous(labels = pct1) +
    ggplot2::scale_size_continuous(range = c(2,8)) +
    ggplot2::labs(
      title = "Accuracy versus signal opportunity",
      subtitle = "Higher coverage provides more potential prop-firm attempts, but should not destroy directional edge",
      x = "Mean realised signal coverage",
      y = "Aggregate OOS win rate",
      size = "Non-overlapping signals",
      colour = "Model",
      shape = "Features",
      caption = "Coverage is on the 15-minute decision grid, not yet executed trades/day."
    ) +
    base_theme

  save_plot(p, "02_accuracy_vs_opportunity", 12.5, 8.5)
}


# ==============================================================================
# 3. Top-12 cross-year heatmap
# ==============================================================================

IDS12 <- TOP12$candidate_id

P3 <- FOLDS[candidate_id %in% IDS12]

if (nrow(P3)) {

  rank_map <- AGG[
    candidate_id %in% IDS12,
    .(candidate_id, v5_rank, strategy)
  ]

  P3 <- merge(P3, rank_map, by = "candidate_id", all.x = TRUE)

  P3[, strategy_plot := paste0("#", v5_rank, "  ", strategy)]

  order_levels <- rank_map[
    order(-v5_rank),
    paste0("#", v5_rank, "  ", strategy)
  ]

  P3[, strategy_plot := factor(
    strategy_plot,
    levels = order_levels
  )]

  P3[, fold := factor(
    fold,
    levels = c("2023","2024","2025","2026_YTD")
  )]

  p <- ggplot2::ggplot(
    P3,
    ggplot2::aes(
      x = fold,
      y = strategy_plot,
      fill = win_rate
    )
  ) +
    ggplot2::geom_tile() +
    ggplot2::geom_text(
      ggplot2::aes(label = pct1(win_rate)),
      size = 3.3
    ) +
    ggplot2::scale_fill_gradient2(
      midpoint = 0.50,
      labels = pct1,
      name = "Win rate"
    ) +
    ggplot2::labs(
      title = "Cross-year persistence of the top V5 strategies",
      subtitle = "A deployable rule should not depend on one exceptional calendar year",
      x = NULL,
      y = NULL,
      caption = "2026 YTD is shorter than the full-year folds."
    ) +
    base_theme +
    ggplot2::theme(
      panel.grid = ggplot2::element_blank(),
      legend.position = "right"
    )

  save_plot(p, "03_top12_cross_year_heatmap", 11.8, 8.5)
}


# ==============================================================================
# 4. Model × horizon robustness landscape
# ==============================================================================

LAND <- ROBUST[
  is.finite(wr_block_lower)
]

if (nrow(LAND)) {

  data.table::setorder(
    LAND,
    horizon,
    model_id,
    -wr_block_lower,
    -overall_wr
  )

  LAND <- LAND[
    ,
    .SD[1],
    by = .(horizon, model_id)
  ]

  LAND[, model_display := model_label(model_id)]
  LAND[, horizon_f := factor(
    horizon,
    levels = sort(unique(horizon))
  )]

  p <- ggplot2::ggplot(
    LAND,
    ggplot2::aes(
      x = horizon_f,
      y = model_display,
      fill = wr_block_lower
    )
  ) +
    ggplot2::geom_tile() +
    ggplot2::geom_text(
      ggplot2::aes(label = pct1(wr_block_lower)),
      size = 3.3
    ) +
    ggplot2::scale_fill_gradient2(
      midpoint = 0.50,
      labels = pct1,
      name = "Lower bound"
    ) +
    ggplot2::labs(
      title = "Where does the robust directional edge cluster?",
      subtitle = "Best stable candidate within each model × prediction-horizon combination",
      x = "Prediction horizon",
      y = NULL,
      caption = "Broad neighbouring strength is more convincing than one isolated high-WR cell."
    ) +
    base_theme +
    ggplot2::theme(
      panel.grid = ggplot2::element_blank(),
      legend.position = "right"
    )

  save_plot(p, "04_model_horizon_landscape", 10.5, 6.2)
}


# ==============================================================================
# 5. Feature ablation
# ==============================================================================

A <- data.table::copy(ABLATION)

A[, display := ablation_set]

A[ablation_set == "NQ_BASE", display := "NQ base"]
A[ablation_set == "NQ_BASE_PLUS_TECH", display := "NQ base + technicals"]
A[ablation_set == "NQ_BASE_PLUS_SESSION", display := "NQ base + session"]
A[ablation_set == "NQ_RICH", display := "NQ rich"]
A[ablation_set == "NQ_ES_RICH", display := "NQ + ES rich"]

A[, display := factor(
  display,
  levels = display[order(overall_wr)]
)]

p <- ggplot2::ggplot(
  A,
  ggplot2::aes(
    x = display,
    y = overall_wr
  )
) +
  ggplot2::geom_hline(
    yintercept = 0.50,
    linetype = "dashed",
    linewidth = 0.5
  ) +
  ggplot2::geom_errorbar(
    ggplot2::aes(
      ymin = wr_block_lower,
      ymax = wr_block_upper
    ),
    width = 0.15,
    na.rm = TRUE
  ) +
  ggplot2::geom_point(size = 3.5) +
  ggplot2::geom_text(
    ggplot2::aes(
      label = paste0(
        pct1(overall_wr),
        " | edge ",
        pct1(edge)
      )
    ),
    hjust = -0.05,
    size = 3.2,
    check_overlap = TRUE
  ) +
  ggplot2::coord_flip(clip = "off") +
  ggplot2::scale_y_continuous(labels = pct1) +
  ggplot2::labs(
    title = "What information actually adds predictive value?",
    subtitle = "Ablation at the champion's model, horizon and target coverage",
    x = NULL,
    y = "Aggregate OOS win rate",
    caption = "Error bars are week-block intervals. Edge is versus the same-timestamp directional baseline."
  ) +
  base_theme +
  ggplot2::theme(
    plot.margin = ggplot2::margin(8,120,8,8)
  )

save_plot(p, "05_feature_ablation", 11, 6.5)


# ==============================================================================
# 6. Long versus short accuracy
# ==============================================================================

P6 <- ROBUST[
  is.finite(long_wr) &
  is.finite(short_wr) &
  long_n > 0 &
  short_n > 0
]

if (nrow(P6)) {

  P6[, balanced_n := pmin(long_n, short_n)]
  LABEL <- P6[v5_rank <= 10]

  p <- ggplot2::ggplot(
    P6,
    ggplot2::aes(
      x = long_wr,
      y = short_wr,
      size = balanced_n,
      colour = model_display,
      shape = feature_display
    )
  ) +
    ggplot2::geom_hline(
      yintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_vline(
      xintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_point(alpha = 0.80) +
    ggplot2::geom_text(
      data = LABEL,
      ggplot2::aes(label = v5_rank),
      nudge_y = 0.0015,
      size = 3,
      check_overlap = TRUE,
      show.legend = FALSE
    ) +
    ggplot2::scale_x_continuous(labels = pct1) +
    ggplot2::scale_y_continuous(labels = pct1) +
    ggplot2::scale_size_continuous(range = c(2.5,9)) +
    ggplot2::labs(
      title = "Is the edge genuinely two-sided?",
      subtitle = "Long and short repeated-OOS win rates",
      x = "Long-signal win rate",
      y = "Short-signal win rate",
      size = "Smaller of long/short N",
      colour = "Model",
      shape = "Features",
      caption = "Upper-right is strongest. One-sided rules can still be viable, but should be implemented explicitly as such."
    ) +
    base_theme

  save_plot(p, "06_long_vs_short", 9.5, 7.5)
}


# ==============================================================================
# 7. Concentration risk
# ==============================================================================

P7 <- ROBUST[
  is.finite(max_top5_day_share_full) &
  is.finite(overall_wr)
]

if (nrow(P7)) {

  LABEL <- P7[v5_rank <= 10]

  p <- ggplot2::ggplot(
    P7,
    ggplot2::aes(
      x = max_top5_day_share_full,
      y = overall_wr,
      size = selected_n,
      colour = model_display,
      shape = feature_display
    )
  ) +
    ggplot2::geom_hline(
      yintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_vline(
      xintercept = 0.35,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_point(alpha = 0.80) +
    ggplot2::geom_text(
      data = LABEL,
      ggplot2::aes(label = v5_rank),
      nudge_y = 0.0015,
      size = 3,
      check_overlap = TRUE,
      show.legend = FALSE
    ) +
    ggplot2::scale_x_continuous(labels = pct1) +
    ggplot2::scale_y_continuous(labels = pct1) +
    ggplot2::scale_size_continuous(range = c(2.5,9)) +
    ggplot2::labs(
      title = "Accuracy versus concentration risk",
      subtitle = "Prefer performance distributed through time rather than generated by a few exceptional days",
      x = "Worst full-year share from five busiest signal days",
      y = "Aggregate OOS win rate",
      size = "Selected signals",
      colour = "Model",
      shape = "Features",
      caption = "The vertical dashed line is the 35% V5 stability gate."
    ) +
    base_theme

  save_plot(p, "07_concentration_risk", 10, 7.5)
}


# ==============================================================================
# 8. Top-10 strategy performance through time
# ==============================================================================

IDS10 <- TOP10$candidate_id
P8 <- FOLDS[candidate_id %in% IDS10]

if (nrow(P8)) {

  rank_map <- TOP10[, .(
    candidate_id,
    v5_rank,
    strategy
  )]

  P8 <- merge(
    P8,
    rank_map,
    by = "candidate_id",
    all.x = TRUE
  )

  P8[, strategy_plot := paste0("#", v5_rank, " ", strategy)]

  P8[, fold := factor(
    fold,
    levels = c("2023","2024","2025","2026_YTD")
  )]

  p <- ggplot2::ggplot(
    P8,
    ggplot2::aes(
      x = fold,
      y = win_rate,
      group = strategy_plot,
      colour = strategy_plot
    )
  ) +
    ggplot2::geom_hline(
      yintercept = 0.50,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_line(linewidth = 0.8, alpha = 0.85) +
    ggplot2::geom_point(size = 2.2) +
    ggplot2::scale_y_continuous(labels = pct1) +
    ggplot2::labs(
      title = "Top-10 strategies through time",
      subtitle = "Useful for spotting decay, regime sensitivity and consistency",
      x = NULL,
      y = "OOS win rate",
      colour = "Strategy",
      caption = "2026 YTD contains fewer observations and is development-OOS."
    ) +
    base_theme +
    ggplot2::theme(
      legend.position = "right",
      legend.text = ggplot2::element_text(size = 8)
    )

  save_plot(p, "08_top10_walkforward_lines", 12, 7.5)
}


# ==============================================================================
# 9. 2026 versus prior full-year mean
#
# Direct decay / continuation diagnostic.
# ==============================================================================

FULL <- FOLDS[
  fold %in% c("2023","2024","2025"),
  .(
    full_year_mean_wr = mean(win_rate),
    full_year_min_wr = min(win_rate),
    full_year_mean_edge = mean(edge)
  ),
  by = candidate_id
]

Y26 <- FOLDS[
  fold == "2026_YTD",
  .(
    candidate_id,
    wr_2026 = win_rate,
    edge_2026 = edge,
    n_2026 = selected_n
  )
]

P9 <- merge(
  AGG[, .(
    candidate_id,
    v5_rank,
    model_display,
    feature_display,
    selected_n
  )],
  merge(FULL,Y26,by="candidate_id"),
  by="candidate_id"
)

P9 <- P9[
  v5_rank <= 50 &
  is.finite(full_year_mean_wr) &
  is.finite(wr_2026)
]

if (nrow(P9)) {

  p <- ggplot2::ggplot(
    P9,
    ggplot2::aes(
      x = full_year_mean_wr,
      y = wr_2026,
      size = n_2026,
      colour = model_display,
      shape = feature_display
    )
  ) +
    ggplot2::geom_abline(
      slope = 1,
      intercept = 0,
      linetype = "dashed",
      linewidth = 0.5
    ) +
    ggplot2::geom_hline(
      yintercept = 0.50,
      linetype = "dotted",
      linewidth = 0.5
    ) +
    ggplot2::geom_vline(
      xintercept = 0.50,
      linetype = "dotted",
      linewidth = 0.5
    ) +
    ggplot2::geom_point(alpha = 0.80) +
    ggplot2::geom_text(
      data = P9[v5_rank <= 10],
      ggplot2::aes(label = v5_rank),
      nudge_y = 0.004,
      size = 3,
      check_overlap = TRUE,
      show.legend = FALSE
    ) +
    ggplot2::scale_x_continuous(labels = pct1) +
    ggplot2::scale_y_continuous(labels = pct1) +
    ggplot2::scale_size_continuous(range = c(2.5,9)) +
    ggplot2::labs(
      title = "Does the edge continue into 2026?",
      subtitle = "2026 YTD versus the mean OOS win rate across 2023-2025",
      x = "Mean 2023-2025 OOS win rate",
      y = "2026 YTD win rate",
      size = "2026 signals",
      colour = "Model",
      shape = "Features",
      caption = "Points below the diagonal weakened in 2026; small 2026 samples should be interpreted cautiously."
    ) +
    base_theme

  save_plot(p, "09_2026_vs_prior_years", 10, 7.5)
}


# ==============================================================================
# 10. TOP-25 DEPLOYMENT SHORTLIST CSV
# ==============================================================================

LED <- data.table::copy(LEDGER26)

data.table::setnames(
  LED,
  old = c(
    "selected_n","win_rate","baseline_wr","edge",
    "active_weeks","unique_days","top5_day_share",
    "long_n","long_wr","short_n","short_wr"
  ),
  new = c(
    "n_2026","wr_2026","baseline_2026","edge_2026",
    "weeks_2026","days_2026","top5_share_2026",
    "long_n_2026","long_wr_2026","short_n_2026","short_wr_2026"
  )
)

SHORTLIST <- merge(
  AGG[1:min(.N,25)],
  LED,
  by = c(
    "candidate_id",
    "horizon",
    "feature_set",
    "model_id",
    "xgb_depth",
    "target_coverage"
  ),
  all.x = TRUE
)

data.table::setorder(
  SHORTLIST,
  v5_rank
)

data.table::fwrite(
  SHORTLIST,
  file.path(
    PLOT_DIR,
    "V5_prop_firm_top25_shortlist.csv"
  )
)


cat("\n============================================================\n")
cat("PROP-FIRM DIAGNOSTIC PLOTS COMPLETE\n")
cat("============================================================\n")

cat("\nPlots saved to:\n")
cat(PLOT_DIR, "\n")

cat("\nCreated:\n")
cat("01_robustness_frontier\n")
cat("02_accuracy_vs_opportunity\n")
cat("03_top12_cross_year_heatmap\n")
cat("04_model_horizon_landscape\n")
cat("05_feature_ablation\n")
cat("06_long_vs_short\n")
cat("07_concentration_risk\n")
cat("08_top10_walkforward_lines\n")
cat("09_2026_vs_prior_years\n")
cat("V5_prop_firm_top25_shortlist.csv\n")
