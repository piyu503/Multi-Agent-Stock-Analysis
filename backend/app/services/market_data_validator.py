"""Market data validator auditing financial time-series integrity."""

from datetime import datetime, timezone
from typing import List, Tuple
import pandas as pd

from app.schemas.market_data import (
    ValidationIssue,
    ValidationResult,
    ValidationSeverity,
    ValidationStatus,
)


class MarketDataValidator:
    """Enforces mathematical, chronological, and data-integrity rules on daily OHLCV bars."""

    @staticmethod
    def validate_ohlcv_dataframe(df: pd.DataFrame, ticker: str) -> Tuple[ValidationResult, pd.DataFrame]:
        """Validate an OHLCV DataFrame from yfinance.

        Returns:
            Tuple[ValidationResult, pd.DataFrame]: Audit result and cleaned, sorted DataFrame.
        """
        issues: List[ValidationIssue] = []

        # 1. Check for empty dataset
        if df is None or df.empty:
            issues.append(
                ValidationIssue(
                    code="EMPTY_DATASET",
                    message=f"No price records returned for ticker '{ticker}' across the requested period.",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return (
                ValidationResult(
                    status=ValidationStatus.INVALID,
                    total_records=0,
                    issues=issues,
                    warnings_count=0,
                    errors_count=1,
                ),
                pd.DataFrame(),
            )

        df = df.copy()

        # Parse index if not already DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            try:
                df.index = pd.to_datetime(df.index)
            except Exception as e:
                issues.append(
                    ValidationIssue(
                        code="INVALID_DATE_INDEX",
                        message=f"Unable to parse timestamp index: {str(e)}",
                        severity=ValidationSeverity.ERROR,
                    )
                )
                return (
                    ValidationResult(
                        status=ValidationStatus.INVALID,
                        total_records=len(df),
                        issues=issues,
                        warnings_count=0,
                        errors_count=1,
                    ),
                    pd.DataFrame(),
                )

        # Standardize index to exchange calendar session date.
        # CRITICAL FIX: Do NOT use tz_convert(None), which converts local exchange midnight (e.g. 00:00:00+05:30 IST)
        # to UTC (18:30:00 of the PREVIOUS day), falsely shifting Monday sessions to Sunday!
        # Using pd.to_datetime(df.index.date) preserves the actual exchange trading calendar date.
        if df.index.tz is not None:
            df.index = pd.to_datetime(df.index.date)
        else:
            df.index = pd.to_datetime(df.index).normalize()

        raw_count = len(df)

        # 2. Check for duplicate dates
        duplicate_mask = df.index.duplicated(keep="last")
        dup_count = int(duplicate_mask.sum())
        if dup_count > 0:
            dup_dates = [d.strftime("%Y-%m-%d") for d in df.index[duplicate_mask]]
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_DATES_DETECTED",
                    message=f"Detected and dropped {dup_count} duplicate date rows, retaining the latest record.",
                    severity=ValidationSeverity.WARNING,
                    details={"duplicate_count": dup_count, "discarded_dates": dup_dates},
                )
            )
            df = df[~duplicate_mask]

        # 3. Ensure monotonic ascending sort by date
        if not df.index.is_monotonic_increasing:
            df = df.sort_index(ascending=True)
            issues.append(
                ValidationIssue(
                    code="NON_MONOTONIC_DATES",
                    message="Price series was not chronologically sorted. Reordered index ascendingly.",
                    severity=ValidationSeverity.WARNING,
                    details={"reordered": True},
                )
            )

        # Required columns mapping (case-insensitive check)
        col_map = {col.lower(): col for col in df.columns}
        required_fields = ["open", "high", "low", "close"]
        for field in required_fields:
            if field not in col_map:
                issues.append(
                    ValidationIssue(
                        code=f"MISSING_FIELD_{field.upper()}",
                        message=f"Required financial field '{field}' is absent from provider payload.",
                        severity=ValidationSeverity.ERROR,
                    )
                )

        if any(issue.severity == ValidationSeverity.ERROR for issue in issues):
            errors = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
            warnings = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)
            return (
                ValidationResult(
                    status=ValidationStatus.INVALID,
                    total_records=len(df),
                    issues=issues,
                    warnings_count=warnings,
                    errors_count=errors,
                ),
                pd.DataFrame(),
            )

        # Map to canonical column names
        open_col = col_map["open"]
        high_col = col_map["high"]
        low_col = col_map["low"]
        close_col = col_map["close"]
        volume_col = col_map.get("volume")

        # 4. Check for NaN / null values in core price columns
        nan_rows = df[[open_col, high_col, low_col, close_col]].isna().any(axis=1)
        nan_count = int(nan_rows.sum())
        if nan_count > 0:
            nan_dates = [d.strftime("%Y-%m-%d") for d in df[nan_rows].index]
            issues.append(
                ValidationIssue(
                    code="MISSING_PRICE_VALUES",
                    message=f"Detected {nan_count} bars with NaN or null price fields. Dropping invalid bars.",
                    severity=ValidationSeverity.WARNING,
                    details={"dropped_count": nan_count, "discarded_dates": nan_dates},
                )
            )
            df = df[~nan_rows]

        if df.empty:
            issues.append(
                ValidationIssue(
                    code="NO_USABLE_RECORDS",
                    message="All retrieved bars contained NaN or corrupted price fields.",
                    severity=ValidationSeverity.ERROR,
                )
            )
            return (
                ValidationResult(
                    status=ValidationStatus.INVALID,
                    total_records=0,
                    issues=issues,
                    warnings_count=1,
                    errors_count=1,
                ),
                pd.DataFrame(),
            )

        # 5. Check for non-positive prices
        non_positive = (
            (df[open_col] <= 0)
            | (df[high_col] <= 0)
            | (df[low_col] <= 0)
            | (df[close_col] <= 0)
        )
        non_pos_count = int(non_positive.sum())
        if non_pos_count > 0:
            non_pos_dates = [d.strftime("%Y-%m-%d") for d in df[non_positive].index]
            issues.append(
                ValidationIssue(
                    code="NON_POSITIVE_PRICE_DETECTED",
                    message=f"Found {non_pos_count} session(s) with non-positive (<= 0) price values. Dropping corrupt bars.",
                    severity=ValidationSeverity.WARNING,
                    details={"count": non_pos_count, "discarded_dates": non_pos_dates},
                )
            )
            df = df[~non_positive]

        # 6. Check OHLC relational invariants: High >= Low, High >= Open, High >= Close, Low <= Open, Low <= Close
        invalid_high_low = df[high_col] < df[low_col]
        invalid_high_open = df[high_col] < df[open_col]
        invalid_high_close = df[high_col] < df[close_col]
        invalid_low_open = df[low_col] > df[open_col]
        invalid_low_close = df[low_col] > df[close_col]

        ohlc_violations = (
            invalid_high_low
            | invalid_high_open
            | invalid_high_close
            | invalid_low_open
            | invalid_low_close
        )
        violation_count = int(ohlc_violations.sum())
        if violation_count > 0:
            violation_dates = [d.strftime("%Y-%m-%d") for d in df[ohlc_violations].index]
            issues.append(
                ValidationIssue(
                    code="INVALID_OHLC_RELATIONSHIP",
                    message=f"Found {violation_count} bar(s) violating OHLC mathematical invariants (e.g. High < Low or Close > High). Dropping corrupt bars.",
                    severity=ValidationSeverity.WARNING,
                    details={"count": violation_count, "discarded_dates": violation_dates},
                )
            )
            df = df[~ohlc_violations]

        # 7. Check for negative volume
        if volume_col and volume_col in df.columns:
            neg_vol = df[volume_col] < 0
            neg_vol_count = int(neg_vol.sum())
            if neg_vol_count > 0:
                issues.append(
                    ValidationIssue(
                        code="NEGATIVE_VOLUME_DETECTED",
                        message=f"Found {neg_vol_count} session(s) with negative trading volume.",
                        severity=ValidationSeverity.WARNING,
                        details={"count": neg_vol_count},
                    )
                )

        # 8. Check for trading calendar gaps (> 7 calendar days between consecutive sessions)
        # Standard weekends (2 days) and typical holiday long weekends (3-4 days) are normal and NOT flagged.
        if len(df) > 1:
            date_diffs = df.index.to_series().diff().dt.days
            suspicious_gaps = date_diffs[date_diffs > 7]
            if not suspicious_gaps.empty:
                gap_details = [
                    {"after_date": idx.strftime("%Y-%m-%d"), "gap_days": int(gap)}
                    for idx, gap in suspicious_gaps.head(5).items()
                ]
                issues.append(
                    ValidationIssue(
                        code="CALENDAR_GAP_WARNING",
                        message=f"Detected {len(suspicious_gaps)} gap(s) exceeding 7 calendar days between trading sessions. May reflect trading halts or provider data gaps.",
                        severity=ValidationSeverity.WARNING,
                        details={"sample_gaps": gap_details},
                    )
                )

        # 9. Corporate Action Auditing: Stock Splits & Cash Dividends
        if "Stock Splits" in df.columns:
            splits = df[df["Stock Splits"] > 0]
            if not splits.empty:
                split_dates = [idx.strftime("%Y-%m-%d") for idx in splits.index]
                ratios = [float(splits.loc[idx, "Stock Splits"]) for idx in splits.index]
                issues.append(
                    ValidationIssue(
                        code="CORPORATE_ACTION_SPLIT_DETECTED",
                        message=(
                            f"Stock split detected on {', '.join(split_dates)}. Raw Close values reflect unadjusted "
                            "exchange quotes; return and moving average calculations use raw Close. Refer to Adj Close for split-adjusted series."
                        ),
                        severity=ValidationSeverity.WARNING,
                        details={"split_dates": split_dates, "ratios": ratios},
                    )
                )

        if "Dividends" in df.columns:
            divs = df[df["Dividends"] > 0]
            if not divs.empty:
                div_dates = [idx.strftime("%Y-%m-%d") for idx in divs.index]
                issues.append(
                    ValidationIssue(
                        code="DIVIDEND_EVENT_DETECTED",
                        message=(
                            f"Cash dividend event recorded on {', '.join(div_dates)}. Raw Close reflects settlement price, "
                            "while Adj Close incorporates dividend reinvestment adjustment."
                        ),
                        severity=ValidationSeverity.INFO,
                        details={"dividend_dates": div_dates},
                    )
                )

        # 10. Check data freshness (stale data warning if latest bar is > 5 calendar days old)
        if not df.empty:
            latest_session = df.index[-1].date()
            today = datetime.now(timezone.utc).date()
            staleness_days = (today - latest_session).days
            if staleness_days > 5:
                issues.append(
                    ValidationIssue(
                        code="STALE_DATA_WARNING",
                        message=f"Latest recorded session is {latest_session.strftime('%Y-%m-%d')} ({staleness_days} days ago). Verify market schedule or provider availability.",
                        severity=ValidationSeverity.WARNING,
                        details={"latest_date": latest_session.strftime("%Y-%m-%d"), "days_ago": staleness_days},
                    )
                )

        # 11. Check minimum history count for deterministic indicators
        n_sessions = len(df)
        if n_sessions < 20:
            issues.append(
                ValidationIssue(
                    code="LIMITED_HISTORY_WARNING",
                    message=(
                        f"Dataset contains {n_sessions} sessions (< 20). 20-SMA, 50-SMA, and 20-session volatility "
                        "will be unavailable."
                    ),
                    severity=ValidationSeverity.INFO,
                    details={"record_count": n_sessions},
                )
            )
        elif n_sessions == 20:
            issues.append(
                ValidationIssue(
                    code="LIMITED_HISTORY_WARNING",
                    message=(
                        "Dataset contains 20 sessions. 20-SMA is available, but 20-session volatility requires 20 return "
                        "values (21 price sessions), and 50-SMA requires 50 sessions; both will be unavailable."
                    ),
                    severity=ValidationSeverity.INFO,
                    details={"record_count": n_sessions},
                )
            )
        elif n_sessions < 50:
            issues.append(
                ValidationIssue(
                    code="LIMITED_HISTORY_WARNING",
                    message=f"Dataset contains {n_sessions} sessions (< 50). 50-SMA will be unavailable.",
                    severity=ValidationSeverity.INFO,
                    details={"record_count": n_sessions},
                )
            )

        # Evaluate final status
        errors_count = sum(1 for i in issues if i.severity == ValidationSeverity.ERROR)
        warnings_count = sum(1 for i in issues if i.severity == ValidationSeverity.WARNING)

        if errors_count > 0:
            status = ValidationStatus.INVALID
        elif warnings_count > 0:
            status = ValidationStatus.WARNING
        else:
            status = ValidationStatus.VALID

        result = ValidationResult(
            status=status,
            total_records=len(df),
            issues=issues,
            warnings_count=warnings_count,
            errors_count=errors_count,
        )

        return result, df
