# ==============================================================================
# NQ + ES DIRECTION SEARCH
# ROLL-SAFE + DAILY-RESET TECHNICALS + WALK-FORWARD V5
#
# BIG-PICTURE GOAL
#   Maximize stable out-of-sample NQ UP/DOWN directional win rate.
#
#   Very low coverage is acceptable IF the apparent edge:
#     1. persists through multiple chronological OOS folds,
#     2. is not concentrated in a few days/weeks,
#     3. beats the same-timestamp directional baseline,
#     4. survives week-block inference,
#     5. is not created by continuous-contract roll discontinuities.
#
#
# IMPORTANT CHANGES VS V4
#
#   1. TECHNICAL INDICATORS RESET AT EACH FUTURES SESSION
#
#      A new futures session begins at 18:00 New York time.
#
#      RSI, MACD, Bollinger Bands, rolling VWAP, EMA, ADX,
#      Donchian channels and relative-volume technicals are restarted
#      from the first 1-minute candle of each new futures session.
#
#      Therefore the beginning of each futures session contains no
#      technical indicators until enough bars have accumulated.
#
#      Since our longest technical lookback is 60 one-minute observations,
#      the fully rich feature set will normally become usable around
#      19:00 ET.
#
#
#   2. SUSPECTED CONTRACT-ROLL DISCONTINUITIES ALSO RESET STATE
#
#      We do NOT back-adjust the continuous futures series.
#      We do NOT winsorize every large return.
#
#      Because instrument_id is unavailable, a deliberately narrow
#      fallback roll detector is used:
#
#        - March / June / September / December
#        - approximately the futures-roll part of the month
#        - around the UTC date-boundary minute where our suspicious
#          discontinuities appeared
#        - sufficiently abnormal NQ/ES price discontinuity
#
#      Every detected roll:
#
#        - starts a new roll segment,
#        - resets all technical indicators,
#        - prevents return/volatility windows from crossing the roll,
#        - invalidates forecast targets crossing the roll,
#        - invalidates an RTH opening gap if previous close and current
#          RTH open belong to different roll segments.
#
#
#   3. REPEATED CHRONOLOGICAL WALK-FORWARD OOS
#
#      2023 test:
#          Train 2017-2021
#          Calibrate confidence cutoff on 2022
#          Test 2023
#
#      2024 test:
#          Train 2018-2022
#          Calibrate on 2023
#          Test 2024
#
#      2025 test:
#          Train 2019-2023
#          Calibrate on 2024
#          Test 2025
#
#      2026 YTD test:
#          Train 2020-2024
#          Calibrate on 2025
#          Test 2026 YTD
#
#      The confidence percentile is NEVER computed on the test year.
#
#
#   4. 2026 IS INCLUDED IN DEVELOPMENT
#
#      We deliberately continue mining 2026.
#
#      Therefore the aggregate V5 ranking should be interpreted as
#      DEVELOPMENT-OOS rather than a pristine study-level confirmation.
#
#
#   5. SELECTION INFERENCE
#
#      Candidate selection no longer uses ordinary iid-binomial lower CI.
#
#      It uses:
#        - repeated chronological OOS folds,
#        - week-block bootstrap,
#        - paired model edge versus training-determined baseline,
#        - temporal breadth,
#        - day-concentration diagnostics,
#        - non-overlapping target-window counts.
#
#
#   6. FEATURE ABLATION
#
#      After the development champion is selected, the same
#      model / horizon / coverage is rerun using:
#
#        NQ_BASE
#        NQ_BASE_PLUS_TECH
#        NQ_BASE_PLUS_SESSION
#        NQ_RICH
#        NQ_ES_RICH
#
#
# LABEL
#
#      At signal time T:
#
#          predict whether NQ close at T+h
#          is above or below NQ close known at T.
#
#      Exact-flat outcome:
#          LOSS in evaluation.
#
#      Binary model training:
#          exact-flat observations excluded.
#
#
# DATA TIMING
#
#      Databento 1-minute timestamp marks START of aggregation interval.
#
#      Therefore:
#
#          bar stamped t
#          becomes fully known at t + 1 minute.
#
# ==============================================================================
#
# NOTE
#
# This script uses:
#
#   data.table
#   lubridate
#   TTR
#   ranger
#   xgboost
#
# No H2O is used.
#
# ==============================================================================



# ==============================================================================
# 0. SETTINGS
# ==============================================================================

SEED <- 1234L

set.seed(SEED)


# ------------------------------------------------------------------------------
# Files
# ------------------------------------------------------------------------------

NQ_NAME <- "NQ_1min_2010-06-07_to_2026-03-13_databento.csv"
ES_NAME <- "ES_1min_2010-06-07_to_2026-03-13_databento.csv"


NQ_FILE <- if (file.exists(NQ_NAME)) {

  normalizePath(NQ_NAME)

} else {

  message("Choose NQ CSV...")
  file.choose()
}


ES_GUESS <- file.path(
  dirname(NQ_FILE),
  ES_NAME
)


ES_FILE <- if (file.exists(ES_GUESS)) {

  ES_GUESS

} else if (file.exists(ES_NAME)) {

  normalizePath(ES_NAME)

} else {

  message("Choose ES CSV...")
  file.choose()
}


OUT <- file.path(
  dirname(NQ_FILE),
  "nq_es_rollsafe_walkforward_v5"
)

dir.create(
  OUT,
  recursive = TRUE,
  showWarnings = FALSE
)



# ------------------------------------------------------------------------------
# Prediction search
# ------------------------------------------------------------------------------

HORIZONS <- c(
  1L,
  3L,
  5L,
  7L,
  10L,
  15L,
  30L,
  60L
)


COVERAGES <- c(
  0.50,
  0.20,
  0.10,
  0.05,
  0.02,
  0.01,
  0.005
)



# ------------------------------------------------------------------------------
# Bootstrap / stability requirements
# ------------------------------------------------------------------------------

BOOT_REPS <- 1000L


# Minimum total OOS selected predictions across ranked folds.
MIN_AGG_N <- 300L


# Greedy count of non-overlapping h-minute prediction windows.
MIN_EFFECTIVE_N <- 200L


# Temporal breadth across FULL calendar-year OOS folds:
# 2023, 2024 and 2025.
MIN_AVG_ACTIVE_WEEKS_FULL <- 40
MIN_MIN_ACTIVE_WEEKS_FULL <- 30


# Prevent a small group of extreme days from dominating the rule.
MAX_TOP5_DAY_SHARE <- 0.35


# Of the three complete OOS years 2023/2024/2025,
# require at least two with WR > 50%.
MIN_FULL_YEARS_OVER_50 <- 2L



# ------------------------------------------------------------------------------
# 2026 treatment
# ------------------------------------------------------------------------------

# TRUE = 2026 YTD contributes to development ranking.
#
# This is what we want now.
#
USE_2026_IN_RANKING <- TRUE



# ------------------------------------------------------------------------------
# Walk-forward folds
# ------------------------------------------------------------------------------

FOLDS <- data.table::data.table(

  fold = c(
    "2023",
    "2024",
    "2025",
    "2026_YTD"
  ),


  train_start = as.Date(c(
    "2017-01-01",
    "2018-01-01",
    "2019-01-01",
    "2020-01-01"
  )),


  train_end = as.Date(c(
    "2022-01-01",
    "2023-01-01",
    "2024-01-01",
    "2025-01-01"
  )),


  cal_start = as.Date(c(
    "2022-01-01",
    "2023-01-01",
    "2024-01-01",
    "2025-01-01"
  )),


  cal_end = as.Date(c(
    "2023-01-01",
    "2024-01-01",
    "2025-01-01",
    "2026-01-01"
  )),


  test_start = as.Date(c(
    "2023-01-01",
    "2024-01-01",
    "2025-01-01",
    "2026-01-01"
  )),


  test_end = as.Date(c(
    "2024-01-01",
    "2025-01-01",
    "2026-01-01",
    "2027-01-01"
  )),


  full_year = c(
    TRUE,
    TRUE,
    TRUE,
    FALSE
  )
)



# ------------------------------------------------------------------------------
# Read warm-up
# ------------------------------------------------------------------------------

READ_START_UTC <- as.POSIXct(
  "2016-10-01 00:00:00",
  tz = "UTC"
)



# ------------------------------------------------------------------------------
# Futures session
# ------------------------------------------------------------------------------

# CME equity-index futures daily maintenance:
# approximately 17:00-18:00 New York time.
#
# We define each new analytical futures session from 18:00 ET.
#
FUTURES_SESSION_OPEN_ET <- 18L * 60L



# ------------------------------------------------------------------------------
# Cash-market session definitions
# ------------------------------------------------------------------------------

ASIA_START_TOKYO <- 9L * 60L

ASIA_END_TOKYO <-
  15L * 60L +
  30L


LONDON_START_LOCAL <- 8L * 60L

LONDON_END_LOCAL <-
  16L * 60L +
  30L


US_RTH_START_ET <-
  9L * 60L +
  30L


US_RTH_END_ET <-
  16L * 60L



# ------------------------------------------------------------------------------
# Fallback roll detector
# ------------------------------------------------------------------------------

# This is deliberately narrow.
#
# We are trying to identify the obvious continuous-contract discontinuities,
# not ordinary large market moves.
#
# Examples previously observed:
#
#   2025-03-20 00:01 UTC:
#       NQ ~ +1.0%
#       ES ~ -0.03%
#
#   2025-09-18 00:01 UTC:
#       NQ ~ +0.96%
#       ES ~ -0.02%
#
#   2024-12-19 00:01 UTC:
#       NQ ~ +1.33%
#       ES ~ +0.03%
#

ROLL_BIG_JUMP <- 0.006

ROLL_SMALL_JUMP <- 0.0025

ROLL_CROSS_DIFF <- 0.004



# ------------------------------------------------------------------------------
# Optional manual roll overrides
# ------------------------------------------------------------------------------

# Example:
#
# MANUAL_ROLL_UTC <- as.POSIXct(
#   c(
#     "2025-03-20 00:01:00",
#     "2025-09-18 00:01:00"
#   ),
#   tz = "UTC"
# )
#
# Default: none.
#

MANUAL_ROLL_UTC <- as.POSIXct(
  character(),
  tz = "UTC"
)


# Exact timestamps that the heuristic incorrectly classified as rolls.
#
MANUAL_IGNORE_ROLL_UTC <- as.POSIXct(
  character(),
  tz = "UTC"
)



# ==============================================================================
# 1. PACKAGES + API CHECK
# ==============================================================================

needed <- c(
  "data.table",
  "lubridate",
  "TTR",
  "ranger",
  "xgboost"
)


missing <- needed[
  !vapply(
    needed,
    requireNamespace,
    logical(1),
    quietly = TRUE
  )
]


if (length(missing) > 0L) {

  stop(
    "Missing package(s): ",
    paste(
      missing,
      collapse = ", "
    ),
    "\nInstall with install.packages()."
  )
}



stopifnot(

  all(
    c(
      "fread",
      "fwrite",
      "setorder",
      "setnames",
      "shift",
      "frollsum",
      "frollmean",
      "fifelse"
    ) %in%
      getNamespaceExports("data.table")
  ),


  all(
    c(
      "with_tz",
      "hour",
      "minute",
      "wday"
    ) %in%
      getNamespaceExports("lubridate")
  ),


  all(
    c(
      "RSI",
      "MACD",
      "BBands",
      "VWAP",
      "EMA",
      "SMA",
      "ADX",
      "DonchianChannel"
    ) %in%
      getNamespaceExports("TTR")
  ),


  "ranger" %in%
    getNamespaceExports("ranger"),


  all(
    c(
      "xgb.DMatrix",
      "xgb.params",
      "xgb.train"
    ) %in%
      getNamespaceExports("xgboost")
  )
)



PACKAGE_VERSIONS <- data.table::data.table(

  package = needed,

  version = vapply(
    needed,
    function(z) {
      as.character(
        utils::packageVersion(z)
      )
    },
    character(1)
  )
)


data.table::fwrite(
  PACKAGE_VERSIONS,
  file.path(
    OUT,
    "00_package_versions.csv"
  )
)



# ==============================================================================
# 2. READ DATA + EXACT NQ/ES ALIGNMENT
# ==============================================================================

read_market <- function(
  file,
  prefix
) {

  x <- data.table::fread(

    file,

    select = c(
      "timestamp",
      "open",
      "high",
      "low",
      "close",
      "volume"
    ),

    colClasses = list(
      character = "timestamp"
    ),

    showProgress = TRUE
  )


  x[
    ,
    ts := as.POSIXct(
      substr(
        timestamp,
        1L,
        19L
      ),
      format = "%Y-%m-%d %H:%M:%S",
      tz = "UTC"
    )
  ]


  if (anyNA(x$ts)) {

    stop(
      prefix,
      ": timestamp parse failure"
    )
  }


  x <- x[
    ts >= READ_START_UTC
  ]


  data.table::setorder(
    x,
    ts
  )


  if (anyDuplicated(x$ts)) {

    stop(
      prefix,
      ": duplicate timestamps"
    )
  }


  data.table::setnames(

    x,

    c(
      "open",
      "high",
      "low",
      "close",
      "volume"
    ),

    paste0(
      prefix,
      c(
        "_open",
        "_high",
        "_low",
        "_close",
        "_volume"
      )
    )
  )


  x[
    ,
    timestamp := NULL
  ]


  x
}



message("Reading NQ...")

NQ <- read_market(
  NQ_FILE,
  "nq"
)


message("Reading ES...")

ES <- read_market(
  ES_FILE,
  "es"
)



ALIGNMENT <- data.table::data.table(

  nq_rows = nrow(NQ),

  es_rows = nrow(ES)
)



# Exact timestamp join.
#
# Never forward-fill one futures market into the other.
#
D <- merge(

  NQ,
  ES,

  by = "ts",

  all = FALSE,

  sort = TRUE
)



ALIGNMENT[
  ,
  `:=`(

    exact_common_rows =
      nrow(D),

    nq_common_fraction =
      nrow(D) / nq_rows,

    es_common_fraction =
      nrow(D) / es_rows
  )
]



data.table::fwrite(

  ALIGNMENT,

  file.path(
    OUT,
    "01_alignment_audit.csv"
  )
)



