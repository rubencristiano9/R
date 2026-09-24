# ==============================================================================
# V5 -> TAPE READER: EXPORT EVERY TRADE OF THE FOUR FROZEN RULES
# ==============================================================================
#
# WHAT THIS DOES
#   Tape Reader's Strategy tab replays the V5 rules' trades (minute + side).
#   V5 saved the trades of ONE rule only (its champion, file 16). This writes
#   the trades of all four rules, year by year, exactly as V5 made them:
#
#     7__NQ_ES__xgb_d2__0.0100     7m XGB NQ+ES, 1%
#     7__NQ_ES__xgb_d2__0.0500     7m XGB NQ+ES, 5%   (same model as 1%, other cutoff)
#     7__NQ_ONLY__ranger__0.0200   7m ranger NQ only, 2%
#     1__NQ_ONLY__xgb_d2__0.1000   1m XGB NQ only, 10%
#
# HOW
#   1. Runs NQ_ES_ROLLSAFE_WALKFORWARD_V5.R ONLY up to the end of its section 11
#      (data, roll-safe features, samples, FOLDS, fit_model, predict_model).
#      Its output folder is renamed to v5_trade_export_audit, so NOTHING in
#      nq_es_rollsafe_walkforward_v5 is overwritten. The long search (12-14)
#      and the ablation (16) are not run. HORIZONS is cut to 1 and 7, the only
#      two the four rules use; each horizon's sample is built on its own, so
#      this changes nothing for them (the check below would catch it if it did).
#   2. For each rule, runs V5's own section-15 loop, line for line: per year,
#      fit on the training years, take the cutoff from the calibration year,
#      score the test year, keep the rows at or beyond the cutoff.
#   3. CHECK: each year's cutoff, number of trades and number of wins must equal
#      nq_es_rollsafe_walkforward_v5/08_walkforward_fold_results.csv. If any
#      differs, it stops and writes NOTHING. Both models are seeded explicitly
#      in V5's fit_model, so an exact match is expected.
#
# OUTPUT (next to the NQ data file)
#   v5_trades/<candidate_id>.csv   fold, signal_et, signal_date, p_up,
#                                  confidence, cutoff, selected, prediction,
#                                  outcome, win
#   v5_trades/00_check.csv         the per-year comparison with V5
#
#   signal_et is UTC and marks the END of the bar the model read -- the minute
#   whose OPEN the trade enters at in Tape Reader. Same column as V5's file 16.
#
# THEN
#   Put the v5_trades folder next to build_viewer3.py and rebuild the page.
#   v5_pack.py re-checks every file against V5 before the page uses it.
#
# OOS SAFETY
#   Reads only the original files ending 2026-03-13 (V5's own inputs) and
#   stops if any trade falls on or after 2026-03-14.
# ==============================================================================

V5_SCRIPT <- "NQ_ES_ROLLSAFE_WALKFORWARD_V5.R"

RULE_IDS <- c(
  "7__NQ_ES__xgb_d2__0.0100",
  "7__NQ_ES__xgb_d2__0.0500",
  "7__NQ_ONLY__ranger__0.0200",
  "1__NQ_ONLY__xgb_d2__0.1000"
)

SEAL_DATE <- as.Date("2026-03-14")

# floating-point slack for the cutoff only; trade and win counts must be exact
CUTOFF_TOL <- 1e-9



# ==============================================================================
# 1. RUN V5 UP TO THE END OF SECTION 11
# ==============================================================================

if (!file.exists(V5_SCRIPT)) {
  message("Choose ", V5_SCRIPT, " ...")
  V5_SCRIPT <- file.choose()
}

v5_lines <- readLines(V5_SCRIPT, warn = FALSE)

sec12 <- grep("^# 12\\. SCORING", v5_lines)

if (length(sec12) != 1L) {
  stop("Could not find exactly one '# 12. SCORING' header in ", V5_SCRIPT)
}

