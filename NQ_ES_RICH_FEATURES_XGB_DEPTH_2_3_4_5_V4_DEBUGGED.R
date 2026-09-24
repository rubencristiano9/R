# ==============================================================================
# NQ + ES DIRECTION SEARCH — RICH FEATURES + XGBOOST DEPTH 2/3/4/5 — DEBUGGED V4
#
# BIG-PICTURE GOAL
#   Maximize genuinely out-of-sample NQ UP/DOWN prediction accuracy.
#   Very low coverage is acceptable if accuracy improves.
#
# CHRONOLOGY
#   2019-2023 : train
#   2024      : select ONE model/horizon/feature-set/confidence cutoff
#   FREEZE
#   2025      : untouched confirmation
#   2026 YTD  : untouched recent continuation
#
# LABEL
#   At signal time T, predict whether NQ close at T+h is above/below NQ close at T.
#   Exact-flat outcomes count as LOSSES in evaluation.
#
# IMPORTANT
#   - Technical indicators are calculated with the CRAN TTR package.
#   - No H2O is used.
#   - 2025/2026 never refit, reselect, or recalibrate the 2024 champion.
#   - Session-specific features are masked until they are actually knowable.
# ==============================================================================


# ==============================================================================
# 0. SETTINGS
# ==============================================================================

SEED <- 1234L
set.seed(SEED)

NQ_NAME <- "NQ_1min_2010-06-07_to_2026-03-13_databento.csv"
ES_NAME <- "ES_1min_2010-06-07_to_2026-03-13_databento.csv"

NQ_FILE <- if (file.exists(NQ_NAME)) {
  normalizePath(NQ_NAME)
} else {
  message("Choose NQ CSV...")
  file.choose()
}

ES_GUESS <- file.path(dirname(NQ_FILE), ES_NAME)
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
  "nq_es_rich_features_xgb_depth_2_3_4_5_v4"
)
dir.create(OUT, recursive = TRUE, showWarnings = FALSE)

HORIZONS <- c(1L, 3L, 5L, 7L, 10L, 15L, 30L, 60L)
COVERAGES <- c(.50, .20, .10, .05, .02, .01, .005)

MIN_VALID_N <- 100L
MIN_VALID_WEEKS <- 8L
BOOT_REPS <- 2000L

TRAIN_START <- as.Date("2019-01-01")
TRAIN_END   <- as.Date("2024-01-01")
VALID_START <- as.Date("2024-01-01")
VALID_END   <- as.Date("2025-01-01")
TEST25_START <- as.Date("2025-01-01")
TEST25_END   <- as.Date("2026-01-01")
TEST26_START <- as.Date("2026-01-01")
TEST26_END   <- as.Date("2027-01-01")

# Session definitions are explicit and easy to edit.
# These are local CASH-market windows; the flags may overlap.
ASIA_START_TOKYO <- 9L * 60L
ASIA_END_TOKYO   <- 15L * 60L + 30L
LONDON_START_LOCAL <- 8L * 60L
LONDON_END_LOCAL   <- 16L * 60L + 30L
US_RTH_START_ET <- 9L * 60L + 30L
US_RTH_END_ET   <- 16L * 60L


# ==============================================================================
# 1. PACKAGE / API CHECKS
# ==============================================================================

needed <- c("data.table", "lubridate", "TTR", "ranger", "xgboost")
missing <- needed[
  !vapply(needed, requireNamespace, logical(1), quietly = TRUE)
]

if (length(missing) > 0L) {
  stop(
    "Missing package(s): ",
    paste(missing, collapse = ", "),
    "\nInstall with install.packages()."
  )
}

stopifnot(
  all(c(
    "fread", "fwrite", "setorder", "setnames", "shift",
    "frollsum", "frollmean", "fifelse"
  ) %in% getNamespaceExports("data.table")),

  all(c(
    "with_tz", "hour", "minute", "wday"
  ) %in% getNamespaceExports("lubridate")),

  all(c(
    "RSI", "MACD", "BBands", "VWAP", "EMA", "SMA",
    "ADX", "DonchianChannel"
  ) %in% getNamespaceExports("TTR")),

  "ranger" %in% getNamespaceExports("ranger"),

  all(c(
    "xgb.DMatrix", "xgb.params", "xgb.train"
  ) %in% getNamespaceExports("xgboost"))
)

PACKAGE_VERSIONS <- data.table::data.table(
  package = needed,
  version = vapply(
    needed,
    function(z) as.character(utils::packageVersion(z)),
    character(1)
  )
)

data.table::fwrite(
  PACKAGE_VERSIONS,
  file.path(OUT, "00_package_versions.csv")
)


# ==============================================================================
# 2. READ + EXACT NQ/ES ALIGNMENT
# ==============================================================================

read_market <- function(file, prefix) {
  x <- data.table::fread(
    file,
    select = c("timestamp", "open", "high", "low", "close", "volume"),
    colClasses = list(character = "timestamp"),
    showProgress = TRUE
  )

  x[, ts := as.POSIXct(
    substr(timestamp, 1L, 19L),
    format = "%Y-%m-%d %H:%M:%S",
    tz = "UTC"
  )]

  if (anyNA(x$ts)) stop(prefix, ": timestamp parse failure")

  # 2019 training start + warm-up for indicators.
  x <- x[ts >= as.POSIXct("2018-11-01 00:00:00", tz = "UTC")]

  data.table::setorder(x, ts)
  if (anyDuplicated(x$ts)) stop(prefix, ": duplicate timestamps")

  data.table::setnames(
    x,
    c("open", "high", "low", "close", "volume"),
    paste0(prefix, c("_open", "_high", "_low", "_close", "_volume"))
  )

  x[, timestamp := NULL]
  x
}

message("Reading NQ...")
NQ <- read_market(NQ_FILE, "nq")

message("Reading ES...")
ES <- read_market(ES_FILE, "es")

ALIGNMENT <- data.table::data.table(
  nq_rows = nrow(NQ),
  es_rows = nrow(ES)
)

# Exact timestamp join only. No forward fill / rolling join.
D <- merge(NQ, ES, by = "ts", all = FALSE, sort = TRUE)

ALIGNMENT[, `:=`(
  exact_common_rows = nrow(D),
  nq_common_fraction = nrow(D) / nq_rows,
  es_common_fraction = nrow(D) / es_rows
)]

data.table::fwrite(
  ALIGNMENT,
  file.path(OUT, "01_alignment_audit.csv")
)

rm(NQ, ES)
invisible(gc())

D[, row_id := .I]
D[, ts_num := as.numeric(ts)]
D[, ts_et := lubridate::with_tz(ts, "America/New_York")]


# ==============================================================================
# 3. CLOCKS, SESSION FLAGS, SIGNAL TIME
# ==============================================================================

is_nq_open <- function(x) {
  dow <- lubridate::wday(x, week_start = 1L)
  m <- lubridate::hour(x) * 60L + lubridate::minute(x)

  (dow %in% 1:4 & (m < 1020L | m >= 1080L)) |
    (dow == 5L & m < 1020L) |
    (dow == 7L & m >= 1080L)
}