rm(
  NQ,
  ES
)

invisible(
  gc()
)



D[
  ,
  row_id := .I
]


D[
  ,
  ts_num := as.numeric(ts)
]


D[
  ,
  ts_et :=
    lubridate::with_tz(
      ts,
      "America/New_York"
    )
]



# ==============================================================================
# 3. CLOCKS + FUTURES SESSIONS + ROLL DETECTION
# ==============================================================================

is_nq_open <- function(x) {

  dow <-
    lubridate::wday(
      x,
      week_start = 1L
    )


  m <-
    lubridate::hour(x) * 60L +
    lubridate::minute(x)


  (
    dow %in% 1:4 &
    (
      m < 1020L |
      m >= 1080L
    )
  ) |

  (
    dow == 5L &
    m < 1020L
  ) |

  (
    dow == 7L &
    m >= 1080L
  )
}



# ------------------------------------------------------------------------------
# Signal time
# ------------------------------------------------------------------------------

# Databento bar timestamp = START of 1-minute bar.
#
# Therefore:
#
#   bar stamped 10:14
#
# is completed / knowable at:
#
#   10:15
#

D[
  ,
  signal_ts_num :=
    ts_num + 60
]


D[
  ,
  signal_utc :=
    as.POSIXct(
      signal_ts_num,
      origin = "1970-01-01",
      tz = "UTC"
    )
]


D[
  ,
  signal_et :=
    lubridate::with_tz(
      signal_utc,
      "America/New_York"
    )
]


D[
  ,
  signal_london :=
    lubridate::with_tz(
      signal_utc,
      "Europe/London"
    )
]


D[
  ,
  signal_tokyo :=
    lubridate::with_tz(
      signal_utc,
      "Asia/Tokyo"
    )
]



D[
  ,
  signal_date :=
    as.Date(
      signal_et,
      tz = "America/New_York"
    )
]


D[
  ,
  signal_minute :=
    lubridate::hour(signal_et) * 60L +
    lubridate::minute(signal_et)
]


D[
  ,
  signal_dow :=
    lubridate::wday(
      signal_et,
      week_start = 1L
    )
]



D[
  ,
  london_minute :=
    lubridate::hour(signal_london) * 60L +
    lubridate::minute(signal_london)
]


D[
  ,
  tokyo_minute :=
    lubridate::hour(signal_tokyo) * 60L +
    lubridate::minute(signal_tokyo)
]



# ------------------------------------------------------------------------------
# Session flags
# ------------------------------------------------------------------------------

D[
  ,
  asia_session :=
    as.integer(
      tokyo_minute >=
        ASIA_START_TOKYO &
      tokyo_minute <
        ASIA_END_TOKYO
    )
]


D[
  ,
  london_session :=
    as.integer(
      london_minute >=
        LONDON_START_LOCAL &
      london_minute <
        LONDON_END_LOCAL
    )
]


D[
  ,
  us_rth_session :=
    as.integer(
      signal_minute >=
        US_RTH_START_ET &
      signal_minute <
        US_RTH_END_ET
    )
]


D[
  ,
  london_us_overlap :=
    london_session *
    us_rth_session
]


D[
  ,
  us_last60 :=
    as.integer(
      signal_minute >=
        15L * 60L &
      signal_minute <
        US_RTH_END_ET
    )
]


D[
  ,
  us_last30 :=
    as.integer(
      signal_minute >=
        15L * 60L + 30L &
      signal_minute <
        US_RTH_END_ET
    )
]


D[
  ,
  minutes_to_us_close :=
    data.table::fifelse(

      us_rth_session == 1L,

      US_RTH_END_ET -
        signal_minute,

      0L
    )
]



# ------------------------------------------------------------------------------
# Bar clock
# ------------------------------------------------------------------------------

D[
  ,
  bar_date_et :=
    as.Date(
      ts_et,
      tz = "America/New_York"
    )
]


D[
  ,
  bar_minute_et :=
    lubridate::hour(ts_et) * 60L +
    lubridate::minute(ts_et)
]


D[
  ,
  bar_dow :=
    lubridate::wday(
      ts_et,
      week_start = 1L
    )
]



D[
  ,
  is_us_rth_bar :=

    bar_dow %in% 1:5 &

    bar_minute_et >=
      US_RTH_START_ET &

    bar_minute_et <
      US_RTH_END_ET
]



D[
  ,
  bar_start_open :=
    is_nq_open(ts_et)
]


D[
  ,
  signal_open :=
    is_nq_open(signal_et)
]



# ------------------------------------------------------------------------------
# Futures-session identifier
# ------------------------------------------------------------------------------

# Futures session date:
#
#   Monday 18:00 ET -> Tuesday futures session
#
# Everything from 18:00 through next day's 17:00 belongs to the same
# analytical futures session.
#

D[
  ,
  futures_session_date :=
    as.Date(
      ts_et,
      tz = "America/New_York"
    )
]


D[
  bar_minute_et >=
    FUTURES_SESSION_OPEN_ET,

  futures_session_date :=
    futures_session_date + 1L
]



prev_session_date <-
  data.table::shift(
    D$futures_session_date
  )


D[
  ,
  new_futures_session :=

    is.na(prev_session_date) |

    futures_session_date !=
      prev_session_date
]



# ------------------------------------------------------------------------------
# Raw exact 1-minute returns
# ------------------------------------------------------------------------------

raw_exact_ret1 <- function(
  price,
  tsnum
) {

  old_price <-
    data.table::shift(
      price,
      1L
    )


  old_ts <-
    data.table::shift(
      tsnum,
      1L
    )


  z <-
    rep(
      NA_real_,
      length(price)
    )


  ok <-
    !is.na(old_ts) &
    (
      tsnum -
      old_ts ==
      60
    )


  z[ok] <-
    log(
      price[ok] /
      old_price[ok]
    )


  z
}



D[
  ,
  nq_raw_ret1 :=
    raw_exact_ret1(
      nq_close,
      ts_num
    )
]


D[
  ,
  es_raw_ret1 :=
    raw_exact_ret1(
      es_close,
      ts_num
    )
]



# ------------------------------------------------------------------------------
# Conservative fallback roll detector
# ------------------------------------------------------------------------------

utc_month <-
  as.integer(
    format(
      D$ts,
      "%m",
      tz = "UTC"
    )
  )


utc_day <-
  as.integer(
    format(
      D$ts,
      "%d",
      tz = "UTC"
    )
  )


utc_hour <-
  as.integer(
    format(
      D$ts,
      "%H",
      tz = "UTC"
    )
  )


utc_minute <-
  as.integer(
    format(
      D$ts,
      "%M",
      tz = "UTC"
    )
  )



D[
  ,
  quarter_roll_window :=

    utc_month %in%
      c(
        3L,
        6L,
        9L,
        12L
      ) &

    utc_day >= 14L &

    utc_day <= 22L &

    utc_hour == 0L &

    utc_minute <= 2L
]



D[
  ,
  raw_cross_diff :=
    abs(
      nq_raw_ret1 -
      es_raw_ret1
    )
]



D[
  ,
  roll_heuristic :=

    quarter_roll_window &

    is.finite(nq_raw_ret1) &

    is.finite(es_raw_ret1) &

    (

      pmax(
        abs(nq_raw_ret1),
        abs(es_raw_ret1)
      ) >=
        ROLL_BIG_JUMP

      |

      (

        pmax(
          abs(nq_raw_ret1),
          abs(es_raw_ret1)
        ) >=
          ROLL_SMALL_JUMP

        &

        raw_cross_diff >=
          ROLL_CROSS_DIFF
      )
    )
]



D[
  ,
  manual_roll :=
    ts %in%
      MANUAL_ROLL_UTC
]



D[
  ,
  roll_break :=
    roll_heuristic |
    manual_roll
]



if (
  length(
    MANUAL_IGNORE_ROLL_UTC
  ) > 0L
) {

  D[
    ts %in%
      MANUAL_IGNORE_ROLL_UTC,

    roll_break := FALSE
  ]
}



# ------------------------------------------------------------------------------
# Roll segment
# ------------------------------------------------------------------------------

# Changes ONLY when suspected continuous contract changes.
#
D[
  ,
  roll_segment :=
    cumsum(
      roll_break
    )
]



# ------------------------------------------------------------------------------
# Technical / state segment
# ------------------------------------------------------------------------------

# We reset technical state whenever:
#
#   1. new futures session starts at 18:00 ET,
#   2. suspected contract roll occurs,
#   3. an unexpected missing-minute gap occurs.
#

prev_ts_num <-
  data.table::shift(
    D$ts_num
  )


D[
  ,
  unexpected_time_gap :=

    is.na(prev_ts_num) |

    (
      ts_num -
      prev_ts_num !=
      60
    )
]



D[
  ,
  state_break :=

    new_futures_session |

    roll_break |

    unexpected_time_gap
]



D[
  ,
  state_segment :=
    cumsum(
      state_break
    )
]



# ------------------------------------------------------------------------------
# Roll audit
# ------------------------------------------------------------------------------

ROLL_EVENTS <- D[
  roll_break == TRUE,
  .(
    ts,
    signal_et,
    futures_session_date,

    nq_raw_ret1,
    es_raw_ret1,
    raw_cross_diff,

    roll_heuristic,
    manual_roll,

    roll_segment
  )
]



data.table::fwrite(

  ROLL_EVENTS,

  file.path(
    OUT,
    "02_detected_roll_events.csv"
  )
)



ROLL_SUMMARY <-
  data.table::data.table(

    detected_roll_events =
      nrow(ROLL_EVENTS),

    detector =
      "quarterly UTC-boundary discontinuity heuristic",

    big_jump_threshold =
      ROLL_BIG_JUMP,

    small_jump_threshold =
      ROLL_SMALL_JUMP,

    cross_difference_threshold =
      ROLL_CROSS_DIFF
  )



data.table::fwrite(

  ROLL_SUMMARY,

  file.path(
    OUT,
    "03_roll_detection_summary.csv"
  )
)



rm(
  prev_session_date,
  prev_ts_num,
  utc_month,
  utc_day,
  utc_hour,
  utc_minute
)



# ==============================================================================
# 4. ROLL-SAFE + SESSION-SAFE RETURNS / VOLATILITY
# ==============================================================================

exact_return <- function(
  price,
  tsnum,
  segment,
  k
) {

  old_price <-
    data.table::shift(
      price,
      k
    )


  old_ts <-
    data.table::shift(
      tsnum,
      k
    )


  old_segment <-
    data.table::shift(
      segment,
      k
    )


  z <-
    rep(
      NA_real_,
      length(price)
    )


  ok <-

    !is.na(old_ts) &

    !is.na(old_segment) &

    (
      tsnum -
      old_ts ==
      60 * k
    ) &

    (
      segment ==
      old_segment
    )


  z[ok] <-
    log(
      price[ok] /
      old_price[ok]
    )


  z
}



rolling_rv <- function(
  ret1,
  tsnum,
  segment,
  k
) {

  z <-
    sqrt(
      data.table::frollsum(

        ret1^2,

        n = k,

        align = "right",

        fill = NA_real_
      )
    )


  old_ts <-
    data.table::shift(
      tsnum,
      k - 1L
    )


  old_segment <-
    data.table::shift(
      segment,
      k - 1L
    )


  ok <-

    !is.na(old_ts) &

    !is.na(old_segment) &

    (
      tsnum -
      old_ts ==
      60 * (k - 1L)
    ) &

    (
      segment ==
      old_segment
    )


  z[!ok] <-
    NA_real_


  z
}



rolling_rs <- function(
  o,
  h,
  l,
  c,
  tsnum,
  segment,
  k
) {

  rs_term <-

    log(h / c) *
    log(h / o) +

    log(l / c) *
    log(l / o)


  z <-
    sqrt(
      pmax(

        data.table::frollsum(

          rs_term,

          n = k,

          align = "right",

          fill = NA_real_

        ) / k,

        0
      )
    )


  old_ts <-
    data.table::shift(
      tsnum,
      k - 1L
    )


  old_segment <-
    data.table::shift(
      segment,
      k - 1L
    )


  ok <-

    !is.na(old_ts) &

    !is.na(old_segment) &

    (
      tsnum -
      old_ts ==
      60 * (k - 1L)
    ) &

    (
      segment ==
      old_segment
    )


  z[!ok] <-
    NA_real_


  z
}



# ------------------------------------------------------------------------------
# Current bar geometry
# ------------------------------------------------------------------------------

D[
  ,
  nq_bar_ret :=
    log(
      nq_close /
      nq_open
    )
]


D[
  ,
  nq_range :=
    (
      nq_high -
      nq_low
    ) /
    nq_close
]


D[
  ,
  nq_close_loc :=
    data.table::fifelse(

      nq_high >
        nq_low,

      (
        nq_close -
        nq_low
      ) /
      (
        nq_high -
        nq_low
      ),

      0.5
    )
]



D[
  ,
  es_bar_ret :=
    log(
      es_close /
      es_open
    )
]


D[
  ,
  es_range :=
    (
      es_high -
      es_low
    ) /
    es_close
]


D[
  ,
  es_close_loc :=
    data.table::fifelse(

      es_high >
        es_low,

      (
        es_close -
        es_low
      ) /
      (
        es_high -
        es_low
      ),

      0.5
    )
]



# ------------------------------------------------------------------------------
# Backward returns
# ------------------------------------------------------------------------------

for (
  k in
  c(
    1L,
    2L,
    5L,
    15L,
    30L,
    60L
  )
) {

  D[
    ,
    (paste0(
      "nq_ret",
      k
    )) :=
      exact_return(
        nq_close,
        ts_num,
        state_segment,
        k
      )
  ]


  D[
    ,
    (paste0(
      "es_ret",
      k
    )) :=
      exact_return(
        es_close,
        ts_num,
        state_segment,
        k
      )
  ]
}



# ------------------------------------------------------------------------------
# Realized volatility
# ------------------------------------------------------------------------------

for (
  k in
  c(
    5L,
    15L,
    60L
  )
) {

  D[
    ,
    (paste0(
      "nq_rv",
      k
    )) :=
      rolling_rv(
        nq_ret1,
        ts_num,
        state_segment,
        k
      )
  ]


  D[
    ,
    (paste0(
      "es_rv",
      k
    )) :=
      rolling_rv(
        es_ret1,
        ts_num,
        state_segment,
        k
      )
  ]
}



