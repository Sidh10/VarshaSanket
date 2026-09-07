"""Stage 1 -- REGIME FORECASTER.

This model FORECASTS A FUTURE REGIME. It does not classify a current state.

CLAUDE.md Rule 3 lists 'Stage 1 "Regime Classifier"' as a superseded design that
this project has regressed to before. The distinction is not cosmetic and is
enforced by the shape of the problem here:

    features are built from the trajectory over  [t-30, t]
    the target is the regime during the window   [t + L, t + L + 6]   for L = 1..4 weeks

There is no code path in this module that predicts the regime at time t. The
`lead_days` argument is required and has no default, so a caller cannot
accidentally construct a nowcast.

ARCHITECTURE.md: "This is the only stage with genuine predictive skill. That
skill comes from MJO/BSISO phase propagation, which is quasi-oscillatory and
therefore partially predictable 2-3 weeks out." If that claim is false, the
project has no skill -- which is why src/eval/backtest.py tests it in isolation
before anything downstream is built.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from src.features.labels import CLASSES


@dataclass(frozen=True)
class RegimeForecast:
    """A forecast of a FUTURE regime window, with its supporting evidence.

    `effective_n` exists because CLAUDE.md requires every forecast-producing
    function to return its effective ensemble size. NOTE the honest caveat:
    entropy-based *effective analog count* is a Stage 2 concept and does not
    apply to a gradient-boosted model. What is returned here is the training
    support behind the fold -- the number of labelled days the forecaster was
    fitted on, and the per-class counts. It is deliberately NOT dressed up as
    an analog ensemble size.
    """

    proba: pd.DataFrame  # index: issue date t, columns: CLASSES
    lead_days: int
    target_window_days: int
    effective_n: int  # training days behind this forecast
    class_support: dict[str, int]

    def describe(self) -> str:
        return (
            f"forecast at lead {self.lead_days}d for a {self.target_window_days}d "
            f"window | n={len(self.proba)} issue dates | "
            f"training support {self.effective_n} days {self.class_support}"
        )


class RegimeForecaster:
    """Gradient-boosted forecaster: index trajectory over [t-30, t] -> P(regime at t+L).

    Deliberately gradient boosting, not a deep model (CLAUDE.md Rule 3,
    DISCUSSION D-B): right-sized for ~1.2k labelled days and ~45 features.
    """

    def __init__(
        self,
        lead_days: int,
        target_window_days: int = 7,
        n_estimators: int = 300,
        max_depth: int = 3,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        reg_lambda: float = 5.0,
        min_child_weight: float = 10.0,
        random_state: int = 0,
    ):
        if lead_days <= 0:
            raise ValueError(
                "lead_days must be positive -- this is a FORECASTER of a future "
                "regime, not a classifier of the current state (CLAUDE.md Rule 3)."
            )
        self.lead_days = lead_days
        self.target_window_days = target_window_days
        self.classes_ = list(CLASSES)
        self._model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            reg_lambda=reg_lambda,
            min_child_weight=min_child_weight,
            objective="multi:softprob",
            num_class=len(CLASSES),
            random_state=random_state,
            n_jobs=4,
            tree_method="hist",
            eval_metric="mlogloss",
        )
        self._support: dict[str, int] = {}
        self._n_train = 0

    # Small a-priori grid for inner-fold model selection. Kept deliberately
    # small: the point is to avoid handicapping the model with an arbitrary
    # capacity choice, NOT to search hard enough to manufacture skill.
    _GRID = [
        {"max_depth": 2, "min_child_weight": 20.0},
        {"max_depth": 3, "min_child_weight": 10.0},
        {"max_depth": 3, "min_child_weight": 30.0},
        {"max_depth": 4, "min_child_weight": 20.0},
    ]

    def fit(
        self, X: pd.DataFrame, y_future: pd.Series, tune: bool = True
    ) -> "RegimeForecaster":
        """Fit on (trajectory features at t) -> (regime in the window at t+lead).

        `y_future` MUST already be the shifted future target produced by
        `make_future_target`. Passing the contemporaneous regime here would make
        this a nowcaster and is not supported.

        When `tune` is set, capacity is chosen by an inner GroupKFold over the
        TRAINING YEARS ONLY. This is not a violation of VERIFICATION.md section 3
        -- that rule forbids hyperparameter choice from touching the HELD-OUT
        year, and `fit` is only ever handed training-fold data by the backtest.
        Leaving capacity fixed at an arbitrary guess would understate achievable
        skill, which is its own form of misreporting.
        """
        mask = y_future.notna() & X.notna().all(axis=1)
        Xf, yf = X[mask], y_future[mask]
        codes = yf.map({c: i for i, c in enumerate(self.classes_)}).astype(int)

        if tune and len(np.unique(Xf.index.year)) >= 6:
            best = self._select_capacity(Xf, codes)
            self._model.set_params(**best)
            self._chosen = best
        else:
            self._chosen = {}

        self._model.fit(Xf.values, codes.values)
        self._n_train = int(len(yf))
        self._support = {c: int((yf == c).sum()) for c in self.classes_}
        return self

    def _select_capacity(self, Xf: pd.DataFrame, codes: pd.Series) -> dict:
        """Inner GroupKFold over training years; score by multiclass Brier."""
        from sklearn.model_selection import GroupKFold

        groups = Xf.index.year.to_numpy()
        gkf = GroupKFold(n_splits=3)
        scores = []
        for params in self._GRID:
            fold_scores = []
            for tr, va in gkf.split(Xf, codes, groups=groups):
                m = self._model.__class__(**{**self._model.get_params(), **params})
                m.fit(Xf.values[tr], codes.values[tr])
                p = m.predict_proba(Xf.values[va])
                o = np.zeros_like(p)
                o[np.arange(len(va)), codes.values[va]] = 1.0
                fold_scores.append(((p - o) ** 2).sum(axis=1).mean())
            scores.append(np.mean(fold_scores))
        return self._GRID[int(np.argmin(scores))]

    def forecast_proba(self, X: pd.DataFrame) -> RegimeForecast:
        """Forecast P(regime) for the window starting `lead_days` after each row's date."""
        mask = X.notna().all(axis=1)
        p = np.full((len(X), len(self.classes_)), np.nan)
        if mask.any():
            p[mask.values] = self._model.predict_proba(X[mask].values)
        return RegimeForecast(
            proba=pd.DataFrame(p, index=X.index, columns=self.classes_),
            lead_days=self.lead_days,
            target_window_days=self.target_window_days,
            effective_n=self._n_train,
            class_support=dict(self._support),
        )

    def feature_importance(self, X: pd.DataFrame) -> pd.Series:
        return pd.Series(
            self._model.feature_importances_, index=X.columns
        ).sort_values(ascending=False)


def make_future_target(
    labels: pd.Series, lead_days: int, window_days: int = 7
) -> pd.Series:
    """Build the FUTURE regime target for issue date t.

    The target is the modal regime over [t + lead_days, t + lead_days + window_days).
    A window rather than a single day because a 3-week-lead forecast of one
    specific calendar day is not a claim this data supports (ARCHITECTURE.md
    output tiering: 14-30 days is "regime outlook only -- not a date").

    Returns NaN where the target window is not fully observed, so partially
    covered windows are dropped rather than silently scored against a
    short sample.
    """
    if lead_days <= 0:
        raise ValueError("lead_days must be positive (future regime, not current)")

    lab = labels.sort_index()
    idx = lab.index
    out = pd.Series(index=idx, dtype=object)
    for t in idx:
        lo = t + pd.Timedelta(days=lead_days)
        hi = lo + pd.Timedelta(days=window_days)
        win = lab[(lab.index >= lo) & (lab.index < hi)]
        if len(win) < window_days:
            continue  # window not fully observed -- do not score a partial window
        out.loc[t] = win.mode().iloc[0]
    return out