# Databento 1m timestamp = START of bar; bar is complete one minute later.
D[, signal_ts_num := ts_num + 60]
D[, signal_utc := as.POSIXct(
  signal_ts_num,
  origin = "1970-01-01",
  tz = "UTC"
)]
D[, signal_et := lubridate::with_tz(signal_utc, "America/New_York")]
D[, signal_london := lubridate::with_tz(signal_utc, "Europe/London")]
D[, signal_tokyo := lubridate::with_tz(signal_utc, "Asia/Tokyo")]

D[, signal_date := as.Date(signal_et, tz = "America/New_York")]
D[, signal_minute := lubridate::hour(signal_et) * 60L + lubridate::minute(signal_et)]
D[, signal_dow := lubridate::wday(signal_et, week_start = 1L)]

D[, london_minute := lubridate::hour(signal_london) * 60L +
                     lubridate::minute(signal_london)]
D[, tokyo_minute := lubridate::hour(signal_tokyo) * 60L +
                    lubridate::minute(signal_tokyo)]

D[, asia_session := as.integer(
  tokyo_minute >= ASIA_START_TOKYO &
  tokyo_minute < ASIA_END_TOKYO
)]

D[, london_session := as.integer(
  london_minute >= LONDON_START_LOCAL &
  london_minute < LONDON_END_LOCAL
)]

D[, us_rth_session := as.integer(
  signal_minute >= US_RTH_START_ET &
  signal_minute < US_RTH_END_ET
)]

D[, london_us_overlap := london_session * us_rth_session]

D[, us_last60 := as.integer(
  signal_minute >= 15L * 60L &
  signal_minute < US_RTH_END_ET
)]

D[, us_last30 := as.integer(
  signal_minute >= 15L * 60L + 30L &
  signal_minute < US_RTH_END_ET
)]

D[, minutes_to_us_close := data.table::fifelse(
  us_rth_session == 1L,
  US_RTH_END_ET - signal_minute,
  0L
)]

D[, bar_date_et := as.Date(ts_et, tz = "America/New_York")]
D[, bar_minute_et := lubridate::hour(ts_et) * 60L + lubridate::minute(ts_et)]
D[, bar_dow := lubridate::wday(ts_et, week_start = 1L)]

D[, is_us_rth_bar := (
  bar_dow %in% 1:5 &
  bar_minute_et >= US_RTH_START_ET &
  bar_minute_et < US_RTH_END_ET
)]

D[, bar_start_open := is_nq_open(ts_et)]
D[, signal_open := is_nq_open(signal_et)]


# ==============================================================================
# 4. PRICE / VOLATILITY FEATURES
# ==============================================================================

exact_return <- function(price, tsnum, k) {
  old_price <- data.table::shift(price, k)
  old_ts <- data.table::shift(tsnum, k)
  z <- rep(NA_real_, length(price))
  ok <- !is.na(old_ts) & (tsnum - old_ts == 60 * k)
  z[ok] <- log(price[ok] / old_price[ok])
  z
}

rolling_rv <- function(ret1, tsnum, k) {
  z <- sqrt(data.table::frollsum(
    ret1^2,
    n = k,
    align = "right",
    fill = NA_real_
  ))
  old_ts <- data.table::shift(tsnum, k - 1L)
  z[is.na(old_ts) | (tsnum - old_ts != 60 * (k - 1L))] <- NA_real_
  z
}

rolling_rs <- function(o, h, l, c, tsnum, k) {
  rs_term <- log(h / c) * log(h / o) +
             log(l / c) * log(l / o)

  z <- sqrt(pmax(
    data.table::frollsum(
      rs_term,
      n = k,
      align = "right",
      fill = NA_real_
    ) / k,
    0
  ))

  old_ts <- data.table::shift(tsnum, k - 1L)
  z[is.na(old_ts) | (tsnum - old_ts != 60 * (k - 1L))] <- NA_real_
  z
}

D[, nq_bar_ret := log(nq_close / nq_open)]
D[, nq_range := (nq_high - nq_low) / nq_close]
D[, nq_close_loc := data.table::fifelse(
  nq_high > nq_low,
  (nq_close - nq_low) / (nq_high - nq_low),
  0.5
)]

D[, es_bar_ret := log(es_close / es_open)]
D[, es_range := (es_high - es_low) / es_close]
D[, es_close_loc := data.table::fifelse(
  es_high > es_low,
  (es_close - es_low) / (es_high - es_low),
  0.5
)]

for (k in c(1L, 2L, 5L, 15L, 30L, 60L)) {
  D[, (paste0("nq_ret", k)) := exact_return(nq_close, ts_num, k)]
  D[, (paste0("es_ret", k)) := exact_return(es_close, ts_num, k)]
}

for (k in c(5L, 15L, 60L)) {
  D[, (paste0("nq_rv", k)) := rolling_rv(nq_ret1, ts_num, k)]
  D[, (paste0("es_rv", k)) := rolling_rv(es_ret1, ts_num, k)]
}

for (k in c(15L, 60L)) {
  D[, (paste0("nq_rs", k)) := rolling_rs(
    nq_open, nq_high, nq_low, nq_close, ts_num, k
  )]

  D[, (paste0("es_rs", k)) := rolling_rs(
    es_open, es_high, es_low, es_close, ts_num, k
  )]
}

# Volatility-regime ratios.
D[, nq_rv5_over_60 := nq_rv5 / nq_rv60]
D[, nq_rs15_over_60 := nq_rs15 / nq_rs60]
D[, es_rv5_over_60 := es_rv5 / es_rv60]
D[, es_rs15_over_60 := es_rs15 / es_rs60]


# ==============================================================================
# 5. TECHNICAL INDICATORS — TTR PACKAGE
# ==============================================================================