# ------------------------------------------------------------------------------
# Rogers-Satchell volatility
# ------------------------------------------------------------------------------

for (
  k in
  c(
    15L,
    60L
  )
) {

  D[
    ,
    (paste0(
      "nq_rs",
      k
    )) :=
      rolling_rs(
        nq_open,
        nq_high,
        nq_low,
        nq_close,
        ts_num,
        state_segment,
        k
      )
  ]


  D[
    ,
    (paste0(
      "es_rs",
      k
    )) :=
      rolling_rs(
        es_open,
        es_high,
        es_low,
        es_close,
        ts_num,
        state_segment,
        k
      )
  ]
}



# ------------------------------------------------------------------------------
# Volatility regime ratios
# ------------------------------------------------------------------------------

D[
  ,
  nq_rv5_over_60 :=
    nq_rv5 /
    nq_rv60
]


D[
  ,
  nq_rs15_over_60 :=
    nq_rs15 /
    nq_rs60
]


D[
  ,
  es_rv5_over_60 :=
    es_rv5 /
    es_rv60
]


D[
  ,
  es_rs15_over_60 :=
    es_rs15 /
    es_rs60
]



# ==============================================================================
# 5. TECHNICAL INDICATORS
#
#    RESET EACH FUTURES SESSION + EACH ROLL + EACH MISSING-MINUTE GAP
#
#    TECHNICAL CALCULATIONS THEMSELVES COME FROM TTR.
# ==============================================================================

add_ttr_features_segmented <- function(
  D,
  prefix
) {

  output_columns <- c(

    paste0(
      prefix,
      "_rsi14"
    ),

    paste0(
      prefix,
      "_macd"
    ),

    paste0(
      prefix,
      "_macd_signal"
    ),

    paste0(
      prefix,
      "_macd_hist"
    ),

    paste0(
      prefix,
      "_bb_pctB"
    ),

    paste0(
      prefix,
      "_bb_width"
    ),

    paste0(
      prefix,
      "_vwap20_dist"
    ),

    paste0(
      prefix,
      "_ema20_dist"
    ),

    paste0(
      prefix,
      "_ema60_dist"
    ),

    paste0(
      prefix,
      "_ema20_60_spread"
    ),

    paste0(
      prefix,
      "_adx14"
    ),

    paste0(
      prefix,
      "_di_spread14"
    ),

    paste0(
      prefix,
      "_donchian20_pos"
    ),

    paste0(
      prefix,
      "_breakout20_up"
    ),

    paste0(
      prefix,
      "_breakout20_down"
    ),

    paste0(
      prefix,
      "_vol_rel15"
    ),

    paste0(
      prefix,
      "_vol_rel60"
    )
  )



  for (
    nm in
    output_columns
  ) {

    D[
      ,
      (nm) :=
        NA_real_
    ]
  }



  close_all <-
    D[[
      paste0(
        prefix,
        "_close"
      )
    ]]


  high_all <-
    D[[
      paste0(
        prefix,
        "_high"
      )
    ]]


  low_all <-
    D[[
      paste0(
        prefix,
        "_low"
      )
    ]]


  volume_all <-
    D[[
      paste0(
        prefix,
        "_volume"
      )
    ]]



  all_segments <-
    unique(
      D$state_segment
    )



  for (
    seg in
    all_segments
  ) {

    idx <-
      which(
        D$state_segment ==
          seg
      )


    # Need enough observations for 60-period indicators.
    if (
      length(idx) <
      70L
    ) {

      next
    }



    close <-
      close_all[idx]


    high <-
      high_all[idx]


    low <-
      low_all[idx]


    volume <-
      volume_all[idx]



    HLC <-
      cbind(
        High = high,
        Low = low,
        Close = close
      )


    HL <-
      cbind(
        High = high,
        Low = low
      )



    # --------------------------------------------------------------------------
    # RSI 14
    # --------------------------------------------------------------------------

    rsi <-
      as.numeric(
        TTR::RSI(
          close,
          n = 14
        )
      )



    # --------------------------------------------------------------------------
    # MACD 12 / 26 / 9
    # --------------------------------------------------------------------------

    macd <-
      TTR::MACD(

        close,

        nFast = 12,

        nSlow = 26,

        nSig = 9,

        percent = TRUE
      )



    # --------------------------------------------------------------------------
    # Bollinger Bands 20 / 2
    # --------------------------------------------------------------------------

    bb <-
      TTR::BBands(

        HLC,

        n = 20,

        sd = 2
      )



    # --------------------------------------------------------------------------
    # Rolling VWAP 20
    # --------------------------------------------------------------------------

    vwap20 <-
      as.numeric(
        TTR::VWAP(
          close,
          volume,
          n = 20
        )
      )



    # --------------------------------------------------------------------------
    # EMA 20 / EMA 60
    # --------------------------------------------------------------------------

    ema20 <-
      as.numeric(
        TTR::EMA(
          close,
          n = 20
        )
      )


    ema60 <-
      as.numeric(
        TTR::EMA(
          close,
          n = 60
        )
      )



    # --------------------------------------------------------------------------
    # ADX 14
    # --------------------------------------------------------------------------

    adx <-
      TTR::ADX(
        HLC,
        n = 14
      )



    # --------------------------------------------------------------------------
    # Donchian channel
    #
    # include.lag = TRUE means current close is compared with PRIOR range.
    # --------------------------------------------------------------------------

    dc <-
      TTR::DonchianChannel(

        HL,

        n = 20,

        include.lag = TRUE
      )


    dc_high <-
      as.numeric(
        dc[
          ,
          "high"
        ]
      )


    dc_low <-
      as.numeric(
        dc[
          ,
          "low"
        ]
      )



    dc_pos <-
      data.table::fifelse(

        dc_high >
          dc_low,

        (
          close -
          dc_low
        ) /
        (
          dc_high -
          dc_low
        ),

        0.5
      )



    # --------------------------------------------------------------------------
    # Relative volume
    # --------------------------------------------------------------------------

    vol_sma15 <-
      as.numeric(
        TTR::SMA(
          volume,
          n = 15
        )
      )


    vol_sma60 <-
      as.numeric(
        TTR::SMA(
          volume,
          n = 60
        )
      )



    values <- list(

      rsi,

      as.numeric(
        macd[
          ,
          "macd"
        ]
      ),

      as.numeric(
        macd[
          ,
          "signal"
        ]
      ),

      as.numeric(
        macd[
          ,
          "macd"
        ] -
        macd[
          ,
          "signal"
        ]
      ),

      as.numeric(
        bb[
          ,
          "pctB"
        ]
      ),

      as.numeric(
        (
          bb[
            ,
            "up"
          ] -
          bb[
            ,
            "dn"
          ]
        ) /
        bb[
          ,
          "mavg"
        ]
      ),

      close /
        vwap20 -
        1,

      close /
        ema20 -
        1,

      close /
        ema60 -
        1,

      ema20 /
        ema60 -
        1,

      as.numeric(
        adx[
          ,
          "ADX"
        ]
      ),

      as.numeric(
        adx[
          ,
          "DIp"
        ] -
        adx[
          ,
          "DIn"
        ]
      ),

      dc_pos,

      as.numeric(
        close >
          dc_high
      ),

      as.numeric(
        close <
          dc_low
      ),

      volume /
        vol_sma15,

      volume /
        vol_sma60
    )



    for (
      j in
      seq_along(
        output_columns
      )
    ) {

      data.table::set(

        D,

        i = idx,

        j =
          output_columns[j],

        value =
          values[[j]]
      )
    }
  }



  invisible(
    NULL
  )
}



message(
  "Calculating session-reset NQ technicals..."
)

add_ttr_features_segmented(
  D,
  "nq"
)



message(
  "Calculating session-reset ES technicals..."
)

add_ttr_features_segmented(
  D,
  "es"
)



# ==============================================================================
# 6. US RTH SESSION-TO-DATE STATE
# ==============================================================================

D[
  ,
  `:=`(

    nq_rth_to_now = 0,

    es_rth_to_now = 0,

    nq_rth_vwap_dist = 0,

    es_rth_vwap_dist = 0,

    nq_rth_position = 0,

    es_rth_position = 0
  )
]



# ------------------------------------------------------------------------------
# Session return to now
# ------------------------------------------------------------------------------

D[
  is_us_rth_bar == TRUE,

  nq_rth_to_now :=
    log(
      nq_close /
      nq_open[1L]
    ),

  by = .(
    bar_date_et,
    roll_segment
  )
]



D[
  is_us_rth_bar == TRUE,

  es_rth_to_now :=
    log(
      es_close /
      es_open[1L]
    ),

  by = .(
    bar_date_et,
    roll_segment
  )
]



# ------------------------------------------------------------------------------
# True reset-at-09:30 session VWAP
# ------------------------------------------------------------------------------

D[
  is_us_rth_bar == TRUE,

  nq_rth_vwap_dist := {

    typical <-
      (
        nq_high +
        nq_low +
        nq_close
      ) /
      3


    svwap <-
      cumsum(
        typical *
        nq_volume
      ) /
      cumsum(
        nq_volume
      )


    nq_close /
      svwap -
      1

  },

  by = .(
    bar_date_et,
    roll_segment
  )
]



D[
  is_us_rth_bar == TRUE,

  es_rth_vwap_dist := {

    typical <-
      (
        es_high +
        es_low +
        es_close
      ) /
      3


    svwap <-
      cumsum(
        typical *
        es_volume
      ) /
      cumsum(
        es_volume
      )


    es_close /
      svwap -
      1

  },

  by = .(
    bar_date_et,
    roll_segment
  )
]



# ------------------------------------------------------------------------------
# Position within RTH range so far
# ------------------------------------------------------------------------------

D[
  is_us_rth_bar == TRUE,

  nq_rth_position := {

    hh <-
      cummax(
        nq_high
      )


    ll <-
      cummin(
        nq_low
      )


    ifelse(

      hh >
        ll,

      (
        nq_close -
        ll
      ) /
      (
        hh -
        ll
      ),

      0.5
    )

  },

  by = .(
    bar_date_et,
    roll_segment
  )
]



D[
  is_us_rth_bar == TRUE,

  es_rth_position := {

    hh <-
      cummax(
        es_high
      )


    ll <-
      cummin(
        es_low
      )


    ifelse(

      hh >
        ll,

      (
        es_close -
        ll
      ) /
      (
        hh -
        ll
      ),

      0.5
    )

  },

  by = .(
    bar_date_et,
    roll_segment
  )
]



# ==============================================================================
# 7. RTH GAP + FIRST 30 MINUTES + LAST COMPLETED RTH
# ==============================================================================

RTH_DAILY <- D[

  is_us_rth_bar == TRUE,

  .(

    rth_open_minute =
      bar_minute_et[1L],

    rth_last_minute =
      bar_minute_et[.N],

    rth_last_bar_ts_num =
      ts_num[.N],

    rth_bar_n =
      .N,


    rth_open_roll_segment =
      roll_segment[1L],

    rth_close_roll_segment =
      roll_segment[.N],


    nq_rth_open =
      nq_open[1L],

    nq_rth_close =
      nq_close[.N],

    nq_rth_high =
      max(
        nq_high,
        na.rm = TRUE
      ),

    nq_rth_low =
      min(
        nq_low,
        na.rm = TRUE
      ),


    es_rth_open =
      es_open[1L],

    es_rth_close =
      es_close[.N],

    es_rth_high =
      max(
        es_high,
        na.rm = TRUE
      ),

    es_rth_low =
      min(
        es_low,
        na.rm = TRUE
      ),


    first30_n =
      sum(
        bar_minute_et >=
          US_RTH_START_ET &
        bar_minute_et <
          10L * 60L
      ),


    first30_roll_segments =
      data.table::uniqueN(

        roll_segment[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]
      ),


    nq_first30_close = {

      ii <-
        match(
          10L * 60L - 1L,
          bar_minute_et
        )


      if (
        is.na(ii)
      ) {

        NA_real_

      } else {

        nq_close[ii]
      }
    },


    es_first30_close = {

      ii <-
        match(
          10L * 60L - 1L,
          bar_minute_et
        )


      if (
        is.na(ii)
      ) {

        NA_real_

      } else {

        es_close[ii]
      }
    },


    nq_first30_high = {

      z <-
        nq_high[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]


      if (
        length(z)
      ) {

        max(
          z,
          na.rm = TRUE
        )

      } else {

        NA_real_
      }
    },


    nq_first30_low = {

      z <-
        nq_low[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]


      if (
        length(z)
      ) {

        min(
          z,
          na.rm = TRUE
        )

      } else {

        NA_real_
      }
    },


    nq_first30_volume = {

      z <-
        nq_volume[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]


      if (
        length(z)
      ) {

        sum(
          z,
          na.rm = TRUE
        )

      } else {

        NA_real_
      }
    },


    es_first30_high = {

      z <-
        es_high[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]


      if (
        length(z)
      ) {

        max(
          z,
          na.rm = TRUE
        )

      } else {

        NA_real_
      }
    },


    es_first30_low = {

      z <-
        es_low[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]


      if (
        length(z)
      ) {

        min(
          z,
          na.rm = TRUE
        )

      } else {

        NA_real_
      }
    },


    es_first30_volume = {

      z <-
        es_volume[
          bar_minute_et >=
            US_RTH_START_ET &
          bar_minute_et <
            10L * 60L
        ]


      if (
        length(z)
      ) {

        sum(
          z,
          na.rm = TRUE
        )

      } else {

        NA_real_
      }
    }
  ),

  by = .(
    rth_date =
      bar_date_et
  )
]



data.table::setorder(
  RTH_DAILY,
  rth_date
)



# ------------------------------------------------------------------------------
# Validate true 09:30 open
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  rth_open_valid :=

    rth_open_minute ==
      US_RTH_START_ET &

    rth_open_roll_segment ==
      rth_close_roll_segment
]



RTH_DAILY[

  rth_open_valid ==
    FALSE,

  `:=`(

    nq_rth_open =
      NA_real_,

    es_rth_open =
      NA_real_
  )
]



