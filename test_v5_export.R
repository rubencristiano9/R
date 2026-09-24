# ==============================================================================
# Test for V5_EXPORT_TRADES.R, runnable without the real data or models.
#
# Section 1 of the export (running V5's own script up to section 11) needs the
# databento files and xgboost/ranger, so it runs only on the real machine. What
# this checks is everything after it, using the export's OWN code for sections
# 2-4, evaluated unchanged:
#   - the per-year loop (V5 section 15) selects exactly the rows at or beyond
#     each year's calibration cutoff, on each side
#   - a reference that matches -> the files are written, one per rule
#   - a reference off by ONE win -> it stops and writes NOTHING
#   - the files it writes are accepted by v5_pack.py: run with
#     V5_EXPORT_TEST_DIR=<folder> and then  V5_DIR=<folder> python3 v5_pack.py
#
# Stand-ins: FOLDS copied from V5; SAMPLES synthetic (a 4-hour grid,
# 2017 -> 2026-03-13, outcome driven by one input); fit_model a logistic
# regression. The plumbing is the same whatever the model is.
#
# Run:  Rscript test_v5_export.R            (from the folder holding the script)
# ==============================================================================

suppressPackageStartupMessages(library(data.table))

PASS <- 0L; FAIL <- 0L
check <- function(name, cond) {
  if (isTRUE(cond)) { PASS <<- PASS + 1L; cat("  PASS ", name, "\n") }
  else { FAIL <<- FAIL + 1L; cat("  FAIL ", name, "\n") }
}

EXPORT <- "V5_EXPORT_TRADES.R"
src <- readLines(EXPORT, warn = FALSE)
# the export's settings (rule ids, seal date, tolerance) + its sections 2-4;
# section 1 (running V5 itself) is the part replaced by the stand-ins below
s1 <- grep("^# 1\\. RUN V5 UP TO", src)
from <- grep("^# 2\\. V5'S OWN RESULTS", src)
sections_2_to_4 <- c(src[seq_len(s1 - 2L)], src[(from - 1L):length(src)])

set.seed(11)

# ---- the stand-in V5 environment ----
FOLDS <- data.table(
  fold = c("2023", "2024", "2025", "2026_YTD"),
  train_start = as.Date(c("2017-01-01", "2018-01-01", "2019-01-01", "2020-01-01")),
  train_end = as.Date(c("2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01")),
  cal_start = as.Date(c("2022-01-01", "2023-01-01", "2024-01-01", "2025-01-01")),
  cal_end = as.Date(c("2023-01-01", "2024-01-01", "2025-01-01", "2026-01-01")),
  test_start = as.Date(c("2023-01-01", "2024-01-01", "2025-01-01", "2026-01-01")),
  test_end = as.Date(c("2024-01-01", "2025-01-01", "2026-01-01", "2026-03-14"))
)

make_sample <- function(h) {
  bar <- seq(as.POSIXct("2017-01-02 00:00", tz = "UTC"),
             as.POSIXct("2026-03-13 20:00", tz = "UTC"), by = "4 hours")
  n <- length(bar)
  f1 <- rnorm(n); f2 <- rnorm(n)
  outcome <- ifelse(0.8 * f1 + rnorm(n) > 0, 1L, -1L)
  outcome[sample.int(n, n %/% 50)] <- 0L
  data.table(
    signal_et = bar + 60,                       # the END of the feature bar, UTC
    signal_date = as.Date(bar, tz = "UTC"),
    forecast_end_date = as.Date(bar + 60 * (h + 1), tz = "UTC"),
    outcome = outcome, f1 = f1, f2 = f2
  )
}
SAMPLES <- list("1" = make_sample(1L), "7" = make_sample(7L))
FEATURE_SETS <- list(NQ_ONLY = c("f1", "f2"), NQ_ES = c("f1", "f2"))

FITS <- 0L
fit_model <- function(train, features, model_id) {
  FITS <<- FITS + 1L
  d <- train[, c(features, "outcome"), with = FALSE]
  d[, up := as.integer(outcome == 1L)][, outcome := NULL]
  glm(up ~ ., data = d, family = binomial())
}
predict_model <- function(model, x, features) {
  as.numeric(predict(model, newdata = x[, features, with = FALSE], type = "response"))
}

# V5_EXPORT_TEST_DIR keeps the output (R removes its own temp folder on exit),
# so the files can be fed through v5_pack.py afterwards
TMP <- Sys.getenv("V5_EXPORT_TEST_DIR", tempfile("v5export"))
dir.create(file.path(TMP, "nq_es_rollsafe_walkforward_v5"), recursive = TRUE)
NQ_FILE <- file.path(TMP, "NQ_1min_2010-06-07_to_2026-03-13_databento.csv")

RULES <- data.table(
  candidate_id = c("7__NQ_ES__xgb_d2__0.0100", "7__NQ_ES__xgb_d2__0.0500",
                   "7__NQ_ONLY__ranger__0.0200", "1__NQ_ONLY__xgb_d2__0.1000"),
  horizon = c(7L, 7L, 7L, 1L), feature_set = c("NQ_ES", "NQ_ES", "NQ_ONLY", "NQ_ONLY"),
  model_id = c("xgb_d2", "xgb_d2", "ranger", "xgb_d2"),
  target_coverage = c(0.01, 0.05, 0.02, 0.10)
)

