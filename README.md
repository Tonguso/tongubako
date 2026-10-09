# tongubako

`tongubako` is Hogan Tong's collection of Python tools for market data, quantitative research, analytics, and charting. The name comes from *dogu-bako* (どうぐばこ), Japanese for toolbox.

## Contents

- `bbgubako`: Bloomberg API tools, including Bloomberg data functions and EMSX utilities. Requires Bloomberg's `blpapi` package and access to the Bloomberg environment for live API calls.
- `yfintori`: Yahoo Finance data tools using `yfinance`, with worldwide equity prices, OHLCV history, fundamentals/metadata, and latest FX rates. Accepts Yahoo-format tickers such as `AAPL`, `7203.T`, and `GSK.L`.
- `openbbg`: Bloomberg-style market data functions backed by a direct Yahoo client or OpenBB providers. Includes ticker and field translation; provider availability and credentials depend on the requested function. Does not require Bloomberg connectivity.
- `utils`: General utilities for time series, performance metrics, data conversion, and related tasks.
- `lppls.py`: Functions for fitting and working with the Log-Periodic Power Law Singularity model.
- `kalman_filter/` and `kalman_filter.py`: Kalman filter implementations.
- `PCA`: Principal component analysis utilities, including robust PCA.
- `plotify`: Plotting helpers for line, scatter, violin, and related charts.
- `shutup`: Mute and restore warnings. `please()` silences Python and C-level warnings (e.g. numpy `RuntimeWarning`) and library logging at WARNING or below; `jk()` restores the previous state. Also usable as `with mute_warnings:`.

## Installation and dependencies

The repository is a collection of modules and does not yet define a unified installation or dependency configuration. Individual modules may require third-party packages such as `numpy`, `pandas`, `scipy`, `matplotlib`, `statsmodels`, or Bloomberg's `blpapi`. Install the dependencies needed by the modules you use.

`yfintori` requires `pandas` and `yfinance`. The default direct Yahoo price route in `openbbg` requires `pandas` and `requests`; OpenBB-backed functions additionally require `openbb` and the relevant provider dependencies. Some providers require API credentials, such as FMP for index constituents. Yahoo/OpenBB data is not a substitute for Bloomberg's field coverage or data quality; `openbbg` supports only simple ticker/field/date BQL requests, not Bloomberg screening or computed expressions.

Bloomberg API functions require a Bloomberg Terminal or other authorized Bloomberg API environment. They will not work in a standard Python environment without Bloomberg connectivity.

## Status

This project is under active development. Interfaces and dependencies may change.

## License

See [LICENSE](LICENSE).