# ------------------------------------------------------------------------------
# Validate complete 09:30-09:59 opening block
# ------------------------------------------------------------------------------

RTH_DAILY[

  first30_n !=
    30L |

  first30_roll_segments !=
    1L |

  rth_open_valid ==
    FALSE,

  `:=`(

    nq_first30_close =
      NA_real_,

    es_first30_close =
      NA_real_,

    nq_first30_high =
      NA_real_,

    nq_first30_low =
      NA_real_,

    nq_first30_volume =
      NA_real_,

    es_first30_high =
      NA_real_,

    es_first30_low =
      NA_real_,

    es_first30_volume =
      NA_real_
  )
]



# ------------------------------------------------------------------------------
# Previous RTH close
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  nq_prev_rth_close :=
    data.table::shift(
      nq_rth_close
    )
]


RTH_DAILY[
  ,
  es_prev_rth_close :=
    data.table::shift(
      es_rth_close
    )
]


RTH_DAILY[
  ,
  prev_rth_close_roll_segment :=
    data.table::shift(
      rth_close_roll_segment
    )
]



# ------------------------------------------------------------------------------
# Today's open must belong to same contract regime as previous RTH close
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  same_contract_gap :=

    !is.na(
      prev_rth_close_roll_segment
    ) &

    rth_open_roll_segment ==
      prev_rth_close_roll_segment
]



# ------------------------------------------------------------------------------
# RTH opening gap
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  nq_rth_gap :=
    data.table::fifelse(

      same_contract_gap,

      log(
        nq_rth_open /
        nq_prev_rth_close
      ),

      NA_real_
    )
]



RTH_DAILY[
  ,
  es_rth_gap :=
    data.table::fifelse(

      same_contract_gap,

      log(
        es_rth_open /
        es_prev_rth_close
      ),

      NA_real_
    )
]



# ------------------------------------------------------------------------------
# First 30 minutes
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  nq_open30_ret :=
    log(
      nq_first30_close /
      nq_rth_open
    )
]


RTH_DAILY[
  ,
  es_open30_ret :=
    log(
      es_first30_close /
      es_rth_open
    )
]



RTH_DAILY[
  ,
  nq_open30_green :=
    as.integer(
      nq_open30_ret >
        0
    )
]


RTH_DAILY[
  ,
  es_open30_green :=
    as.integer(
      es_open30_ret >
        0
    )
]



RTH_DAILY[
  ,
  nq_open30_range :=
    (
      nq_first30_high -
      nq_first30_low
    ) /
    nq_rth_open
]


RTH_DAILY[
  ,
  es_open30_range :=
    (
      es_first30_high -
      es_first30_low
    ) /
    es_rth_open
]



# ------------------------------------------------------------------------------
# Gao-style previous RTH close -> 10:00
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  nq_prevclose_to_1000 :=
    data.table::fifelse(

      same_contract_gap,

      log(
        nq_first30_close /
        nq_prev_rth_close
      ),

      NA_real_
    )
]



RTH_DAILY[
  ,
  es_prevclose_to_1000 :=
    data.table::fifelse(

      same_contract_gap,

      log(
        es_first30_close /
        es_prev_rth_close
      ),

      NA_real_
    )
]



# ------------------------------------------------------------------------------
# Opening 30-minute relative volume
#
# Current opening volume / mean of previous 20 RTH opening windows.
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  nq_open30_vol_avg20_prior :=
    data.table::shift(

      data.table::frollmean(

        nq_first30_volume,

        n = 20L,

        align = "right",

        fill = NA_real_,

        na.rm = FALSE
      ),

      1L
    )
]



RTH_DAILY[
  ,
  es_open30_vol_avg20_prior :=
    data.table::shift(

      data.table::frollmean(

        es_first30_volume,

        n = 20L,

        align = "right",

        fill = NA_real_,

        na.rm = FALSE
      ),

      1L
    )
]



RTH_DAILY[
  ,
  nq_open30_vol_rel20 :=
    nq_first30_volume /
    nq_open30_vol_avg20_prior
]


RTH_DAILY[
  ,
  es_open30_vol_rel20 :=
    es_first30_volume /
    es_open30_vol_avg20_prior
]



# ------------------------------------------------------------------------------
# Attach current calendar day's RTH variables
# ------------------------------------------------------------------------------

TODAY_RTH_FEATURES <- RTH_DAILY[
  ,
  .(

    signal_date =
      rth_date,

    nq_rth_gap,
    es_rth_gap,

    nq_open30_ret,
    nq_open30_green,
    nq_open30_range,
    nq_open30_vol_rel20,
    nq_prevclose_to_1000,

    es_open30_ret,
    es_open30_green,
    es_open30_range,
    es_open30_vol_rel20,
    es_prevclose_to_1000
  )
]



D <- merge(

  D,

  TODAY_RTH_FEATURES,

  by = "signal_date",

  all.x = TRUE,

  sort = FALSE
)



data.table::setorder(
  D,
  ts
)


D[
  ,
  row_id := .I
]



# ------------------------------------------------------------------------------
# Most recently COMPLETED RTH state
# ------------------------------------------------------------------------------

RTH_DAILY[
  ,
  rth_available_ts_num :=
    rth_last_bar_ts_num +
    60
]



RTH_DAILY[
  ,
  nq_completed_rth_ret :=
    data.table::fifelse(

      rth_open_roll_segment ==
        rth_close_roll_segment &

      is.finite(
        nq_rth_open
      ),

      log(
        nq_rth_close /
        nq_rth_open
      ),

      NA_real_
    )
]



RTH_DAILY[
  ,
  es_completed_rth_ret :=
    data.table::fifelse(

      rth_open_roll_segment ==
        rth_close_roll_segment &

      is.finite(
        es_rth_open
      ),

      log(
        es_rth_close /
        es_rth_open
      ),

      NA_real_
    )
]



RTH_DAILY[
  ,
  nq_completed_rth_range :=
    data.table::fifelse(

      is.finite(
        nq_rth_open
      ),

      (
        nq_rth_high -
        nq_rth_low
      ) /
      nq_rth_open,

      NA_real_
    )
]



RTH_DAILY[
  ,
  es_completed_rth_range :=
    data.table::fifelse(

      is.finite(
        es_rth_open
      ),

      (
        es_rth_high -
        es_rth_low
      ) /
      es_rth_open,

      NA_real_
    )
]



last_rth_idx <-
  findInterval(

    D$signal_ts_num,

    RTH_DAILY$rth_available_ts_num
  )



D[
  ,
  nq_last_rth_ret :=
    NA_real_
]


D[
  ,
  es_last_rth_ret :=
    NA_real_
]


D[
  ,
  nq_last_rth_range :=
    NA_real_
]


D[
  ,
  es_last_rth_range :=
    NA_real_
]



has_last_rth <-
  last_rth_idx >
  0L



D[
  has_last_rth == TRUE,

  nq_last_rth_ret :=
    RTH_DAILY$nq_completed_rth_ret[
      last_rth_idx[
        has_last_rth
      ]
    ]
]



D[
  has_last_rth == TRUE,

  es_last_rth_ret :=
    RTH_DAILY$es_completed_rth_ret[
      last_rth_idx[
        has_last_rth
      ]
    ]
]



D[
  has_last_rth == TRUE,

  nq_last_rth_range :=
    RTH_DAILY$nq_completed_rth_range[
      last_rth_idx[
        has_last_rth
      ]
    ]
]



D[
  has_last_rth == TRUE,

  es_last_rth_range :=
    RTH_DAILY$es_completed_rth_range[
      last_rth_idx[
        has_last_rth
      ]
    ]
]



D[
  ,
  last_rth_known :=
    as.integer(

      is.finite(
        nq_last_rth_ret
      ) &

      is.finite(
        es_last_rth_ret
      )
    )
]



# ------------------------------------------------------------------------------
# Availability masks
# ------------------------------------------------------------------------------

D[
  ,
  rth_gap_known :=
    as.integer(

      is.finite(
        nq_rth_gap
      ) &

      is.finite(
        es_rth_gap
      ) &

      signal_minute >=
        (
          US_RTH_START_ET +
          1L
        )
    )
]



D[
  ,
  opening30_known :=
    as.integer(

      is.finite(
        nq_open30_ret
      ) &

      is.finite(
        es_open30_ret
      ) &

      signal_minute >=
        10L * 60L
    )
]



last_rth_cols <- c(

  "nq_last_rth_ret",
  "nq_last_rth_range",

  "es_last_rth_ret",
  "es_last_rth_range"
)



gap_cols <- c(

  "nq_rth_gap",

  "es_rth_gap"
)



open30_cols <- c(

  "nq_open30_ret",
  "nq_open30_green",
  "nq_open30_range",
  "nq_open30_vol_rel20",
  "nq_prevclose_to_1000",

  "es_open30_ret",
  "es_open30_green",
  "es_open30_range",
  "es_open30_vol_rel20",
  "es_prevclose_to_1000"
)



for (
  v in
  last_rth_cols
) {

  D[
    last_rth_known == 0L |
    !is.finite(
      get(v)
    ),

    (v) := 0
  ]
}



for (
  v in
  gap_cols
) {

  D[
    rth_gap_known == 0L |
    !is.finite(
      get(v)
    ),

    (v) := 0
  ]
}



for (
  v in
  open30_cols
) {

  D[
    opening30_known == 0L |
    !is.finite(
      get(v)
    ),

    (v) := 0
  ]
}



# ------------------------------------------------------------------------------
# Cross-market opening variables
# ------------------------------------------------------------------------------

D[
  ,
  nq_minus_es_gap :=
    nq_rth_gap -
    es_rth_gap
]


D[
  ,
  nq_minus_es_open30 :=
    nq_open30_ret -
    es_open30_ret
]


D[
  ,
  open30_disagree :=
    as.integer(

      opening30_known ==
        1L &

      sign(
        nq_open30_ret
      ) !=
      sign(
        es_open30_ret
      )
    )
]



# ==============================================================================
# 8. OTHER CROSS-MARKET + CALENDAR FEATURES
# ==============================================================================

# ------------------------------------------------------------------------------
# NQ minus ES relative returns
# ------------------------------------------------------------------------------

for (
  k in
  c(
    1L,
    5L,
    15L,
    60L
  )
) {

  nq_col <-
    paste0(
      "nq_ret",
      k
    )


  es_col <-
    paste0(
      "es_ret",
      k
    )


  D[
    ,
    (paste0(
      "nq_minus_es_",
      k
    )) :=
      get(nq_col) -
      get(es_col)
  ]
}



# ------------------------------------------------------------------------------
# NQ / ES directional disagreement
# ------------------------------------------------------------------------------

for (
  k in
  c(
    1L,
    5L,
    15L
  )
) {

  nq_col <-
    paste0(
      "nq_ret",
      k
    )


  es_col <-
    paste0(
      "es_ret",
      k
    )


  D[
    ,
    (paste0(
      "disagree_",
      k
    )) :=
      as.integer(

        sign(
          get(nq_col)
        ) !=

        sign(
          get(es_col)
        )
      )
  ]
}



# ------------------------------------------------------------------------------
# Time of day
# ------------------------------------------------------------------------------

D[
  ,
  tod_sin :=
    sin(
      2 *
      pi *
      signal_minute /
      1440
    )
]


D[
  ,
  tod_cos :=
    cos(
      2 *
      pi *
      signal_minute /
      1440
    )
]



# ------------------------------------------------------------------------------
# Day-of-week dummies
#
# Monday is reference.
# ------------------------------------------------------------------------------

for (
  dd in
  c(
    2L,
    3L,
    4L,
    5L,
    7L
  )
) {

  D[
    ,
    (paste0(
      "dow_",
      dd
    )) :=
      as.integer(
        signal_dow ==
          dd
      )
  ]
}



# ------------------------------------------------------------------------------
# Seasons
#
# Winter is reference.
# ------------------------------------------------------------------------------

month_num <-
  as.integer(
    format(
      D$signal_date,
      "%m"
    )
  )



D[
  ,
  season :=
    data.table::fifelse(

      month_num %in%
        c(
          12L,
          1L,
          2L
        ),

      "winter",

      data.table::fifelse(

        month_num %in%
          3:5,

        "spring",

        data.table::fifelse(

          month_num %in%
            6:8,

          "summer",

          "autumn"
        )
      )
    )
]



D[
  ,
  season_spring :=
    as.integer(
      season ==
        "spring"
    )
]


D[
  ,
  season_summer :=
    as.integer(
      season ==
        "summer"
    )
]


D[
  ,
  season_autumn :=
    as.integer(
      season ==
        "autumn"
    )
]



rm(
  month_num
)



# ==============================================================================
# 9. FEATURE SETS + ABLATION GROUPS
# ==============================================================================

# ------------------------------------------------------------------------------
# NQ technical indicators
# ------------------------------------------------------------------------------

NQ_TECH <- c(

  "nq_rsi14",

  "nq_macd",
  "nq_macd_signal",
  "nq_macd_hist",

  "nq_bb_pctB",
  "nq_bb_width",

  "nq_vwap20_dist",

  "nq_ema20_dist",
  "nq_ema60_dist",
  "nq_ema20_60_spread",

  "nq_adx14",
  "nq_di_spread14",

  "nq_donchian20_pos",
  "nq_breakout20_up",
  "nq_breakout20_down",

  "nq_vol_rel15",
  "nq_vol_rel60"
)



# ------------------------------------------------------------------------------
# ES technical indicators
# ------------------------------------------------------------------------------

ES_TECH <- c(

  "es_rsi14",

  "es_macd",
  "es_macd_signal",
  "es_macd_hist",

  "es_bb_pctB",
  "es_bb_width",

  "es_vwap20_dist",

  "es_ema20_dist",
  "es_ema60_dist",
  "es_ema20_60_spread",

  "es_adx14",
  "es_di_spread14",

  "es_donchian20_pos",
  "es_breakout20_up",
  "es_breakout20_down",

  "es_vol_rel15",
  "es_vol_rel60"
)



# ------------------------------------------------------------------------------
# Session flags
# ------------------------------------------------------------------------------

COMMON_SESSION <- c(

  "asia_session",

  "london_session",

  "us_rth_session",

  "london_us_overlap",

  "us_last60",

  "us_last30",

  "minutes_to_us_close",

  "last_rth_known",

  "rth_gap_known",

  "opening30_known"
)