# stop at the '# =====' rule just above the section-12 title
cut_at <- max(grep("^# =+\\s*$", v5_lines[seq_len(sec12 - 1L)]))
prefix <- v5_lines[seq_len(cut_at - 1L)]

# redirect V5's output folder so none of its files is touched
out_line <- grep("\"nq_es_rollsafe_walkforward_v5\"", prefix, fixed = TRUE)

if (length(out_line) != 1L) {
  stop("Expected exactly one OUT folder name in V5's settings; found ",
       length(out_line))
}

prefix[out_line] <- sub(
  "\"nq_es_rollsafe_walkforward_v5\"",
  "\"v5_trade_export_audit\"",
  prefix[out_line],
  fixed = TRUE
)

# The uploaded V5 script has its double brackets split across lines
# ("SAMPLES[" newline "[as.character(h)]" newline "]"), which R cannot parse.
# Re-join them: the tokens are the same, only the line breaks move.
prefix_text <- paste(prefix, collapse = "\n")
prefix_text <- gsub("\\[[ \t]*\n[ \t]*\\[", "[[", prefix_text, perl = TRUE)
prefix_text <- gsub("\\][ \t]*\n[ \t]*\\]", "]]", prefix_text, perl = TRUE)

exprs <- parse(text = prefix_text, keep.source = FALSE)

message("Running V5 sections 0-11 (", length(exprs), " top-level expressions)...")

for (k in seq_along(exprs)) {

  eval(exprs[[k]], envir = globalenv())

  # right after V5 sets HORIZONS, keep only the two these rules use
  e <- exprs[[k]]
  if (is.call(e) && identical(e[[1]], as.name("<-")) &&
      identical(e[[2]], as.name("HORIZONS"))) {
    assign("HORIZONS", c(1L, 7L), envir = globalenv())
    message("HORIZONS cut to 1 and 7 for this export.")
  }
}

for (need in c("FOLDS", "SAMPLES", "FEATURE_SETS", "fit_model",
               "predict_model", "NQ_FILE")) {
  if (!exists(need, envir = globalenv())) {
    stop("V5 did not define ", need, " before section 12; has the script changed?")
  }
}



# ==============================================================================
# 2. V5'S OWN RESULTS, TO CHECK AGAINST
# ==============================================================================

V5_DIR <- file.path(dirname(NQ_FILE), "nq_es_rollsafe_walkforward_v5")

REF <- data.table::fread(file.path(V5_DIR, "08_walkforward_fold_results.csv"))

OUT_TRADES <- file.path(dirname(NQ_FILE), "v5_trades")



# ==============================================================================
# 3. V5 SECTION 15, ONE RULE AT A TIME
# ==============================================================================

# predictions per (horizon, inputs, model, year), shared between rules
FIT_CACHE <- new.env()