add_ttr_features <- function(D, prefix) {
  close <- D[[paste0(prefix, "_close")]]
  high <- D[[paste0(prefix, "_high")]]
  low <- D[[paste0(prefix, "_low")]]
  volume <- D[[paste0(prefix, "_volume")]]

  HLC <- cbind(High = high, Low = low, Close = close)
  HL <- cbind(High = high, Low = low)

  # RSI(14)
  data.table::set(
    D,
    j = paste0(prefix, "_rsi14"),
    value = as.numeric(TTR::RSI(close, n = 14))
  )

  # MACD(12,26,9), expressed as percentage differences for scale stability.
  macd <- TTR::MACD(
    close,
    nFast = 12,
    nSlow = 26,
    nSig = 9,
    percent = TRUE
  )

  data.table::set(
    D,
    j = paste0(prefix, "_macd"),
    value = as.numeric(macd[, "macd"])
  )

  data.table::set(
    D,
    j = paste0(prefix, "_macd_signal"),
    value = as.numeric(macd[, "signal"])
  )

  data.table::set(
    D,
    j = paste0(prefix, "_macd_hist"),
    value = as.numeric(macd[, "macd"] - macd[, "signal"])
  )

  # Bollinger Bands(20,2).
  bb <- TTR::BBands(HLC, n = 20, sd = 2)

  data.table::set(
    D,
    j = paste0(prefix, "_bb_pctB"),
    value = as.numeric(bb[, "pctB"])
  )

  data.table::set(
    D,
    j = paste0(prefix, "_bb_width"),
    value = as.numeric((bb[, "up"] - bb[, "dn"]) / bb[, "mavg"])
  )

  # Rolling VWAP(20), distinct from the reset-at-09:30 session VWAP below.
  vwap20 <- as.numeric(TTR::VWAP(close, volume, n = 20))
  data.table::set(
    D,
    j = paste0(prefix, "_vwap20_dist"),
    value = close / vwap20 - 1
  )

  # Moving-average state.
  ema20 <- as.numeric(TTR::EMA(close, n = 20))
  ema60 <- as.numeric(TTR::EMA(close, n = 60))

  data.table::set(
    D,
    j = paste0(prefix, "_ema20_dist"),
    value = close / ema20 - 1
  )

  data.table::set(
    D,
    j = paste0(prefix, "_ema60_dist"),
    value = close / ema60 - 1
  )

  data.table::set(
    D,
    j = paste0(prefix, "_ema20_60_spread"),
    value = ema20 / ema60 - 1
  )

  # ADX / directional movement.
  adx <- TTR::ADX(HLC, n = 14)

  data.table::set(
    D,
    j = paste0(prefix, "_adx14"),
    value = as.numeric(adx[, "ADX"])
  )

  data.table::set(
    D,
    j = paste0(prefix, "_di_spread14"),
    value = as.numeric(adx[, "DIp"] - adx[, "DIn"])
  )

  # Donchian channel uses PRIOR bars only (include.lag=TRUE).
  dc <- TTR::DonchianChannel(
    HL,
    n = 20,
    include.lag = TRUE
  )

  dc_high <- as.numeric(dc[, "high"])
  dc_low <- as.numeric(dc[, "low"])

  dc_pos <- data.table::fifelse(
    dc_high > dc_low,
    (close - dc_low) / (dc_high - dc_low),
    0.5
  )

  data.table::set(
    D,
    j = paste0(prefix, "_donchian20_pos"),
    value = dc_pos
  )

  data.table::set(
    D,
    j = paste0(prefix, "_breakout20_up"),
    value = as.integer(close > dc_high)
  )

  data.table::set(
    D,
    j = paste0(prefix, "_breakout20_down"),
    value = as.integer(close < dc_low)
  )

  # Relative activity using TTR moving averages.
  vol_sma15 <- as.numeric(TTR::SMA(volume, n = 15))
  vol_sma60 <- as.numeric(TTR::SMA(volume, n = 60))

  data.table::set(
    D,
    j = paste0(prefix, "_vol_rel15"),
    value = volume / vol_sma15
  )

  data.table::set(
    D,
    j = paste0(prefix, "_vol_rel60"),
    value = volume / vol_sma60
  )

  invisible(NULL)
}

add_ttr_features(D, "nq")
add_ttr_features(D, "es")


# ==============================================================================
# 6. RTH SESSION-TO-DATE STATE
# ==============================================================================

# These use only completed RTH bars up to the current row.
D[, `:=`(
  nq_rth_to_now = 0,
  es_rth_to_now = 0,
  nq_rth_vwap_dist = 0,
  es_rth_vwap_dist = 0,
  nq_rth_position = 0,
  es_rth_position = 0
)]

D[
  is_us_rth_bar == TRUE,
  nq_rth_to_now := log(nq_close / nq_open[1L]),
  by = bar_date_et
]

D[
  is_us_rth_bar == TRUE,
  es_rth_to_now := log(es_close / es_open[1L]),
  by = bar_date_et
]

D[
  is_us_rth_bar == TRUE,
  nq_rth_vwap_dist := {
    typical <- (nq_high + nq_low + nq_close) / 3
    svwap <- cumsum(typical * nq_volume) / cumsum(nq_volume)
    nq_close / svwap - 1
  },
  by = bar_date_et
]

D[
  is_us_rth_bar == TRUE,
  es_rth_vwap_dist := {
    typical <- (es_high + es_low + es_close) / 3
    svwap <- cumsum(typical * es_volume) / cumsum(es_volume)
    es_close / svwap - 1
  },
  by = bar_date_et
]

D[
  is_us_rth_bar == TRUE,
  nq_rth_position := {
    hh <- cummax(nq_high)
    ll <- cummin(nq_low)
    ifelse(hh > ll, (nq_close - ll) / (hh - ll), 0.5)
  },
  by = bar_date_et
]

D[
  is_us_rth_bar == TRUE,
  es_rth_position := {
    hh <- cummax(es_high)
    ll <- cummin(es_low)
    ifelse(hh > ll, (es_close - ll) / (hh - ll), 0.5)
  },
  by = bar_date_et
]


# ==============================================================================
# 7. RTH OPENING GAP + FIRST 30 MINUTES + LAST COMPLETED RTH
# ==============================================================================

# Daily RTH summaries. We explicitly record whether the true 09:30 bar exists.
RTH_DAILY <- D[
  is_us_rth_bar == TRUE,
  .(
    rth_open_minute = bar_minute_et[1L],
    rth_last_minute = bar_minute_et[.N],
    rth_last_bar_ts_num = ts_num[.N],
    rth_bar_n = .N,

    nq_rth_open = nq_open[1L],
    nq_rth_close = nq_close[.N],
    nq_rth_high = max(nq_high, na.rm = TRUE),
    nq_rth_low = min(nq_low, na.rm = TRUE),

    es_rth_open = es_open[1L],
    es_rth_close = es_close[.N],
    es_rth_high = max(es_high, na.rm = TRUE),
    es_rth_low = min(es_low, na.rm = TRUE),

    first30_n = sum(
      bar_minute_et >= US_RTH_START_ET &
      bar_minute_et < 10L * 60L
    ),

    nq_first30_close = {
      ii <- match(10L * 60L - 1L, bar_minute_et)
      if (is.na(ii)) NA_real_ else nq_close[ii]
    },

    es_first30_close = {
      ii <- match(10L * 60L - 1L, bar_minute_et)
      if (is.na(ii)) NA_real_ else es_close[ii]
    },

    nq_first30_high = {
      z <- nq_high[
        bar_minute_et >= US_RTH_START_ET &
        bar_minute_et < 10L * 60L
      ]
      if (length(z)) max(z, na.rm = TRUE) else NA_real_
    },

    nq_first30_low = {
      z <- nq_low[
        bar_minute_et >= US_RTH_START_ET &
        bar_minute_et < 10L * 60L
      ]
      if (length(z)) min(z, na.rm = TRUE) else NA_real_
    },

    nq_first30_volume = {
      z <- nq_volume[
        bar_minute_et >= US_RTH_START_ET &
        bar_minute_et < 10L * 60L
      ]
      if (length(z)) sum(z, na.rm = TRUE) else NA_real_
    },

    es_first30_high = {
      z <- es_high[
        bar_minute_et >= US_RTH_START_ET &
        bar_minute_et < 10L * 60L
      ]
      if (length(z)) max(z, na.rm = TRUE) else NA_real_
    },

    es_first30_low = {
      z <- es_low[
        bar_minute_et >= US_RTH_START_ET &
        bar_minute_et < 10L * 60L
      ]
      if (length(z)) min(z, na.rm = TRUE) else NA_real_
    },

    es_first30_volume = {
      z <- es_volume[
        bar_minute_et >= US_RTH_START_ET &
        bar_minute_et < 10L * 60L
      ]
      if (length(z)) sum(z, na.rm = TRUE) else NA_real_
    }
  ),
  by = .(rth_date = bar_date_et)
]