# ------------------------------------------------------------------------------
# NQ session state
# ------------------------------------------------------------------------------

NQ_SESSION_STATE <- c(

  "nq_rth_to_now",

  "nq_rth_vwap_dist",

  "nq_rth_position",

  "nq_last_rth_ret",

  "nq_last_rth_range",

  "nq_rth_gap",

  "nq_open30_ret",

  "nq_open30_green",

  "nq_open30_range",

  "nq_open30_vol_rel20",

  "nq_prevclose_to_1000"
)



# ------------------------------------------------------------------------------
# ES session state
# ------------------------------------------------------------------------------

ES_SESSION_STATE <- c(

  "es_rth_to_now",

  "es_rth_vwap_dist",

  "es_rth_position",

  "es_last_rth_ret",

  "es_last_rth_range",

  "es_rth_gap",

  "es_open30_ret",

  "es_open30_green",

  "es_open30_range",

  "es_open30_vol_rel20",

  "es_prevclose_to_1000"
)



# ------------------------------------------------------------------------------
# Calendar / time
# ------------------------------------------------------------------------------

CALENDAR_FEATURES <- c(

  "tod_sin",

  "tod_cos",

  paste0(
    "dow_",
    c(
      2,
      3,
      4,
      5,
      7
    )
  ),

  "season_spring",

  "season_summer",

  "season_autumn"
)



# ------------------------------------------------------------------------------
# NQ BASE
#
# No technicals.
# No session-derived features.
# ------------------------------------------------------------------------------

NQ_BASE <- c(

  "nq_bar_ret",

  "nq_range",

  "nq_close_loc",

  paste0(
    "nq_ret",
    c(
      1,
      2,
      5,
      15,
      30,
      60
    )
  ),

  paste0(
    "nq_rv",
    c(
      5,
      15,
      60
    )
  ),

  paste0(
    "nq_rs",
    c(
      15,
      60
    )
  ),

  "nq_rv5_over_60",

  "nq_rs15_over_60",

  CALENDAR_FEATURES
)



# ------------------------------------------------------------------------------
# ES BASE
# ------------------------------------------------------------------------------

ES_BASE <- c(

  "es_bar_ret",

  "es_range",

  "es_close_loc",

  paste0(
    "es_ret",
    c(
      1,
      2,
      5,
      15,
      30,
      60
    )
  ),

  paste0(
    "es_rv",
    c(
      5,
      15,
      60
    )
  ),

  paste0(
    "es_rs",
    c(
      15,
      60
    )
  ),

  "es_rv5_over_60",

  "es_rs15_over_60"
)



# ------------------------------------------------------------------------------
# NQ / ES cross-market state
# ------------------------------------------------------------------------------

CROSS_MARKET <- c(

  paste0(
    "nq_minus_es_",
    c(
      1,
      5,
      15,
      60
    )
  ),

  paste0(
    "disagree_",
    c(
      1,
      5,
      15
    )
  ),

  "nq_minus_es_gap",

  "nq_minus_es_open30",

  "open30_disagree"
)



# ------------------------------------------------------------------------------
# Rich NQ
# ------------------------------------------------------------------------------

NQ_FEATURES <- unique(
  c(

    NQ_BASE,

    NQ_TECH,

    COMMON_SESSION,

    NQ_SESSION_STATE
  )
)



# ------------------------------------------------------------------------------
# Rich NQ + ES
# ------------------------------------------------------------------------------

NQ_ES_FEATURES <- unique(
  c(

    NQ_FEATURES,

    ES_BASE,

    ES_TECH,

    ES_SESSION_STATE,

    CROSS_MARKET
  )
)



# ------------------------------------------------------------------------------
# Main search feature sets
# ------------------------------------------------------------------------------

FEATURE_SETS <- list(

  NQ_ONLY =
    NQ_FEATURES,

  NQ_ES =
    NQ_ES_FEATURES
)



# ------------------------------------------------------------------------------
# Feature ablation sets
# ------------------------------------------------------------------------------

ABLATION_FEATURE_SETS <- list(

  NQ_BASE =
    NQ_BASE,


  NQ_BASE_PLUS_TECH =
    unique(
      c(
        NQ_BASE,
        NQ_TECH
      )
    ),


  NQ_BASE_PLUS_SESSION =
    unique(
      c(
        NQ_BASE,
        COMMON_SESSION,
        NQ_SESSION_STATE
      )
    ),


  NQ_RICH =
    NQ_FEATURES,


  NQ_ES_RICH =
    NQ_ES_FEATURES
)



# ------------------------------------------------------------------------------
# Convert +/- Inf / NaN to NA
#
# complete.cases() does not automatically reject Inf.
# ------------------------------------------------------------------------------

for (
  v in
  NQ_ES_FEATURES
) {

  bad <-
    which(
      !is.finite(
        D[[v]]
      )
    )


  if (
    length(bad)
  ) {

    data.table::set(

      D,

      i = bad,

      j = v,

      value =
        NA_real_
    )
  }
}



# ------------------------------------------------------------------------------
# Feature manifest
# ------------------------------------------------------------------------------

FEATURE_MANIFEST <-
  data.table::rbindlist(

    lapply(

      names(
        ABLATION_FEATURE_SETS
      ),

      function(nm) {

        data.table::data.table(

          feature_set =
            nm,

          feature =
            ABLATION_FEATURE_SETS[
              [nm]
            ]
        )
      }
    )
  )



data.table::fwrite(

  FEATURE_MANIFEST,

  file.path(
    OUT,
    "04_feature_manifest.csv"
  )
)



# ------------------------------------------------------------------------------
# Session audit
# ------------------------------------------------------------------------------

SESSION_AUDIT <- D[

  signal_minute %%
    15L ==
    0L &

  bar_start_open &

  signal_open,

  .(

    candidate_signal_rows =
      .N,

    asia_rows =
      sum(
        asia_session
      ),

    london_rows =
      sum(
        london_session
      ),

    us_rth_rows =
      sum(
        us_rth_session
      ),

    us_last60_rows =
      sum(
        us_last60
      ),

    gap_known_rows =
      sum(
        rth_gap_known
      ),

    opening30_known_rows =
      sum(
        opening30_known
      )
  )
]



data.table::fwrite(

  SESSION_AUDIT,

  file.path(
    OUT,
    "05_session_feature_audit.csv"
  )
)



# ------------------------------------------------------------------------------
# Largest raw 1-minute moves
# ------------------------------------------------------------------------------

JUMP_AUDIT <- head(

  D[
    signal_date >=
      as.Date(
        "2017-01-01"
      ),

    .(

      ts,

      signal_et,

      futures_session_date,

      state_segment,

      roll_segment,

      roll_break,

      nq_raw_ret1,

      es_raw_ret1,

      max_abs_1m =
        pmax(
          abs(
            nq_raw_ret1
          ),
          abs(
            es_raw_ret1
          )
        )
    )
  ][
    order(
      -max_abs_1m
    )
  ],

  300L
)



data.table::fwrite(

  JUMP_AUDIT,

  file.path(
    OUT,
    "06_largest_1m_moves_after_roll_flags.csv"
  )
)



# ==============================================================================
# 10. SIGNAL GRID + EXACT ROLL-SAFE TARGETS
# ==============================================================================

lookup_ts <-
  D$ts_num


lookup_close <-
  D$nq_close


lookup_row <-
  D$row_id


lookup_roll_segment <-
  D$roll_segment



# Keep only necessary columns before making one copy per horizon.
#
SIG_COLS <- unique(
  c(

    "ts_num",

    "row_id",

    "roll_segment",

    "signal_ts_num",

    "signal_et",

    "signal_date",

    "signal_minute",

    "season",

    "nq_close",

    NQ_ES_FEATURES
  )
)



SIG <- D[

  signal_minute %%
    15L ==
    0L &

  bar_start_open &

  signal_open,

  ..SIG_COLS
]



SAMPLES <- list()

target_audits <- list()



for (
  h in
  HORIZONS
) {

  S <-
    data.table::copy(
      SIG
    )



  # ---------------------------------------------------------------------------
  # Exact endpoint
  #
  # Signal time:
  #
  #   T = ts + 1 minute
  #
  # Future price known at:
  #
  #   T + h
  #
  # is close of bar beginning:
  #
  #   ts + h
  #
  # ---------------------------------------------------------------------------

  endpoint_idx <-
    match(

      S$ts_num +
      60 * h,

      lookup_ts
    )



  S[
    ,
    endpoint_row :=
      lookup_row[
        endpoint_idx
      ]
  ]


  S[
    ,
    endpoint_roll_segment :=
      lookup_roll_segment[
        endpoint_idx
      ]
  ]


  S[
    ,
    future_close :=
      lookup_close[
        endpoint_idx
      ]
  ]


  S[
    ,
    forecast_end_ts_num :=
      signal_ts_num +
      60 * h
  ]



  end_et <-
    lubridate::with_tz(

      as.POSIXct(

        S$forecast_end_ts_num,

        origin =
          "1970-01-01",

        tz =
          "UTC"
      ),

      "America/New_York"
    )



  S[
    ,
    forecast_end_date :=
      as.Date(
        end_et,
        tz =
          "America/New_York"
      )
  ]



  # ---------------------------------------------------------------------------
  # Require every intervening common NQ/ES minute
  # ---------------------------------------------------------------------------

  S[
    ,
    target_contiguous :=

      !is.na(
        endpoint_row
      ) &

      (
        endpoint_row -
        row_id ==
        h
      )
  ]



  # ---------------------------------------------------------------------------
  # Never allow prediction outcome to cross a suspected contract roll
  # ---------------------------------------------------------------------------

  S[
    ,
    target_same_contract :=

      !is.na(
        endpoint_roll_segment
      ) &

      endpoint_roll_segment ==
        roll_segment
  ]



  S[
    ,
    endpoint_open :=
      is_nq_open(
        end_et
      )
  ]



  S[
    ,
    outcome :=
      data.table::fifelse(

        is.na(
          future_close
        ),

        NA_integer_,

        data.table::fifelse(

          future_close >
            nq_close,

          1L,

          data.table::fifelse(

            future_close <
              nq_close,

            -1L,

            0L
          )
        )
      )
  ]



  candidate_n <-
    nrow(S)


  missing_n <-
    sum(
      is.na(
        S$future_close
      )
    )


  broken_n <-
    sum(

      !is.na(
        S$future_close
      ) &

      !S$target_contiguous
    )


  crossed_roll_n <-
    sum(

      !is.na(
        S$future_close
      ) &

      S$target_contiguous &

      !S$target_same_contract
    )



  # ---------------------------------------------------------------------------
  # COMMON rich-feature sample
  #
  # This deliberately removes approximately the first hour after each futures
  # session open because the reset technicals have not yet accumulated enough
  # observations.
  #
  # NQ_ONLY and NQ_ES therefore compare on exactly the same timestamps.
  # ---------------------------------------------------------------------------

  S <- S[

    target_contiguous &

    target_same_contract &

    endpoint_open &

    !is.na(
      outcome
    ) &

    complete.cases(
      S[
        ,
        ..NQ_ES_FEATURES
      ]
    )
  ]



  S[
    ,
    week_id :=
      format(
        signal_date,
        "%G-%V"
      )
  ]


  S[
    ,
    horizon :=
      h
  ]



  if (
    any(
      S$forecast_end_ts_num -
      S$signal_ts_num !=
      60 * h
    )
  ) {

    stop(
      "Target timing failure at h=",
      h
    )
  }



  SAMPLES[
    [as.character(h)]
  ] <-
    S



  target_audits[
    [as.character(h)]
  ] <-
    data.table::data.table(

      horizon =
        h,

      candidate_signals =
        candidate_n,

      missing_exact_endpoint =
        missing_n,

      discontinuous_target =
        broken_n,

      target_crossed_roll =
        crossed_roll_n,

      retained =
        nrow(S),

      flat_n =
        sum(
          S$outcome ==
            0L
        ),

      flat_rate =
        mean(
          S$outcome ==
            0L
        )
    )
}



TARGET_AUDIT <-
  data.table::rbindlist(
    target_audits
  )



data.table::fwrite(

  TARGET_AUDIT,

  file.path(
    OUT,
    "07_target_audit.csv"
  )
)



rm(

  D,

  SIG,

  lookup_ts,

  lookup_close,

  lookup_row,

  lookup_roll_segment,

  TODAY_RTH_FEATURES,

  RTH_DAILY
)


invisible(
  gc()
)



# ==============================================================================
# 11. MODELS
# ==============================================================================

MODEL_SPECS <- list(

  logit =
    list(
      type =
        "logit"
    ),


  ranger =
    list(
      type =
        "ranger"
    ),


  xgb_d2 =
    list(
      type =
        "xgboost",
      depth =
        2L
    ),


  xgb_d3 =
    list(
      type =
        "xgboost",
      depth =
        3L
    ),


  xgb_d4 =
    list(
      type =
        "xgboost",
      depth =
        4L
    ),


  xgb_d5 =
    list(
      type =
        "xgboost",
      depth =
        5L
    )
)



MODEL_IDS <-
  names(
    MODEL_SPECS
  )