run_rule <- function(cid) {

  spec <- REF[candidate_id == cid][1]

  if (!nrow(spec) || is.na(spec$horizon)) {
    stop("Rule ", cid, " is not in 08_walkforward_fold_results.csv")
  }

  champ_h <- spec$horizon
  champ_fs <- spec$feature_set
  champ_model <- spec$model_id
  champ_cov <- spec$target_coverage
  champ_features <- FEATURE_SETS[[champ_fs]]

  pred_list <- list()

  for (fi in seq_len(nrow(FOLDS))) {

    F <- FOLDS[fi]

    S <- SAMPLES[[as.character(champ_h)]]

    train <- S[
      signal_date >= F$train_start &
      signal_date < F$train_end &
      forecast_end_date < F$train_end &
      outcome != 0L
    ]

    calibrate <- S[
      signal_date >= F$cal_start &
      signal_date < F$cal_end &
      forecast_end_date < F$cal_end
    ]

    test <- S[
      signal_date >= F$test_start &
      signal_date < F$test_end &
      forecast_end_date < F$test_end
    ]

    # The 1% and 5% XGB rules are the SAME fitted model with different cutoffs:
    # fit each (horizon, inputs, model, year) once and reuse its predictions.
    fit_key <- paste(champ_h, champ_fs, champ_model, F$fold, sep = "|")

    if (is.null(FIT_CACHE[[fit_key]])) {
      model <- fit_model(train, champ_features, champ_model)
      FIT_CACHE[[fit_key]] <- list(
        p_cal = predict_model(model, calibrate, champ_features),
        p_test = predict_model(model, test, champ_features)
      )
      rm(model)
    } else {
      message("  (same fitted model as an earlier rule: ", fit_key, ")")
    }

    p_cal <- FIT_CACHE[[fit_key]]$p_cal
    p_test <- FIT_CACHE[[fit_key]]$p_test

    cutoff <- as.numeric(
      stats::quantile(
        abs(p_cal - 0.5),
        probs = 1 - champ_cov,
        names = FALSE,
        type = 7
      )
    )

    confidence <- abs(p_test - 0.5)
    selected <- confidence >= cutoff
    side <- ifelse(p_test >= 0.5, 1L, -1L)

    P <- data.table::data.table(
      fold = F$fold,
      signal_et = test$signal_et,
      signal_date = test$signal_date,
      p_up = p_test,
      confidence = confidence,
      cutoff = cutoff,
      selected = selected,
      prediction = side,
      outcome = test$outcome,
      win = as.integer(side == test$outcome)
    )

    pred_list[[fi]] <- P[selected == TRUE]

    message(sprintf("  %-28s %-9s cutoff %.10f  trades %d",
                    cid, F$fold, cutoff, sum(selected)))

    rm(p_cal, p_test)
    invisible(gc(FALSE))
  }

  data.table::rbindlist(pred_list, fill = TRUE)
}



# ==============================================================================
# 4. RUN, CHECK, THEN WRITE (all or nothing)
# ==============================================================================

TRADES <- list()
CHECK <- list()

for (cid in RULE_IDS) {

  message("Rule ", cid, " ...")

  TR <- run_rule(cid)

  for (f in unique(FOLDS$fold)) {

    ref <- REF[candidate_id == cid & fold == f]
    mine <- TR[fold == f]
    cut_mine <- if (nrow(mine)) mine$cutoff[1] else NA_real_

    CHECK[[length(CHECK) + 1L]] <- data.table::data.table(
      candidate_id = cid,
      fold = f,
      trades = nrow(mine),
      v5_trades = ref$selected_n,
      wins = sum(mine$win),
      v5_wins = ref$wins,
      cutoff = cut_mine,
      v5_cutoff = ref$confidence_cutoff,
      match = nrow(mine) == ref$selected_n &&
        sum(mine$win) == ref$wins &&
        isTRUE(abs(cut_mine - ref$confidence_cutoff) <= CUTOFF_TOL)
    )
  }

  if (nrow(TR) && max(as.Date(TR$signal_et, tz = "UTC")) >= SEAL_DATE) {
    stop("Rule ", cid, " has a trade on or after ", SEAL_DATE,
         "; nothing written.")
  }

  data.table::setorder(TR, signal_et)
  TRADES[[cid]] <- TR
}

CHECK <- data.table::rbindlist(CHECK)

print(CHECK)

if (!all(CHECK$match)) {
  stop("The export does NOT reproduce V5 for the rows marked match = FALSE ",
       "above. Nothing was written.")
}

dir.create(OUT_TRADES, recursive = TRUE, showWarnings = FALSE)

for (cid in RULE_IDS) {
  data.table::fwrite(TRADES[[cid]], file.path(OUT_TRADES, paste0(cid, ".csv")))
}

data.table::fwrite(CHECK, file.path(OUT_TRADES, "00_check.csv"))

message("Done: every rule reproduces V5 year by year. Files in ", OUT_TRADES)