data.table::setorder(RTH_DAILY, rth_date)

# A gap requires the true 09:30 bar. First-30-minute features require all 30 bars.
RTH_DAILY[, rth_open_valid := (rth_open_minute == US_RTH_START_ET)]

RTH_DAILY[
  rth_open_valid == FALSE,
  `:=`(
    nq_rth_open = NA_real_,
    es_rth_open = NA_real_
  )
]

RTH_DAILY[
  first30_n != 30L | rth_open_valid == FALSE,
  `:=`(
    nq_first30_close = NA_real_,
    es_first30_close = NA_real_,
    nq_first30_high = NA_real_,
    nq_first30_low = NA_real_,
    nq_first30_volume = NA_real_,
    es_first30_high = NA_real_,
    es_first30_low = NA_real_,
    es_first30_volume = NA_real_
  )
]

# Previous RTH close is required for today's opening gap / previous-close-to-10:00.
RTH_DAILY[, nq_prev_rth_close := data.table::shift(nq_rth_close)]
RTH_DAILY[, es_prev_rth_close := data.table::shift(es_rth_close)]

RTH_DAILY[, nq_rth_gap := log(nq_rth_open / nq_prev_rth_close)]
RTH_DAILY[, es_rth_gap := log(es_rth_open / es_prev_rth_close)]

# 09:30 open -> 09:59 close, available at 10:00.
RTH_DAILY[, nq_open30_ret := log(nq_first30_close / nq_rth_open)]
RTH_DAILY[, es_open30_ret := log(es_first30_close / es_rth_open)]

RTH_DAILY[, nq_open30_green := as.integer(nq_open30_ret > 0)]
RTH_DAILY[, es_open30_green := as.integer(es_open30_ret > 0)]

RTH_DAILY[, nq_open30_range :=
  (nq_first30_high - nq_first30_low) / nq_rth_open]
RTH_DAILY[, es_open30_range :=
  (es_first30_high - es_first30_low) / es_rth_open]

# Gao-style first-half-hour return: previous RTH close -> 10:00.
RTH_DAILY[, nq_prevclose_to_1000 :=
  log(nq_first30_close / nq_prev_rth_close)]
RTH_DAILY[, es_prevclose_to_1000 :=
  log(es_first30_close / es_prev_rth_close)]

