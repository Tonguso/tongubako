# tongubako

`tongubako` is Hogan Tong's collection of Python tools for market data, quantitative research, analytics, and charting. The name comes from *dogu-bako* (どうぐばこ), Japanese for toolbox.

## Contents

- `bbgubako`: Bloomberg API tools, including Bloomberg data functions and EMSX utilities. Requires Bloomberg's `blpapi` package and access to the Bloomberg environment for live API calls.
- `utils`: General utilities for time series, performance metrics, data conversion, and related tasks.
- `lppls.py`: Functions for fitting and working with the Log-Periodic Power Law Singularity model.
- `kalman_filter/` and `kalman_filter.py`: Kalman filter implementations.
- `PCA`: Principal component analysis utilities, including robust PCA.
- `plotify`: Plotting helpers for line, scatter, violin, and related charts.

## Installation and dependencies

The repository is a collection of modules and does not yet define a unified installation or dependency configuration. Individual modules may require third-party packages such as `numpy`, `pandas`, `scipy`, `matplotlib`, `statsmodels`, or Bloomberg's `blpapi`. Install the dependencies needed by the modules you use.

Bloomberg API functions require a Bloomberg Terminal or other authorized Bloomberg API environment. They will not work in a standard Python environment without Bloomberg connectivity.

## Status

This project is under active development. Interfaces and dependencies may change.

## License

See [LICENSE](LICENSE).