fit_model <- function(
  train,
  features,
  model_id
) {

  spec <-
    MODEL_SPECS[
      [model_id]
    ]


  if (
    is.null(spec)
  ) {

    stop(
      "Unknown model_id: ",
      model_id
    )
  }



  x <-
    as.data.frame(
      train[
        ,
        ..features
      ]
    )


  y <-
    as.integer(
      train$outcome ==
        1L
    )



  # ---------------------------------------------------------------------------
  # Logistic regression benchmark
  # ---------------------------------------------------------------------------

  if (
    spec$type ==
      "logit"
  ) {

    dat <-
      data.frame(

        y = y,

        x,

        check.names =
          FALSE
      )


    return(
      list(

        id =
          model_id,

        type =
          "logit",

        depth =
          NA_integer_,

        fit =
          stats::glm(

            y ~ .,

            data = dat,

            family =
              stats::binomial()
          )
      )
    )
  }



  # ---------------------------------------------------------------------------
  # Random Forest / probability forest
  # ---------------------------------------------------------------------------

  if (
    spec$type ==
      "ranger"
  ) {

    dat <-
      data.frame(

        y =
          factor(

            ifelse(
              train$outcome ==
                1L,
              "UP",
              "DOWN"
            ),

            levels =
              c(
                "DOWN",
                "UP"
              )
          ),

        x,

        check.names =
          FALSE
      )



    fit <-
      ranger::ranger(

        y ~ .,

        data =
          dat,

        probability =
          TRUE,

        num.trees =
          500,

        mtry =
          max(
            1L,
            floor(
              sqrt(
                length(features)
              )
            )
          ),

        min.node.size =
          50,

        max.depth =
          8,

        importance =
          "none",

        num.threads =
          0,

        seed =
          SEED,

        verbose =
          FALSE
      )



    return(
      list(

        id =
          model_id,

        type =
          "ranger",

        depth =
          NA_integer_,

        fit =
          fit
      )
    )
  }



  # ---------------------------------------------------------------------------
  # XGBoost
  # ---------------------------------------------------------------------------

  dtrain <-
    xgboost::xgb.DMatrix(

      data =
        as.matrix(x),

      label =
        y
    )



  params <-
    xgboost::xgb.params(

      objective =
        "binary:logistic",

      eval_metric =
        "logloss",

      max_depth =
        spec$depth,

      eta =
        0.05,

      min_child_weight =
        30,

      subsample =
        0.8,

      colsample_bytree =
        0.8,

      tree_method =
        "hist",

      nthread =
        0,

      seed =
        SEED
    )



  list(

    id =
      model_id,

    type =
      "xgboost",

    depth =
      spec$depth,

    fit =
      xgboost::xgb.train(

        params =
          params,

        data =
          dtrain,

        nrounds =
          150L,

        verbose =
          0
      )
  )
}



predict_model <- function(
  model,
  newdata,
  features
) {

  x <-
    as.data.frame(
      newdata[
        ,
        ..features
      ]
    )



  if (
    model$type ==
      "logit"
  ) {

    p <-
      as.numeric(
        stats::predict(

          model$fit,

          newdata =
            x,

          type =
            "response"
        )
      )


  } else if (
    model$type ==
      "ranger"
  ) {

    pr <-
      predict(

        model$fit,

        data =
          x,

        num.threads =
          0,

        verbose =
          FALSE
      )$predictions



    if (
      !(
        "UP" %in%
        colnames(pr)
      )
    ) {

      stop(
        "Ranger UP probability column missing."
      )
    }



    p <-
      as.numeric(
        pr[
          ,
          "UP"
        ]
      )


  } else {

    p <-
      as.numeric(
        predict(

          model$fit,

          xgboost::xgb.DMatrix(
            as.matrix(x)
          )
        )
      )
  }



  if (

    length(p) !=
      nrow(newdata) ||

    any(
      !is.finite(p)
    ) ||

    any(
      p < 0 |
      p > 1
    )
  ) {

    stop(
      "Invalid probabilities from ",
      model$id
    )
  }



  p
}



# ==============================================================================
# 12. SCORING + CONCENTRATION + NON-OVERLAP + BLOCK INFERENCE
# ==============================================================================

# ------------------------------------------------------------------------------
# Greedy count of non-overlapping h-minute forecast windows
# ------------------------------------------------------------------------------

count_nonoverlap <- function(
  tsnum,
  horizon
) {

  if (
    !length(tsnum)
  ) {

    return(
      0L
    )
  }



  x <-
    sort(
      tsnum
    )


  next_allowed <-
    -Inf


  n <-
    0L



  for (
    tt in
    x
  ) {

    if (
      tt >=
      next_allowed
    ) {

      n <-
        n + 1L


      next_allowed <-
        tt +
        60 *
        horizon
    }
  }



  n
}



# ------------------------------------------------------------------------------
# Candidate evaluation
# ------------------------------------------------------------------------------

evaluate_selected <- function(
  Z,
  p,
  cutoff,
  base_side,
  horizon
) {

  confidence <-
    abs(
      p -
      0.5
    )


  selected <-
    confidence >=
    cutoff


  side <-
    ifelse(
      p >=
        0.5,
      1L,
      -1L
    )



  all_weeks <-
    data.table::data.table(

      week_id =
        unique(
          Z$week_id
        )
    )



  if (
    !any(selected)
  ) {

    week_zero <-
      data.table::copy(
        all_weeks
      )


    week_zero[
      ,
      `:=`(

        n = 0L,

        wins = 0L,

        base_wins = 0L
      )
    ]



    return(
      list(

        metric =
          data.table::data.table(

            selected_n =
              0L,

            coverage =
              0,

            wins =
              0L,

            win_rate =
              NA_real_,

            base_wins =
              0L,

            baseline_wr =
              NA_real_,

            edge =
              NA_real_,

            flat_rate =
              NA_real_,

            active_weeks =
              0L,

            unique_days =
              0L,

            top_day_share =
              NA_real_,

            top5_day_share =
              NA_real_,

            nonoverlap_n =
              0L,

            nonoverlap_fraction =
              NA_real_,

            long_n =
              0L,

            long_wins =
              0L,

            long_wr =
              NA_real_,

            short_n =
              0L,

            short_wins =
              0L,

            short_wr =
              NA_real_,

            up_only_wr =
              NA_real_,

            down_only_wr =
              NA_real_
          ),

        weeks =
          week_zero
      )
    )
  }



  Zs <-
    Z[selected]


  side_s <-
    side[selected]



  # Flat = loss because +/-1 cannot equal 0.
  win <-
    as.integer(
      side_s ==
      Zs$outcome
    )


  base_win <-
    as.integer(
      base_side ==
      Zs$outcome
    )



  n <-
    nrow(Zs)


  wins <-
    sum(win)


  base_wins <-
    sum(
      base_win
    )



  # ---------------------------------------------------------------------------
  # Day concentration
  # ---------------------------------------------------------------------------

  day_counts <-
    sort(

      table(
        as.character(
          Zs$signal_date
        )
      ),

      decreasing =
        TRUE
    )



  top_day_share <-
    as.numeric(
      day_counts[1L]
    ) /
    n



  top5_day_share <-
    sum(
      head(
        as.numeric(
          day_counts
        ),
        5L
      )
    ) /
    n



  # ---------------------------------------------------------------------------
  # Long / short
  # ---------------------------------------------------------------------------

  long_idx <-
    side_s ==
    1L


  short_idx <-
    side_s ==
    -1L



  long_n <-
    sum(
      long_idx
    )


  short_n <-
    sum(
      short_idx
    )



  long_wins <-
    sum(
      win[
        long_idx
      ]
    )


  short_wins <-
    sum(
      win[
        short_idx
      ]
    )



  # ---------------------------------------------------------------------------
  # Effective non-overlapping target count
  # ---------------------------------------------------------------------------

  nonoverlap_n <-
    count_nonoverlap(

      Zs$signal_ts_num,

      horizon
    )



  # ---------------------------------------------------------------------------
  # Week totals
  # ---------------------------------------------------------------------------

  wk <-
    data.table::data.table(

      week_id =
        Zs$week_id,

      win =
        win,

      base_win =
        base_win
    )[
      ,
      .(

        n =
          .N,

        wins =
          sum(win),

        base_wins =
          sum(
            base_win
          )
      ),

      by =
        week_id
    ]



  wk <-
    merge(

      all_weeks,

      wk,

      by =
        "week_id",

      all.x =
        TRUE
    )



  wk[
    is.na(n),
    `:=`(

      n =
        0L,

      wins =
        0L,

      base_wins =
        0L
    )
  ]



  list(

    metric =
      data.table::data.table(

        selected_n =
          n,

        coverage =
          mean(selected),

        wins =
          wins,

        win_rate =
          wins /
          n,

        base_wins =
          base_wins,

        baseline_wr =
          base_wins /
          n,

        edge =
          (
            wins -
            base_wins
          ) /
          n,

        flat_rate =
          mean(
            Zs$outcome ==
              0L
          ),

        active_weeks =
          data.table::uniqueN(
            Zs$week_id
          ),

        unique_days =
          data.table::uniqueN(
            Zs$signal_date
          ),

        top_day_share =
          top_day_share,

        top5_day_share =
          top5_day_share,

        nonoverlap_n =
          nonoverlap_n,

        nonoverlap_fraction =
          nonoverlap_n /
          n,

        long_n =
          long_n,

        long_wins =
          long_wins,

        long_wr =
          if (
            long_n >
            0L
          ) {

            long_wins /
            long_n

          } else {

            NA_real_
          },

        short_n =
          short_n,

        short_wins =
          short_wins,

        short_wr =
          if (
            short_n >
            0L
          ) {

            short_wins /
            short_n

          } else {

            NA_real_
          },

        # Direction-only descriptive baselines on the selected timestamps.
        up_only_wr =
          mean(
            Zs$outcome ==
              1L
          ),

        down_only_wr =
          mean(
            Zs$outcome ==
              -1L
          )
      ),

    weeks =
      wk
  )
}



# ------------------------------------------------------------------------------
# Week-block bootstrap
#
# Resample weeks WITHIN each chronological OOS fold.
#
# Outputs:
#
#   CI for model win rate
#   CI for paired model edge over baseline
# ------------------------------------------------------------------------------

stratified_week_bootstrap <- function(
  W,
  reps = BOOT_REPS,
  seed = SEED
) {

  fold_tables <-
    split(
      W,
      W$fold
    )



  set.seed(
    seed
  )



  boot_wr <-
    rep(
      NA_real_,
      reps
    )


  boot_edge <-
    rep(
      NA_real_,
      reps
    )



  for (
    b in
    seq_len(reps)
  ) {

    total_n <-
      0


    total_wins <-
      0


    total_base_wins <-
      0



    for (
      z in
      fold_tables
    ) {

      if (
        nrow(z) ==
        0L
      ) {

        next
      }



      idx <-
        sample.int(

          nrow(z),

          nrow(z),

          replace =
            TRUE
        )



      total_n <-
        total_n +
        sum(
          z$n[idx]
        )


      total_wins <-
        total_wins +
        sum(
          z$wins[idx]
        )


      total_base_wins <-
        total_base_wins +
        sum(
          z$base_wins[idx]
        )
    }



    if (
      total_n >
      0L
    ) {

      boot_wr[b] <-
        total_wins /
        total_n


      boot_edge[b] <-
        (
          total_wins -
          total_base_wins
        ) /
        total_n
    }
  }



  boot_wr <-
    boot_wr[
      is.finite(
        boot_wr
      )
    ]


  boot_edge <-
    boot_edge[
      is.finite(
        boot_edge
      )
    ]



  if (
    !length(
      boot_wr
    ) ||
    !length(
      boot_edge
    )
  ) {

    return(
      c(

        wr_lower =
          NA_real_,

        wr_upper =
          NA_real_,

        edge_lower =
          NA_real_,

        edge_upper =
          NA_real_
      )
    )
  }



  c(

    wr_lower =
      unname(
        stats::quantile(
          boot_wr,
          0.025
        )
      ),

    wr_upper =
      unname(
        stats::quantile(
          boot_wr,
          0.975
        )
      ),

    edge_lower =
      unname(
        stats::quantile(
          boot_edge,
          0.025
        )
      ),

    edge_upper =
      unname(
        stats::quantile(
          boot_edge,
          0.975
        )
      )
  )
}



candidate_id <- function(
  h,
  feature_set,
  model_id,
  coverage
) {

  paste(

    h,

    feature_set,

    model_id,

    sprintf(
      "%.4f",
      coverage
    ),

    sep =
      "__"
  )
}



safe_max <- function(x) {

  if (
    all(
      is.na(x)
    )
  ) {

    return(
      NA_real_
    )
  }


  max(
    x,
    na.rm =
      TRUE
  )
}



safe_min <- function(x) {

  if (
    all(
      is.na(x)
    )
  ) {

    return(
      NA_real_
    )
  }


  min(
    x,
    na.rm =
      TRUE
  )
}



# ==============================================================================
# 13. REPEATED CHRONOLOGICAL WALK-FORWARD SEARCH
# ==============================================================================

fold_results <- list()

week_results <- list()


fold_counter <-
  0L


week_counter <-
  0L