# Relative first-30-minute volume: prior 20 DAILY observations only.
# data.table rolling means tolerate missing rows without TTR's non-leading-NA issue.
RTH_DAILY[, nq_open30_vol_avg20_prior :=
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

RTH_DAILY[, es_open30_vol_avg20_prior :=
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

RTH_DAILY[, nq_open30_vol_rel20 :=
  nq_first30_volume / nq_open30_vol_avg20_prior]
RTH_DAILY[, es_open30_vol_rel20 :=
  es_first30_volume / es_open30_vol_avg20_prior]

# Today's gap/opening-30 variables are attached by NY calendar date,
# then masked until the information is actually available.
TODAY_RTH_FEATURES <- RTH_DAILY[
  ,
  .(
    signal_date = rth_date,
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
data.table::setorder(D, ts)
D[, row_id := .I]

# Attach the MOST RECENT COMPLETED RTH return/range by availability time.
# This fixes the post-16:00 problem in a simple calendar-date merge.
RTH_DAILY[, rth_available_ts_num := rth_last_bar_ts_num + 60]

RTH_DAILY[, nq_completed_rth_ret := log(nq_rth_close / nq_rth_open)]
RTH_DAILY[, es_completed_rth_ret := log(es_rth_close / es_rth_open)]

RTH_DAILY[, nq_completed_rth_range :=
  (nq_rth_high - nq_rth_low) / nq_rth_open]
RTH_DAILY[, es_completed_rth_range :=
  (es_rth_high - es_rth_low) / es_rth_open]

# If the true RTH open is unavailable, do not treat the day's full-session
# return/range as valid.
RTH_DAILY[
  rth_open_valid == FALSE,
  `:=`(
    nq_completed_rth_ret = NA_real_,
    es_completed_rth_ret = NA_real_,
    nq_completed_rth_range = NA_real_,
    es_completed_rth_range = NA_real_
  )
]

last_rth_idx <- findInterval(
  D$signal_ts_num,
  RTH_DAILY$rth_available_ts_num
)

D[, nq_last_rth_ret := NA_real_]
D[, es_last_rth_ret := NA_real_]
D[, nq_last_rth_range := NA_real_]
D[, es_last_rth_range := NA_real_]

has_last_rth <- last_rth_idx > 0L

D[has_last_rth == TRUE, nq_last_rth_ret :=
  RTH_DAILY$nq_completed_rth_ret[last_rth_idx[has_last_rth]]]
D[has_last_rth == TRUE, es_last_rth_ret :=
  RTH_DAILY$es_completed_rth_ret[last_rth_idx[has_last_rth]]]
D[has_last_rth == TRUE, nq_last_rth_range :=
  RTH_DAILY$nq_completed_rth_range[last_rth_idx[has_last_rth]]]
D[has_last_rth == TRUE, es_last_rth_range :=
  RTH_DAILY$es_completed_rth_range[last_rth_idx[has_last_rth]]]

D[, last_rth_known := as.integer(
  is.finite(nq_last_rth_ret) &
  is.finite(es_last_rth_ret)
)]

# Under the conservative completed-bar convention, today's 09:30 opening gap
# is used only after the 09:30 bar has begun. With the 15-minute signal grid,
# its first practical signal is 09:45.
D[, rth_gap_known := as.integer(
  is.finite(nq_rth_gap) &
  is.finite(es_rth_gap) &
  signal_minute >= (US_RTH_START_ET + 1L)
)]

# The 09:30-09:59 opening block is complete at 10:00.
D[, opening30_known := as.integer(
  is.finite(nq_open30_ret) &
  is.finite(es_open30_ret) &
  signal_minute >= 10L * 60L
)]

last_rth_cols <- c(
  "nq_last_rth_ret", "nq_last_rth_range",
  "es_last_rth_ret", "es_last_rth_range"
)

gap_cols <- c("nq_rth_gap", "es_rth_gap")

open30_cols <- c(
  "nq_open30_ret", "nq_open30_green", "nq_open30_range",
  "nq_open30_vol_rel20", "nq_prevclose_to_1000",
  "es_open30_ret", "es_open30_green", "es_open30_range",
  "es_open30_vol_rel20", "es_prevclose_to_1000"
)

for (v in last_rth_cols) {
  D[last_rth_known == 0L | !is.finite(get(v)), (v) := 0]
}
for (v in gap_cols) {
  D[rth_gap_known == 0L | !is.finite(get(v)), (v) := 0]
}
for (v in open30_cols) {
  D[opening30_known == 0L | !is.finite(get(v)), (v) := 0]
}

# Cross-market RTH opening information.
D[, nq_minus_es_gap := nq_rth_gap - es_rth_gap]
D[, nq_minus_es_open30 := nq_open30_ret - es_open30_ret]
D[, open30_disagree := as.integer(
  opening30_known == 1L &
  sign(nq_open30_ret) != sign(es_open30_ret)
)]


# ==============================================================================
# 8. OTHER CROSS-MARKET + CALENDAR FEATURES
# ==============================================================================

for (k in c(1L, 5L, 15L, 60L)) {
  nq_col <- paste0("nq_ret", k)
  es_col <- paste0("es_ret", k)

  D[, (paste0("nq_minus_es_", k)) :=
      get(nq_col) - get(es_col)]
}

for (k in c(1L, 5L, 15L)) {
  nq_col <- paste0("nq_ret", k)
  es_col <- paste0("es_ret", k)

  D[, (paste0("disagree_", k)) := as.integer(
    sign(get(nq_col)) != sign(get(es_col))
  )]
}

D[, tod_sin := sin(2 * pi * signal_minute / 1440)]
D[, tod_cos := cos(2 * pi * signal_minute / 1440)]

for (dd in c(2L, 3L, 4L, 5L, 7L)) {
  D[, (paste0("dow_", dd)) := as.integer(signal_dow == dd)]
}

month_num <- as.integer(format(D$signal_date, "%m"))

D[, season := data.table::fifelse(
  month_num %in% c(12L, 1L, 2L), "winter",
  data.table::fifelse(
    month_num %in% 3:5, "spring",
    data.table::fifelse(
      month_num %in% 6:8, "summer", "autumn"
    )
  )
)]

D[, season_spring := as.integer(season == "spring")]
D[, season_summer := as.integer(season == "summer")]
D[, season_autumn := as.integer(season == "autumn")]


# ==============================================================================
# 9. FEATURE SETS
# ==============================================================================

NQ_TECH <- c(
  "nq_rsi14",
  "nq_macd", "nq_macd_signal", "nq_macd_hist",
  "nq_bb_pctB", "nq_bb_width",
  "nq_vwap20_dist",
  "nq_ema20_dist", "nq_ema60_dist", "nq_ema20_60_spread",
  "nq_adx14", "nq_di_spread14",
  "nq_donchian20_pos", "nq_breakout20_up", "nq_breakout20_down",
  "nq_vol_rel15", "nq_vol_rel60"
)

ES_TECH <- c(
  "es_rsi14",
  "es_macd", "es_macd_signal", "es_macd_hist",
  "es_bb_pctB", "es_bb_width",
  "es_vwap20_dist",
  "es_ema20_dist", "es_ema60_dist", "es_ema20_60_spread",
  "es_adx14", "es_di_spread14",
  "es_donchian20_pos", "es_breakout20_up", "es_breakout20_down",
  "es_vol_rel15", "es_vol_rel60"
)

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

NQ_FEATURES <- c(
  "nq_bar_ret", "nq_range", "nq_close_loc",

  paste0("nq_ret", c(1, 2, 5, 15, 30, 60)),
  paste0("nq_rv", c(5, 15, 60)),
  paste0("nq_rs", c(15, 60)),
  "nq_rv5_over_60",
  "nq_rs15_over_60",

  NQ_TECH,
  COMMON_SESSION,
  NQ_SESSION_STATE,

  "tod_sin", "tod_cos",
  paste0("dow_", c(2, 3, 4, 5, 7)),
  "season_spring", "season_summer", "season_autumn"
)

NQ_ES_FEATURES <- c(
  NQ_FEATURES,

  "es_bar_ret", "es_range", "es_close_loc",

  paste0("es_ret", c(1, 2, 5, 15, 30, 60)),
  paste0("es_rv", c(5, 15, 60)),
  paste0("es_rs", c(15, 60)),
  "es_rv5_over_60",
  "es_rs15_over_60",

  ES_TECH,
  ES_SESSION_STATE,

  paste0("nq_minus_es_", c(1, 5, 15, 60)),
  paste0("disagree_", c(1, 5, 15)),

  "nq_minus_es_gap",
  "nq_minus_es_open30",
  "open30_disagree"
)

FEATURE_SETS <- list(
  NQ_ONLY = NQ_FEATURES,
  NQ_ES = NQ_ES_FEATURES
)

# complete.cases() does NOT remove +/-Inf. Sanitize every model feature first.
for (v in NQ_ES_FEATURES) {
  bad <- which(!is.finite(D[[v]]))
  if (length(bad)) {
    data.table::set(D, i = bad, j = v, value = NA_real_)
  }
}

FEATURE_MANIFEST <- data.table::rbindlist(list(
  data.table::data.table(
    feature_set = "NQ_ONLY",
    feature = NQ_FEATURES
  ),
  data.table::data.table(
    feature_set = "NQ_ES",
    feature = NQ_ES_FEATURES
  )
))

data.table::fwrite(
  FEATURE_MANIFEST,
  file.path(OUT, "02_feature_manifest.csv")
)

SESSION_AUDIT <- D[
  signal_minute %% 15L == 0L &
  bar_start_open &
  signal_open,
  .(
    candidate_signal_rows = .N,
    asia_rows = sum(asia_session),
    london_rows = sum(london_session),
    us_rth_rows = sum(us_rth_session),
    us_last60_rows = sum(us_last60),
    gap_known_rows = sum(rth_gap_known),
    opening30_known_rows = sum(opening30_known)
  )
]

data.table::fwrite(
  SESSION_AUDIT,
  file.path(OUT, "03_session_feature_audit.csv")
)

# Unadjusted continuous contracts can jump around roll transitions.
JUMP_AUDIT <- head(
  D[
    signal_date >= TRAIN_START,
    .(
      signal_et,
      nq_ret1,
      es_ret1,
      max_abs_1m = pmax(abs(nq_ret1), abs(es_ret1))
    )
  ][order(-max_abs_1m)],
  200L
)

data.table::fwrite(
  JUMP_AUDIT,
  file.path(OUT, "04_largest_1m_moves_roll_audit.csv")
)


# ==============================================================================
# 10. SIGNAL GRID + EXACT TARGETS
# ==============================================================================

lookup_ts <- D$ts_num
lookup_close <- D$nq_close
lookup_row <- D$row_id

# Keep only columns needed downstream before making one copy per horizon.
SIG_COLS <- unique(c(
  "ts_num", "row_id", "signal_ts_num", "signal_et", "signal_date",
  "signal_minute", "season", "nq_close", NQ_ES_FEATURES
))

SIG <- D[
  signal_minute %% 15L == 0L &
  bar_start_open &
  signal_open,
  ..SIG_COLS
]

SAMPLES <- list()
target_audits <- list()

for (h in HORIZONS) {
  S <- data.table::copy(SIG)

  # T = ts + 1m. Close known at T+h is the close of bar starting at ts+h.
  endpoint_idx <- match(S$ts_num + 60 * h, lookup_ts)

  S[, endpoint_row := lookup_row[endpoint_idx]]
  S[, future_close := lookup_close[endpoint_idx]]
  S[, forecast_end_ts_num := signal_ts_num + 60 * h]

  end_et <- lubridate::with_tz(
    as.POSIXct(
      S$forecast_end_ts_num,
      origin = "1970-01-01",
      tz = "UTC"
    ),
    "America/New_York"
  )

  S[, forecast_end_date := as.Date(end_et, tz = "America/New_York")]

  # Require every intervening common NQ/ES minute to exist.
  S[, target_contiguous :=
      !is.na(endpoint_row) &
      (endpoint_row - row_id == h)]

  S[, endpoint_open := is_nq_open(end_et)]

  S[, outcome := data.table::fifelse(
    is.na(future_close),
    NA_integer_,
    data.table::fifelse(
      future_close > nq_close, 1L,
      data.table::fifelse(
        future_close < nq_close, -1L, 0L
      )
    )
  )]

  candidate_n <- nrow(S)
  missing_n <- sum(is.na(S$future_close))
  broken_n <- sum(!is.na(S$future_close) & !S$target_contiguous)

  # Same complete-case universe for NQ_ONLY and NQ_ES -> fair comparison.
  S <- S[
    target_contiguous &
    endpoint_open &
    !is.na(outcome) &
    complete.cases(S[, ..NQ_ES_FEATURES])
  ]

  S[, week_id := format(signal_date, "%G-%V")]
  S[, horizon := h]

  if (any(S$forecast_end_ts_num - S$signal_ts_num != 60 * h)) {
    stop("Target timing failure at h=", h)
  }

  SAMPLES[[as.character(h)]] <- S

  target_audits[[as.character(h)]] <- data.table::data.table(
    horizon = h,
    candidate_signals = candidate_n,
    missing_exact_endpoint = missing_n,
    discontinuous_target = broken_n,
    retained = nrow(S),
    flat_n = sum(S$outcome == 0L),
    flat_rate = mean(S$outcome == 0L)
  )
}

TARGET_AUDIT <- data.table::rbindlist(target_audits)

data.table::fwrite(
  TARGET_AUDIT,
  file.path(OUT, "05_target_audit.csv")
)

rm(D, SIG, lookup_ts, lookup_close, lookup_row, TODAY_RTH_FEATURES, RTH_DAILY)
invisible(gc())


# ==============================================================================
# 11. MODELS
# ==============================================================================

MODEL_SPECS <- list(
  logit = list(type = "logit"),
  ranger = list(type = "ranger"),
  xgb_d2 = list(type = "xgboost", depth = 2L),
  xgb_d3 = list(type = "xgboost", depth = 3L),
  xgb_d4 = list(type = "xgboost", depth = 4L),
  xgb_d5 = list(type = "xgboost", depth = 5L)
)

MODEL_IDS <- names(MODEL_SPECS)

fit_model <- function(train, features, model_id) {
  spec <- MODEL_SPECS[[model_id]]
  if (is.null(spec)) stop("Unknown model_id: ", model_id)

  x <- as.data.frame(train[, ..features])
  y <- as.integer(train$outcome == 1L)

  if (spec$type == "logit") {
    dat <- data.frame(y = y, x, check.names = FALSE)

    return(list(
      id = model_id,
      type = "logit",
      depth = NA_integer_,
      fit = stats::glm(
        y ~ .,
        data = dat,
        family = stats::binomial()
      )
    ))
  }

  if (spec$type == "ranger") {
    dat <- data.frame(
      y = factor(
        ifelse(train$outcome == 1L, "UP", "DOWN"),
        levels = c("DOWN", "UP")
      ),
      x,
      check.names = FALSE
    )

    fit <- ranger::ranger(
      y ~ .,
      data = dat,
      probability = TRUE,
      num.trees = 500,
      mtry = max(1L, floor(sqrt(length(features)))),
      min.node.size = 50,
      max.depth = 8,
      importance = "none",
      num.threads = 0,
      seed = SEED,
      verbose = FALSE
    )

    return(list(
      id = model_id,
      type = "ranger",
      depth = NA_integer_,
      fit = fit
    ))
  }

  dtrain <- xgboost::xgb.DMatrix(
    data = as.matrix(x),
    label = y
  )

  params <- xgboost::xgb.params(
    objective = "binary:logistic",
    eval_metric = "logloss",
    max_depth = spec$depth,
    eta = 0.05,
    min_child_weight = 30,
    subsample = 0.8,
    colsample_bytree = 0.8,
    tree_method = "hist",
    nthread = 0,
    seed = SEED
  )

  list(
    id = model_id,
    type = "xgboost",
    depth = spec$depth,
    fit = xgboost::xgb.train(
      params = params,
      data = dtrain,
      nrounds = 150L,
      verbose = 0
    )
  )
}

predict_model <- function(model, newdata, features) {
  x <- as.data.frame(newdata[, ..features])

  if (model$type == "logit") {
    p <- as.numeric(stats::predict(
      model$fit,
      newdata = x,
      type = "response"
    ))
  } else if (model$type == "ranger") {
    pr <- predict(
      model$fit,
      data = x,
      num.threads = 0,
      verbose = FALSE
    )$predictions

    if (!("UP" %in% colnames(pr))) {
      stop("Ranger UP probability column missing.")
    }

    p <- as.numeric(pr[, "UP"])
  } else {
    p <- as.numeric(predict(
      model$fit,
      xgboost::xgb.DMatrix(as.matrix(x))
    ))
  }

  if (
    length(p) != nrow(newdata) ||
    any(!is.finite(p)) ||
    any(p < 0 | p > 1)
  ) {
    stop("Invalid probabilities from ", model$id)
  }

  p
}


# ==============================================================================
# 12. SCORING / INFERENCE
# ==============================================================================

exact_ci <- function(wins, n) {
  ci <- stats::binom.test(wins, n)$conf.int
  c(lower = unname(ci[1]), upper = unname(ci[2]))
}

score_predictions <- function(Z, p, cutoff, base_side) {
  confidence <- abs(p - 0.5)
  selected <- confidence >= cutoff

  if (!any(selected)) {
    return(data.table::data.table(
      selected_n = 0L,
      coverage = 0,
      wins = 0L,
      win_rate = NA_real_,
      ci95_lower = NA_real_,
      ci95_upper = NA_real_,
      flat_rate = NA_real_,
      baseline_wr = NA_real_,
      edge = NA_real_,
      active_weeks = 0L
    ))
  }

  side <- ifelse(p >= 0.5, 1L, -1L)
  win <- side[selected] == Z$outcome[selected]  # flat => FALSE

  n <- sum(selected)
  wins <- sum(win)
  ci <- exact_ci(wins, n)

  data.table::data.table(
    selected_n = n,
    coverage = mean(selected),
    wins = wins,
    win_rate = mean(win),
    ci95_lower = ci["lower"],
    ci95_upper = ci["upper"],
    flat_rate = mean(Z$outcome[selected] == 0L),
    baseline_wr = mean(base_side == Z$outcome[selected]),
    edge = mean(win) - mean(base_side == Z$outcome[selected]),
    active_weeks = data.table::uniqueN(Z$week_id[selected])
  )
}

week_block_ci <- function(Z, p, cutoff, reps = BOOT_REPS, seed = SEED) {
  selected <- abs(p - 0.5) >= cutoff

  if (!any(selected)) {
    return(c(lower = NA_real_, upper = NA_real_))
  }

  side <- ifelse(p >= 0.5, 1L, -1L)

  all_weeks <- data.table::data.table(
    week_id = unique(Z$week_id)
  )

  q <- data.table::data.table(
    week_id = Z$week_id[selected],
    win = as.integer(side[selected] == Z$outcome[selected])
  )[, .(
    n = .N,
    wins = sum(win)
  ), by = week_id]

  w <- merge(all_weeks, q, by = "week_id", all.x = TRUE)
  w[is.na(n), `:=`(n = 0L, wins = 0L)]

  set.seed(seed)
  boot_wr <- rep(NA_real_, reps)

  for (b in seq_len(reps)) {
    idx <- sample.int(nrow(w), nrow(w), replace = TRUE)
    n_b <- sum(w$n[idx])

    if (n_b > 0L) {
      boot_wr[b] <- sum(w$wins[idx]) / n_b
    }
  }

  boot_wr <- boot_wr[is.finite(boot_wr)]

  if (!length(boot_wr)) {
    return(c(lower = NA_real_, upper = NA_real_))
  }

  c(
    lower = unname(stats::quantile(boot_wr, 0.025)),
    upper = unname(stats::quantile(boot_wr, 0.975))
  )
}


# ==============================================================================
# 13. 2024 MODEL SELECTION
# ==============================================================================

selection_results <- list()
result_counter <- 0L

# Keep only the best fitted model in memory. Storing all 96 fitted models is
# unnecessary and can consume several GB on a long rich-feature run.
BEST_MODEL_BUNDLE <- NULL
BEST_CANDIDATE <- NULL

is_better_candidate <- function(candidate, best) {
  if (is.null(best)) return(TRUE)

  if (candidate$ci95_lower != best$ci95_lower) {
    return(candidate$ci95_lower > best$ci95_lower)
  }
  if (candidate$win_rate != best$win_rate) {
    return(candidate$win_rate > best$win_rate)
  }
  candidate$selected_n > best$selected_n
}

for (h in HORIZONS) {
  S <- SAMPLES[[as.character(h)]]

  train <- S[
    signal_date >= TRAIN_START &
    signal_date < TRAIN_END &
    forecast_end_date < TRAIN_END &
    outcome != 0L
  ]

  valid <- S[
    signal_date >= VALID_START &
    signal_date < VALID_END &
    forecast_end_date < VALID_END
  ]

  if (nrow(train) < 5000L || nrow(valid) < 1000L) {
    stop("Unexpectedly small sample at h=", h)
  }

  base_side <- ifelse(
    mean(train$outcome == 1L) >= 0.5,
    1L,
    -1L
  )

  for (feature_set in names(FEATURE_SETS)) {
    features <- FEATURE_SETS[[feature_set]]

    for (model_id in MODEL_IDS) {
      spec <- MODEL_SPECS[[model_id]]
      xgb_depth <- if (is.null(spec$depth)) NA_integer_ else spec$depth

      cat(
        "2024 selection | h=", h,
        " | ", feature_set,
        " | ", model_id,
        "\n",
        sep = ""
      )

      model <- fit_model(train, features, model_id)
      p <- predict_model(model, valid, features)
      confidence <- abs(p - 0.5)

      for (target_coverage in COVERAGES) {
        # Only 2024 determines this percentile-derived ABSOLUTE cutoff.
        cutoff <- as.numeric(stats::quantile(
          confidence,
          probs = 1 - target_coverage,
          names = FALSE,
          type = 7
        ))

        sc <- score_predictions(valid, p, cutoff, base_side)

        result_counter <- result_counter + 1L

        candidate <- cbind(
          data.table::data.table(
            horizon = h,
            feature_set = feature_set,
            model_id = model_id,
            xgb_depth = xgb_depth,
            target_coverage = target_coverage,
            confidence_cutoff = cutoff
          ),
          sc
        )

        selection_results[[result_counter]] <- candidate

        if (
          candidate$selected_n >= MIN_VALID_N &&
          candidate$active_weeks >= MIN_VALID_WEEKS &&
          is.finite(candidate$ci95_lower) &&
          is_better_candidate(candidate, BEST_CANDIDATE)
        ) {
          BEST_CANDIDATE <- data.table::copy(candidate)
          BEST_MODEL_BUNDLE <- list(
            model = model,
            features = features,
            horizon = h,
            feature_set = feature_set,
            model_id = model_id,
            xgb_depth = xgb_depth,
            base_side = base_side
          )
        }
      }
    }
  }
}

SELECTION <- data.table::rbindlist(selection_results)

data.table::fwrite(
  SELECTION,
  file.path(OUT, "06_all_2024_selection_results.csv")
)

ELIGIBLE <- SELECTION[
  selected_n >= MIN_VALID_N &
  active_weeks >= MIN_VALID_WEEKS
]

if (nrow(ELIGIBLE) == 0L) {
  stop("No candidate passed the 2024 minimum sample/stability rules.")
}

# Conservative selection: lower 95% binomial bound first, then WR, then N.
data.table::setorder(
  ELIGIBLE,
  -ci95_lower,
  -win_rate,
  -selected_n
)

CHAMPION <- data.table::copy(ELIGIBLE[1])
CHAMPION[, validation_ci_above_50 := ci95_lower > 0.50]

data.table::fwrite(
  ELIGIBLE[1:min(.N, 100L)],
  file.path(OUT, "07_top_2024_candidates.csv")
)

data.table::fwrite(
  CHAMPION,
  file.path(OUT, "08_FROZEN_CHAMPION.csv")
)

XGB_DEPTH_COMPARISON <- ELIGIBLE[
  !is.na(xgb_depth)
][
  order(-ci95_lower, -win_rate, -selected_n),
  .SD[1],
  by = xgb_depth
]

data.table::setorder(XGB_DEPTH_COMPARISON, xgb_depth)

data.table::fwrite(
  XGB_DEPTH_COMPARISON,
  file.path(OUT, "09_best_candidate_by_xgb_depth_2024.csv")
)

BEST_FEATURE_SET <- ELIGIBLE[
  order(-ci95_lower, -win_rate, -selected_n),
  .SD[1],
  by = feature_set
]

data.table::fwrite(
  BEST_FEATURE_SET,
  file.path(OUT, "10_best_NQ_only_vs_NQ_ES_2024.csv")
)


# ==============================================================================
# 14. FREEZE 2024 CHAMPION
# ==============================================================================

if (is.null(BEST_MODEL_BUNDLE) || is.null(BEST_CANDIDATE)) {
  stop("Frozen champion model was not retained.")
}

same_champion <- (
  CHAMPION$horizon == BEST_CANDIDATE$horizon &&
  CHAMPION$feature_set == BEST_CANDIDATE$feature_set &&
  CHAMPION$model_id == BEST_CANDIDATE$model_id &&
  isTRUE(all.equal(
    CHAMPION$confidence_cutoff,
    BEST_CANDIDATE$confidence_cutoff,
    tolerance = 0
  ))
)

if (!same_champion) {
  stop("Internal selection/model-retention mismatch.")
}

FROZEN <- BEST_MODEL_BUNDLE
FROZEN_CUTOFF <- CHAMPION$confidence_cutoff


# ==============================================================================
# 15. 2025 + 2026 YTD — NO REFIT / RESELECTION / RECALIBRATION
# ==============================================================================

evaluate_frozen_period <- function(start_date, end_date, label, seed_offset) {
  S <- SAMPLES[[as.character(FROZEN$horizon)]]

  Z <- S[
    signal_date >= start_date &
    signal_date < end_date &
    forecast_end_date < end_date
  ]

  if (nrow(Z) == 0L) stop("No rows for ", label)

  p <- predict_model(FROZEN$model, Z, FROZEN$features)

  sc <- score_predictions(
    Z,
    p,
    FROZEN_CUTOFF,
    FROZEN$base_side
  )

  block_ci <- week_block_ci(
    Z,
    p,
    FROZEN_CUTOFF,
    reps = BOOT_REPS,
    seed = SEED + seed_offset
  )

  sc[, `:=`(
    period = label,
    block_ci95_lower = block_ci["lower"],
    block_ci95_upper = block_ci["upper"],
    horizon = FROZEN$horizon,
    feature_set = FROZEN$feature_set,
    model_id = FROZEN$model_id,
    xgb_depth = FROZEN$xgb_depth,
    confidence_cutoff = FROZEN_CUTOFF
  )]

  side <- ifelse(p >= 0.5, 1L, -1L)
  confidence <- abs(p - 0.5)
  selected <- confidence >= FROZEN_CUTOFF

  predictions <- data.table::data.table(
    signal_et = Z$signal_et,
    signal_date = Z$signal_date,
    week_id = Z$week_id,
    season = Z$season,

    asia_session = Z$asia_session,
    london_session = Z$london_session,
    us_rth_session = Z$us_rth_session,
    us_last60 = Z$us_last60,
    opening30_known = Z$opening30_known,

    nq_rth_gap = Z$nq_rth_gap,
    nq_open30_ret = Z$nq_open30_ret,
    nq_prevclose_to_1000 = Z$nq_prevclose_to_1000,

    p_up = p,
    confidence = confidence,
    selected = selected,
    prediction = side,
    outcome = Z$outcome,
    win = as.integer(side == Z$outcome)
  )

  list(metric = sc, predictions = predictions)
}

TEST_2025 <- evaluate_frozen_period(
  TEST25_START, TEST25_END, "2025", 25L
)

TEST_2026 <- evaluate_frozen_period(
  TEST26_START, TEST26_END, "2026_YTD", 26L
)

RECENT_RESULTS <- data.table::rbindlist(list(
  TEST_2025$metric,
  TEST_2026$metric
))

RECENT_RESULTS[, statistically_above_50 :=
  win_rate > 0.50 &
  is.finite(block_ci95_lower) &
  block_ci95_lower > 0.50
]

data.table::fwrite(
  RECENT_RESULTS,
  file.path(OUT, "11_PRIMARY_RECENT_RESULTS.csv")
)

data.table::fwrite(
  TEST_2025$predictions[selected == TRUE],
  file.path(OUT, "12_selected_predictions_2025.csv")
)

data.table::fwrite(
  TEST_2026$predictions[selected == TRUE],
  file.path(OUT, "13_selected_predictions_2026_YTD.csv")
)


# ==============================================================================
# 16. DESCRIPTIVE DIAGNOSTICS — NEVER USED TO RESELECT
# ==============================================================================

season_summary <- function(P, period_label) {
  P[
    selected == TRUE,
    .(
      n = .N,
      win_rate = mean(win),
      flat_rate = mean(outcome == 0L)
    ),
    by = season
  ][, period := period_label]
}

session_summary <- function(P, period_label) {
  out <- data.table::rbindlist(list(
    P[selected == TRUE & asia_session == 1L,
      .(session = "Asia", n = .N, win_rate = mean(win))],

    P[selected == TRUE & london_session == 1L,
      .(session = "London", n = .N, win_rate = mean(win))],

    P[selected == TRUE & us_rth_session == 1L,
      .(session = "US_RTH", n = .N, win_rate = mean(win))],

    P[selected == TRUE & us_last60 == 1L,
      .(session = "US_last60", n = .N, win_rate = mean(win))]
  ), fill = TRUE)

  out[, period := period_label]
  out
}

RECENT_BY_SEASON <- data.table::rbindlist(list(
  season_summary(TEST_2025$predictions, "2025"),
  season_summary(TEST_2026$predictions, "2026_YTD")
))

RECENT_BY_SESSION <- data.table::rbindlist(list(
  session_summary(TEST_2025$predictions, "2025"),
  session_summary(TEST_2026$predictions, "2026_YTD")
), fill = TRUE)

data.table::fwrite(
  RECENT_BY_SEASON,
  file.path(OUT, "14_recent_results_by_season.csv")
)

data.table::fwrite(
  RECENT_BY_SESSION,
  file.path(OUT, "15_recent_results_by_session.csv")
)


# ==============================================================================
# 17. SUMMARY
# ==============================================================================

cat("\n============================================================\n")
cat("FEATURE COUNTS\n")
cat("============================================================\n")
cat("NQ_ONLY:", length(NQ_FEATURES), "\n")
cat("NQ_ES:  ", length(NQ_ES_FEATURES), "\n")

cat("\n============================================================\n")
cat("FROZEN 2024 CHAMPION\n")
cat("============================================================\n")
print(CHAMPION)

cat("\n============================================================\n")
cat("BEST 2024 CANDIDATE BY XGBOOST DEPTH\n")
cat("============================================================\n")
print(XGB_DEPTH_COMPARISON)

cat("\n============================================================\n")
cat("2025 CONFIRMATION + 2026 YTD RECENT TEST\n")
cat("============================================================\n")
print(RECENT_RESULTS)

cat(
  "\nInterpretation:\n",
  "- 2024 is selection only.\n",
  "- 2025 is the first untouched confirmation period.\n",
  "- 2026 YTD is the recent untouched continuation period.\n",
  "- Flats count as losses.\n",
  "- TTR supplies RSI, MACD, Bollinger Bands, rolling VWAP, EMA, ADX, Donchian and SMA.\n",
  "- First-30-minute features are unavailable until 10:00 ET and are masked before then.\n",
  "- RTH gap is masked until the 09:30 opening bar has begun; on our 15-minute grid it first matters at 09:45.\n",
  "- The exact model and absolute confidence cutoff are frozen after 2024.\n",
  "- Week-block CI > 50% is the main statistical evidence threshold.\n",
  sep = ""
)

cat(
  "\nPrimary result file:\n",
  file.path(OUT, "11_PRIMARY_RECENT_RESULTS.csv"),
  "\n",
  sep = ""
)