# ---- the expected rows, computed independently of the export's code ----
expected <- list()
for (r in seq_len(nrow(RULES))) {
  R <- RULES[r]
  for (fi in seq_len(nrow(FOLDS))) {
    F <- FOLDS[fi]; S <- SAMPLES[[as.character(R$horizon)]]
    tr <- S[signal_date >= F$train_start & signal_date < F$train_end &
            forecast_end_date < F$train_end & outcome != 0L]
    ca <- S[signal_date >= F$cal_start & signal_date < F$cal_end & forecast_end_date < F$cal_end]
    te <- S[signal_date >= F$test_start & signal_date < F$test_end & forecast_end_date < F$test_end]
    m <- fit_model(tr, FEATURE_SETS[[R$feature_set]], R$model_id)
    pc <- predict_model(m, ca, FEATURE_SETS[[R$feature_set]])
    pt <- predict_model(m, te, FEATURE_SETS[[R$feature_set]])
    cut <- as.numeric(quantile(abs(pc - 0.5), 1 - R$target_coverage, names = FALSE, type = 7))
    keep <- abs(pt - 0.5) >= cut
    side <- ifelse(pt >= 0.5, 1L, -1L)
    expected[[length(expected) + 1L]] <- data.table(
      candidate_id = R$candidate_id, fold = F$fold, horizon = R$horizon,
      feature_set = R$feature_set, model_id = R$model_id,
      target_coverage = R$target_coverage, confidence_cutoff = cut,
      selected_n = sum(keep), wins = sum(side[keep] == te$outcome[keep]))
  }
}
REF_OK <- rbindlist(expected)
ref_path <- file.path(TMP, "nq_es_rollsafe_walkforward_v5", "08_walkforward_fold_results.csv")
out_dir <- file.path(TMP, "v5_trades")

run_export <- function(ref) {
  fwrite(ref, ref_path)
  unlink(out_dir, recursive = TRUE)
  env <- new.env(parent = globalenv())
  tryCatch({
    eval(parse(text = sections_2_to_4), envir = env)
    "ok"
  }, error = function(e) conditionMessage(e))
}

cat("--- a reference that matches ---\n")
FITS <- 0L
res <- suppressMessages(capture.output(r1 <- run_export(REF_OK)))
check("the 1% and 5% XGB rules share their fits (12 fits for 16 rule-years)", FITS == 12L)
check("the export finishes", identical(r1, "ok"))
files <- list.files(out_dir)
check("one file per rule, plus the check table",
      setequal(files, c(paste0(RULES$candidate_id, ".csv"), "00_check.csv")))
ck <- fread(file.path(out_dir, "00_check.csv"))
check("every rule and year matches V5", nrow(ck) == 16L && all(ck$match))

x <- fread(file.path(out_dir, "7__NQ_ES__xgb_d2__0.0500.csv"))
check("columns are the ones v5_pack.py reads",
      all(c("fold", "signal_et", "p_up", "prediction", "win", "selected") %in% names(x)))
check("every row is a trade (at or beyond its year's cutoff)", all(x$confidence >= x$cutoff))
check("side follows the score", all((x$p_up >= 0.5) == (x$prediction == 1L)))
check("times rise", !is.unsorted(x$signal_et, strictly = TRUE))
check("nothing on or after 2026-03-14", max(as.Date(x$signal_et, tz = "UTC")) < as.Date("2026-03-14"))
check("times are written as UTC ISO with Z",
      all(grepl("^\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\dZ$", readLines(file.path(out_dir,
          "7__NQ_ES__xgb_d2__0.0500.csv"))[-1] |> sub(pattern = "^[^,]*,([^,]*),.*$", replacement = "\\1"))))
check("1% is a subset of 5% (same model, stricter cutoff) in each year",
      {
        a <- fread(file.path(out_dir, "7__NQ_ES__xgb_d2__0.0100.csv"))
        all(a$cutoff >= x[match(a$fold, x$fold)]$cutoff) &&
          all(as.character(a$signal_et) %in% as.character(x$signal_et))
      })

cat("--- a reference off by one win ---\n")
REF_BAD <- copy(REF_OK)
REF_BAD[candidate_id == "7__NQ_ONLY__ranger__0.0200" & fold == "2024", wins := wins + 1L]
res <- suppressMessages(capture.output(r2 <- run_export(REF_BAD)))
check("the export stops", !identical(r2, "ok") && grepl("does NOT reproduce V5", r2))
check("and writes nothing", !dir.exists(out_dir) || length(list.files(out_dir)) == 0L)

# leave a good export behind for test_v5.py to feed through v5_pack.py
invisible(suppressMessages(capture.output(run_export(REF_OK))))

cat(sprintf("\n  %d passed, %d failed\n", PASS, FAIL))
quit(status = if (FAIL) 1L else 0L)