for (
  fi in
  seq_len(
    nrow(FOLDS)
  )
) {

  F <-
    FOLDS[fi]



  cat(
    "\n============================================================\n"
  )


  cat(
    "WALK-FORWARD TEST FOLD: ",
    F$fold,
    "\n",
    sep = ""
  )


  cat(
    "============================================================\n"
  )



  for (
    h in
    HORIZONS
  ) {

    S <-
      SAMPLES[
        [as.character(h)]
      ]



    # -------------------------------------------------------------------------
    # Model training
    #
    # Flat outcomes excluded only from binary model estimation.
    # -------------------------------------------------------------------------

    train <- S[

      signal_date >=
        F$train_start &

      signal_date <
        F$train_end &

      forecast_end_date <
        F$train_end &

      outcome !=
        0L
    ]



    # -------------------------------------------------------------------------
    # Confidence calibration year
    #
    # Outcome is NOT used to choose confidence cutoff.
    #
    # We only take percentile of model confidence.
    # -------------------------------------------------------------------------

    calibrate <- S[

      signal_date >=
        F$cal_start &

      signal_date <
        F$cal_end &

      forecast_end_date <
        F$cal_end
    ]



    # -------------------------------------------------------------------------
    # OOS test
    # -------------------------------------------------------------------------

    test <- S[

      signal_date >=
        F$test_start &

      signal_date <
        F$test_end &

      forecast_end_date <
        F$test_end
    ]



    if (
      nrow(train) <
        5000L ||

      nrow(calibrate) <
        500L ||

      nrow(test) <
        100L
    ) {

      stop(

        "Unexpectedly small fold sample | fold=",

        F$fold,

        " | h=",

        h
      )
    }



    # -------------------------------------------------------------------------
    # Training-period unconditional directional baseline
    # -------------------------------------------------------------------------

    base_side <-
      ifelse(

        mean(
          train$outcome ==
            1L
        ) >=
          0.5,

        1L,

        -1L
      )



    for (
      feature_set in
      names(
        FEATURE_SETS
      )
    ) {

      features <-
        FEATURE_SETS[
          [feature_set]
        ]



      for (
        model_id in
        MODEL_IDS
      ) {

        spec <-
          MODEL_SPECS[
            [model_id]
          ]


        xgb_depth <-
          if (
            is.null(
              spec$depth
            )
          ) {

            NA_integer_

          } else {

            spec$depth
          }



        cat(

          "fold=",
          F$fold,

          " | h=",
          h,

          " | ",
          feature_set,

          " | ",
          model_id,

          "\n",

          sep = ""
        )



        # ---------------------------------------------------------------------
        # Fit ONLY on historical training years
        # ---------------------------------------------------------------------

        model <-
          fit_model(

            train,

            features,

            model_id
          )



        # ---------------------------------------------------------------------
        # Calibration-year confidence
        # ---------------------------------------------------------------------

        p_cal <-
          predict_model(

            model,

            calibrate,

            features
          )



        # ---------------------------------------------------------------------
        # Future OOS test
        # ---------------------------------------------------------------------

        p_test <-
          predict_model(

            model,

            test,

            features
          )



        cal_conf <-
          abs(
            p_cal -
            0.5
          )



        for (
          target_coverage in
          COVERAGES
        ) {

          # -------------------------------------------------------------------
          # IMPORTANT:
          #
          # cutoff comes from PRIOR calibration year,
          # NEVER from current OOS test fold.
          # -------------------------------------------------------------------

          cutoff <-
            as.numeric(
              stats::quantile(

                cal_conf,

                probs =
                  1 -
                  target_coverage,

                names =
                  FALSE,

                type =
                  7
              )
            )



          ev <-
            evaluate_selected(

              test,

              p_test,

              cutoff,

              base_side,

              h
            )



          cid <-
            candidate_id(

              h,

              feature_set,

              model_id,

              target_coverage
            )



          fold_counter <-
            fold_counter +
            1L



          fold_results[
            [fold_counter]
          ] <-
            cbind(

              data.table::data.table(

                candidate_id =
                  cid,

                fold =
                  F$fold,

                full_year =
                  F$full_year,

                horizon =
                  h,

                feature_set =
                  feature_set,

                model_id =
                  model_id,

                xgb_depth =
                  xgb_depth,

                target_coverage =
                  target_coverage,

                confidence_cutoff =
                  cutoff,

                base_side =
                  base_side
              ),

              ev$metric
            )



          wk <-
            data.table::copy(
              ev$weeks
            )



          wk[
            ,
            `:=`(

              candidate_id =
                cid,

              fold =
                F$fold,

              horizon =
                h,

              feature_set =
                feature_set,

              model_id =
                model_id,

              target_coverage =
                target_coverage
            )
          ]



          week_counter <-
            week_counter +
            1L



          week_results[
            [week_counter]
          ] <-
            wk
        }



        rm(
          model,
          p_cal,
          p_test
        )


        invisible(
          gc(
            FALSE
          )
        )
      }
    }
  }
}



FOLD_RESULTS <-
  data.table::rbindlist(

    fold_results,

    fill =
      TRUE
  )



WEEK_RESULTS <-
  data.table::rbindlist(

    week_results,

    fill =
      TRUE
  )



data.table::fwrite(

  FOLD_RESULTS,

  file.path(
    OUT,
    "08_walkforward_fold_results.csv"
  )
)



# ==============================================================================
# 14. AGGREGATE DEVELOPMENT-OOS EVIDENCE
# ==============================================================================

if (
  USE_2026_IN_RANKING
) {

  RANK_FOLDS <-
    FOLDS$fold

} else {

  RANK_FOLDS <-
    FOLDS[
      full_year ==
        TRUE,
      fold
    ]
}



FR <- FOLD_RESULTS[
  fold %in%
    RANK_FOLDS
]


WR <- WEEK_RESULTS[
  fold %in%
    RANK_FOLDS
]



AGG <- FR[
  ,
  .(

    selected_n =
      sum(
        selected_n
      ),


    wins =
      sum(
        wins
      ),


    overall_wr =
      if (
        sum(
          selected_n
        ) >
        0L
      ) {

        sum(
          wins
        ) /
        sum(
          selected_n
        )

      } else {

        NA_real_
      },


    base_wins =
      sum(
        base_wins
      ),


    overall_baseline_wr =
      if (
        sum(
          selected_n
        ) >
        0L
      ) {

        sum(
          base_wins
        ) /
        sum(
          selected_n
        )

      } else {

        NA_real_
      },


    overall_edge =
      if (
        sum(
          selected_n
        ) >
        0L
      ) {

        (
          sum(
            wins
          ) -
          sum(
            base_wins
          )
        ) /
        sum(
          selected_n
        )

      } else {

        NA_real_
      },


    total_nonoverlap_n =
      sum(
        nonoverlap_n
      ),


    nonoverlap_fraction =
      if (
        sum(
          selected_n
        ) >
        0L
      ) {

        sum(
          nonoverlap_n
        ) /
        sum(
          selected_n
        )

      } else {

        NA_real_
      },


    avg_active_weeks_full =
      mean(
        active_weeks[
          full_year
        ]
      ),


    min_active_weeks_full =
      safe_min(
        active_weeks[
          full_year
        ]
      ),


    folds_over_50 =
      sum(
        win_rate >
          0.50,
        na.rm =
          TRUE
      ),


    full_years_over_50 =
      sum(
        win_rate[
          full_year
        ] >
          0.50,
        na.rm =
          TRUE
      ),


    min_full_year_wr =
      safe_min(
        win_rate[
          full_year
        ]
      ),


    max_full_year_wr =
      safe_max(
        win_rate[
          full_year
        ]
      ),


    max_top_day_share =
      safe_max(
        top_day_share
      ),


    max_top5_day_share =
      safe_max(
        top5_day_share
      ),


    long_n =
      sum(
        long_n
      ),


    long_wins =
      sum(
        long_wins
      ),


    long_wr =
      if (
        sum(
          long_n
        ) >
        0L
      ) {

        sum(
          long_wins
        ) /
        sum(
          long_n
        )

      } else {

        NA_real_
      },


    short_n =
      sum(
        short_n
      ),


    short_wins =
      sum(
        short_wins
      ),


    short_wr =
      if (
        sum(
          short_n
        ) >
        0L
      ) {

        sum(
          short_wins
        ) /
        sum(
          short_n
        )

      } else {

        NA_real_
      },


    mean_actual_coverage =
      mean(
        coverage,
        na.rm =
          TRUE
      )
  ),

  by = .(

    candidate_id,

    horizon,

    feature_set,

    model_id,

    xgb_depth,

    target_coverage
  )
]



# ------------------------------------------------------------------------------
# Block-bootstrap intervals
# ------------------------------------------------------------------------------

AGG[
  ,
  `:=`(

    wr_block_lower =
      NA_real_,

    wr_block_upper =
      NA_real_,

    edge_block_lower =
      NA_real_,

    edge_block_upper =
      NA_real_
  )
]



data.table::setkey(
  WR,
  candidate_id
)



for (
  i in
  seq_len(
    nrow(AGG)
  )
) {

  W <-
    WR[
      .(
        AGG$candidate_id[i]
      )
    ]



  ci <-
    stratified_week_bootstrap(

      W,

      reps =
        BOOT_REPS,

      seed =
        SEED +
        i
    )



  AGG[
    i,
    `:=`(

      wr_block_lower =
        ci["wr_lower"],

      wr_block_upper =
        ci["wr_upper"],

      edge_block_lower =
        ci["edge_lower"],

      edge_block_upper =
        ci["edge_upper"]
    )
  ]
}



# ------------------------------------------------------------------------------
# Stability gates
# ------------------------------------------------------------------------------

AGG[
  ,
  temporal_ok :=

    selected_n >=
      MIN_AGG_N &

    total_nonoverlap_n >=
      MIN_EFFECTIVE_N &

    avg_active_weeks_full >=
      MIN_AVG_ACTIVE_WEEKS_FULL &

    min_active_weeks_full >=
      MIN_MIN_ACTIVE_WEEKS_FULL &

    max_top5_day_share <=
      MAX_TOP5_DAY_SHARE
]



AGG[
  ,
  persistence_ok :=

    full_years_over_50 >=
      MIN_FULL_YEARS_OVER_50
]



AGG[
  ,
  statistically_robust :=

    temporal_ok &

    persistence_ok &

    is.finite(
      wr_block_lower
    ) &

    is.finite(
      edge_block_lower
    ) &

    wr_block_lower >
      0.50 &

    edge_block_lower >
      0
]



# ------------------------------------------------------------------------------
# Candidate ranking
#
# Priority:
#
#   1. statistically robust
#   2. temporal breadth
#   3. persistence
#   4. conservative WR lower bound
#   5. conservative incremental-edge lower bound
#   6. number of full years above 50%
#   7. overall WR
#   8. sample size
# ------------------------------------------------------------------------------

data.table::setorder(

  AGG,

  -statistically_robust,

  -temporal_ok,

  -persistence_ok,

  -wr_block_lower,

  -edge_block_lower,

  -full_years_over_50,

  -overall_wr,

  -selected_n
)



CHAMPION <-
  data.table::copy(
    AGG[1]
  )



data.table::fwrite(

  AGG,

  file.path(
    OUT,
    "09_walkforward_aggregate_all_candidates.csv"
  )
)



data.table::fwrite(

  AGG[
    1:min(
      .N,
      100L
    )
  ],

  file.path(
    OUT,
    "10_top_stable_candidates.csv"
  )
)



data.table::fwrite(

  CHAMPION,

  file.path(
    OUT,
    "11_DEVELOPMENT_CHAMPION.csv"
  )
)



# ------------------------------------------------------------------------------
# Best candidate by XGBoost depth
# ------------------------------------------------------------------------------

XGB_DEPTH_COMPARISON <- AGG[

  !is.na(
    xgb_depth
  )

][

  order(

    -statistically_robust,

    -temporal_ok,

    -persistence_ok,

    -wr_block_lower,

    -edge_block_lower,

    -overall_wr
  ),

  .SD[1],

  by =
    xgb_depth
]



data.table::setorder(

  XGB_DEPTH_COMPARISON,

  xgb_depth
)



data.table::fwrite(

  XGB_DEPTH_COMPARISON,

  file.path(
    OUT,
    "12_best_candidate_by_xgb_depth.csv"
  )
)



# ------------------------------------------------------------------------------
# Best NQ_ONLY versus NQ_ES
# ------------------------------------------------------------------------------

BEST_FEATURE_SET <- AGG[

  order(

    -statistically_robust,

    -temporal_ok,

    -persistence_ok,

    -wr_block_lower,

    -edge_block_lower,

    -overall_wr
  ),

  .SD[1],

  by =
    feature_set
]



data.table::fwrite(

  BEST_FEATURE_SET,

  file.path(
    OUT,
    "13_best_NQ_only_vs_NQ_ES.csv"
  )
)



# ------------------------------------------------------------------------------
# Explicit 2026 results for top aggregate candidates
# ------------------------------------------------------------------------------

TOP_IDS <-
  AGG[
    1:min(
      .N,
      50L
    ),
    candidate_id
  ]



TOP_2026 <- FOLD_RESULTS[

  fold ==
    "2026_YTD" &

  candidate_id %in%
    TOP_IDS
]



TOP_2026[
  ,
  aggregate_rank :=
    match(
      candidate_id,
      TOP_IDS
    )
]



data.table::setorder(

  TOP_2026,

  aggregate_rank
)



data.table::fwrite(

  TOP_2026,

  file.path(
    OUT,
    "14_top_candidates_2026_YTD.csv"
  )
)



# ==============================================================================
# 15. RE-RUN DEVELOPMENT CHAMPION
#
#     Save exact selected predictions for audit.
# ==============================================================================

champ_h <-
  CHAMPION$horizon


champ_fs <-
  CHAMPION$feature_set


champ_model <-
  CHAMPION$model_id


champ_cov <-
  CHAMPION$target_coverage


champ_features <-
  FEATURE_SETS[
    [champ_fs]
  ]



champ_prediction_list <-
  list()


champ_fold_list <-
  list()



for (
  fi in
  seq_len(
    nrow(FOLDS)
  )
) {

  F <-
    FOLDS[fi]


  S <-
    SAMPLES[
      [as.character(
        champ_h
      )]
    ]



  train <- S[

    signal_date >=
      F$train_start &

    signal_date <
      F$train_end &

    forecast_end_date <
      F$train_end &

    outcome !=
      0L
  ]



  calibrate <- S[

    signal_date >=
      F$cal_start &

    signal_date <
      F$cal_end &

    forecast_end_date <
      F$cal_end
  ]



  test <- S[

    signal_date >=
      F$test_start &

    signal_date <
      F$test_end &

    forecast_end_date <
      F$test_end
  ]



  base_side <-
    ifelse(

      mean(
        train$outcome ==
          1L
      ) >=
        0.5,

      1L,

      -1L
    )



  model <-
    fit_model(

      train,

      champ_features,

      champ_model
    )



  p_cal <-
    predict_model(

      model,

      calibrate,

      champ_features
    )



  p_test <-
    predict_model(

      model,

      test,

      champ_features
    )



  cutoff <-
    as.numeric(
      stats::quantile(

        abs(
          p_cal -
          0.5
        ),

        probs =
          1 -
          champ_cov,

        names =
          FALSE,

        type =
          7
      )
    )



  confidence <-
    abs(
      p_test -
      0.5
    )



  selected <-
    confidence >=
    cutoff



  side <-
    ifelse(
      p_test >=
        0.5,
      1L,
      -1L
    )



  P <-
    data.table::data.table(

      fold =
        F$fold,

      signal_et =
        test$signal_et,

      signal_date =
        test$signal_date,

      week_id =
        test$week_id,

      season =
        test$season,

      asia_session =
        test$asia_session,

      london_session =
        test$london_session,

      us_rth_session =
        test$us_rth_session,

      us_last60 =
        test$us_last60,

      opening30_known =
        test$opening30_known,

      nq_rth_gap =
        test$nq_rth_gap,

      nq_open30_ret =
        test$nq_open30_ret,

      nq_prevclose_to_1000 =
        test$nq_prevclose_to_1000,

      p_up =
        p_test,

      confidence =
        confidence,

      cutoff =
        cutoff,

      selected =
        selected,

      prediction =
        side,

      outcome =
        test$outcome,

      win =
        as.integer(
          side ==
          test$outcome
        ),

      baseline_win =
        as.integer(
          base_side ==
          test$outcome
        )
    )



  champ_prediction_list[
    [fi]
  ] <-
    P[
      selected ==
        TRUE
    ]



  champ_fold_list[
    [fi]
  ] <-
    FOLD_RESULTS[

      candidate_id ==
        CHAMPION$candidate_id &

      fold ==
        F$fold
    ]



  rm(
    model,
    p_cal,
    p_test
  )


  invisible(
    gc(
      FALSE
    )
  )
}



CHAMPION_PRED <-
  data.table::rbindlist(

    champ_prediction_list,

    fill =
      TRUE
  )



CHAMPION_FOLDS <-
  data.table::rbindlist(

    champ_fold_list,

    fill =
      TRUE
  )



data.table::fwrite(

  CHAMPION_FOLDS,

  file.path(
    OUT,
    "15_champion_fold_results.csv"
  )
)



data.table::fwrite(

  CHAMPION_PRED,

  file.path(
    OUT,
    "16_champion_selected_predictions_all_folds.csv"
  )
)



# ------------------------------------------------------------------------------
# Champion by session
# ------------------------------------------------------------------------------

CHAMPION_BY_SESSION <-
  data.table::rbindlist(

    list(

      CHAMPION_PRED[
        asia_session ==
          1L,
        .(
          session =
            "Asia",
          n =
            .N,
          wr =
            mean(win)
        ),
        by =
          fold
      ],


      CHAMPION_PRED[
        london_session ==
          1L,
        .(
          session =
            "London",
          n =
            .N,
          wr =
            mean(win)
        ),
        by =
          fold
      ],


      CHAMPION_PRED[
        us_rth_session ==
          1L,
        .(
          session =
            "US_RTH",
          n =
            .N,
          wr =
            mean(win)
        ),
        by =
          fold
      ],


      CHAMPION_PRED[
        us_last60 ==
          1L,
        .(
          session =
            "US_last60",
          n =
            .N,
          wr =
            mean(win)
        ),
        by =
          fold
      ]
    ),

    fill =
      TRUE
  )



data.table::fwrite(

  CHAMPION_BY_SESSION,

  file.path(
    OUT,
    "17_champion_by_session.csv"
  )
)



# ------------------------------------------------------------------------------
# Champion by season
# ------------------------------------------------------------------------------

CHAMPION_BY_SEASON <- CHAMPION_PRED[
  ,
  .(

    n =
      .N,

    wr =
      mean(win)
  ),

  by = .(
    fold,
    season
  )
]



data.table::fwrite(

  CHAMPION_BY_SEASON,

  file.path(
    OUT,
    "18_champion_by_season.csv"
  )
)



# ==============================================================================
# 16. FEATURE ABLATION
#
#     Same selected model / horizon / coverage.
#     Only information set changes.
# ==============================================================================

ablation_fold_results <-
  list()


ablation_week_results <-
  list()


ablation_fold_counter <-
  0L


ablation_week_counter <-
  0L



for (
  ablation_name in
  names(
    ABLATION_FEATURE_SETS
  )
) {

  features <-
    ABLATION_FEATURE_SETS[
      [ablation_name]
    ]



  cat(
    "\nAblation: ",
    ablation_name,
    "\n",
    sep = ""
  )



  for (
    fi in
    seq_len(
      nrow(FOLDS)
    )
  ) {

    F <-
      FOLDS[fi]


    S <-
      SAMPLES[
        [as.character(
          champ_h
        )]
      ]



    train <- S[

      signal_date >=
        F$train_start &

      signal_date <
        F$train_end &

      forecast_end_date <
        F$train_end &

      outcome !=
        0L
    ]



    calibrate <- S[

      signal_date >=
        F$cal_start &

      signal_date <
        F$cal_end &

      forecast_end_date <
        F$cal_end
    ]



    test <- S[

      signal_date >=
        F$test_start &

      signal_date <
        F$test_end &

      forecast_end_date <
        F$test_end
    ]



    base_side <-
      ifelse(

        mean(
          train$outcome ==
            1L
        ) >=
          0.5,

        1L,

        -1L
      )



    model <-
      fit_model(

        train,

        features,

        champ_model
      )



    p_cal <-
      predict_model(

        model,

        calibrate,

        features
      )



    p_test <-
      predict_model(

        model,

        test,

        features
      )



    cutoff <-
      as.numeric(
        stats::quantile(

          abs(
            p_cal -
            0.5
          ),

          probs =
            1 -
            champ_cov,

          names =
            FALSE,

          type =
            7
        )
      )



    ev <-
      evaluate_selected(

        test,

        p_test,

        cutoff,

        base_side,

        champ_h
      )



    ablation_fold_counter <-
      ablation_fold_counter +
      1L



    ablation_fold_results[
      [ablation_fold_counter]
    ] <-
      cbind(

        data.table::data.table(

          ablation_set =
            ablation_name,

          fold =
            F$fold,

          full_year =
            F$full_year,

          horizon =
            champ_h,

          model_id =
            champ_model,

          target_coverage =
            champ_cov,

          confidence_cutoff =
            cutoff
        ),

        ev$metric
      )



    W <-
      data.table::copy(
        ev$weeks
      )



    W[
      ,
      `:=`(

        ablation_set =
          ablation_name,

        fold =
          F$fold
      )
    ]



    ablation_week_counter <-
      ablation_week_counter +
      1L



    ablation_week_results[
      [ablation_week_counter]
    ] <-
      W



    rm(
      model,
      p_cal,
      p_test
    )


    invisible(
      gc(
        FALSE
      )
    )
  }
}



ABLATION_FOLD <-
  data.table::rbindlist(

    ablation_fold_results,

    fill =
      TRUE
  )



ABLATION_WEEK <-
  data.table::rbindlist(

    ablation_week_results,

    fill =
      TRUE
  )



# ------------------------------------------------------------------------------
# Respect same ranking-fold policy
# ------------------------------------------------------------------------------

ABLATION_FOLD_RANK <- ABLATION_FOLD[
  fold %in%
    RANK_FOLDS
]


ABLATION_WEEK_RANK <- ABLATION_WEEK[
  fold %in%
    RANK_FOLDS
]



ABLATION_AGG <- ABLATION_FOLD_RANK[
  ,
  .(

    selected_n =
      sum(
        selected_n
      ),

    wins =
      sum(
        wins
      ),

    overall_wr =
      sum(
        wins
      ) /
      sum(
        selected_n
      ),

    base_wins =
      sum(
        base_wins
      ),

    baseline_wr =
      sum(
        base_wins
      ) /
      sum(
        selected_n
      ),

    edge =
      (
        sum(
          wins
        ) -
        sum(
          base_wins
        )
      ) /
      sum(
        selected_n
      ),

    total_nonoverlap_n =
      sum(
        nonoverlap_n
      ),

    avg_active_weeks_full =
      mean(
        active_weeks[
          full_year
        ]
      ),

    min_active_weeks_full =
      safe_min(
        active_weeks[
          full_year
        ]
      ),

    full_years_over_50 =
      sum(
        win_rate[
          full_year
        ] >
          0.50,
        na.rm =
          TRUE
      ),

    max_top5_day_share =
      safe_max(
        top5_day_share
      )
  ),

  by =
    ablation_set
]



ABLATION_AGG[
  ,
  `:=`(

    wr_block_lower =
      NA_real_,

    wr_block_upper =
      NA_real_,

    edge_block_lower =
      NA_real_,

    edge_block_upper =
      NA_real_
  )
]



for (
  i in
  seq_len(
    nrow(
      ABLATION_AGG
    )
  )
) {

  W <- ABLATION_WEEK_RANK[
    ablation_set ==
      ABLATION_AGG$ablation_set[i]
  ]



  ci <-
    stratified_week_bootstrap(

      W,

      reps =
        BOOT_REPS,

      seed =
        SEED +
        10000L +
        i
    )



  ABLATION_AGG[
    i,
    `:=`(

      wr_block_lower =
        ci["wr_lower"],

      wr_block_upper =
        ci["wr_upper"],

      edge_block_lower =
        ci["edge_lower"],

      edge_block_upper =
        ci["edge_upper"]
    )
  ]
}



data.table::setorder(

  ABLATION_AGG,

  -wr_block_lower,

  -edge_block_lower,

  -overall_wr
)



data.table::fwrite(

  ABLATION_FOLD,

  file.path(
    OUT,
    "19_ablation_fold_results.csv"
  )
)



data.table::fwrite(

  ABLATION_AGG,

  file.path(
    OUT,
    "20_ablation_aggregate.csv"
  )
)



# ==============================================================================
# 17. OUTPUT / SUMMARY
# ==============================================================================

cat(
  "\n\n============================================================\n"
)

cat(
  "PACKAGE VERSIONS\n"
)

cat(
  "============================================================\n"
)

print(
  PACKAGE_VERSIONS
)



cat(
  "\n\n============================================================\n"
)

cat(
  "ROLL DETECTION\n"
)

cat(
  "============================================================\n"
)

print(
  ROLL_SUMMARY
)


cat(
  "\nDetected roll boundaries: ",
  nrow(
    ROLL_EVENTS
  ),
  "\n",
  sep = ""
)


if (
  nrow(
    ROLL_EVENTS
  ) >
  0L
) {

  print(
    ROLL_EVENTS
  )
}



cat(
  "\n\n============================================================\n"
)

cat(
  "TARGET AUDIT\n"
)

cat(
  "============================================================\n"
)

print(
  TARGET_AUDIT
)



cat(
  "\n\n============================================================\n"
)

cat(
  "FEATURE COUNTS\n"
)

cat(
  "============================================================\n"
)

cat(
  "NQ_ONLY: ",
  length(
    NQ_FEATURES
  ),
  "\n",
  sep = ""
)


cat(
  "NQ_ES:   ",
  length(
    NQ_ES_FEATURES
  ),
  "\n",
  sep = ""
)



cat(
  "\n\n============================================================\n"
)

cat(
  "2026 USED IN DEVELOPMENT RANKING?\n"
)

cat(
  "============================================================\n"
)

print(
  USE_2026_IN_RANKING
)



cat(
  "\n\n============================================================\n"
)

cat(
  "DEVELOPMENT WALK-FORWARD CHAMPION\n"
)

cat(
  "============================================================\n"
)

print(
  CHAMPION
)



cat(
  "\n\n============================================================\n"
)

cat(
  "CHAMPION BY OOS FOLD\n"
)

cat(
  "============================================================\n"
)

print(
  CHAMPION_FOLDS
)



cat(
  "\n\n============================================================\n"
)

cat(
  "BEST CANDIDATE BY XGBOOST DEPTH\n"
)

cat(
  "============================================================\n"
)

print(
  XGB_DEPTH_COMPARISON
)



cat(
  "\n\n============================================================\n"
)

cat(
  "BEST NQ_ONLY VS NQ_ES\n"
)

cat(
  "============================================================\n"
)

print(
  BEST_FEATURE_SET
)



cat(
  "\n\n============================================================\n"
)

cat(
  "FEATURE ABLATION\n"
)

cat(
  "============================================================\n"
)

print(
  ABLATION_AGG
)



cat(
  "\n\n============================================================\n"
)

cat(
  "INTERPRETATION RULES\n"
)

cat(
  "============================================================\n"
)


cat(

  "- Technical indicators restart every futures session at 18:00 ET.\n",

  "- Technical indicators also restart after suspected contract-roll boundaries.\n",

  "- Unexpected missing-minute gaps also restart technical state.\n",

  "- Returns and volatility windows cannot cross state resets.\n",

  "- Prediction targets cannot cross suspected contract-roll boundaries.\n",

  "- RTH gaps are invalid if previous RTH close and current RTH open are in different roll segments.\n",

  "- First-30-minute variables remain unavailable until 10:00 ET.\n",

  "- 2023, 2024, 2025 and 2026 YTD are chronological OOS development folds.\n",

  "- Each test fold uses only earlier years for model estimation.\n",

  "- Confidence cutoffs are learned from the immediately preceding calibration year.\n",

  "- No test-year confidence percentile is used to select that year's observations.\n",

  "- Flats count as losses in evaluation.\n",

  "- Binary model training excludes flats.\n",

  "- Candidate inference uses week-block bootstrap.\n",

  "- Paired model edge is evaluated against the training-determined directional baseline on the same selected timestamps.\n",

  "- temporal_ok requires sufficient observations, non-overlapping targets, broad weekly activity and limited day concentration.\n",

  "- persistence_ok requires at least two of the three full OOS years 2023/2024/2025 above 50% WR.\n",

  "- statistically_robust additionally requires block lower WR > 50% and block lower paired edge > 0.\n",

  "- Because USE_2026_IN_RANKING=TRUE, 2026 is deliberately development-OOS rather than a pristine project-level holdout.\n",

  sep = ""
)



cat(
  "\n\n============================================================\n"
)

cat(
  "PRIMARY OUTPUT FILES\n"
)

cat(
  "============================================================\n"
)



primary_files <- c(

  "02_detected_roll_events.csv",

  "03_roll_detection_summary.csv",

  "06_largest_1m_moves_after_roll_flags.csv",

  "07_target_audit.csv",

  "08_walkforward_fold_results.csv",

  "09_walkforward_aggregate_all_candidates.csv",

  "10_top_stable_candidates.csv",

  "11_DEVELOPMENT_CHAMPION.csv",

  "12_best_candidate_by_xgb_depth.csv",

  "13_best_NQ_only_vs_NQ_ES.csv",

  "14_top_candidates_2026_YTD.csv",

  "15_champion_fold_results.csv",

  "16_champion_selected_predictions_all_folds.csv",

  "17_champion_by_session.csv",

  "18_champion_by_season.csv",

  "19_ablation_fold_results.csv",

  "20_ablation_aggregate.csv"
)



for (
  f in
  primary_files
) {

  cat(
    file.path(
      OUT,
      f
    ),
    "\n",
    sep = ""
  )
}



cat(
  "\n\n============================================================\n"
)

cat(
  "V5 COMPLETE\n"
)

cat(
  "============================================================\n"
)