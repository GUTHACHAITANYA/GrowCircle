# GrowCircle Machine Learning & Analytics

Contains price forecasting models, crop planning guidance, and backtesting benchmarks.

### Guiding Principles:
1. Every model must beat naive baseline models on a time-based backtest.
2. Error metrics and uncertainty intervals must be transparently reported.
3. Predictions must always be explicitly labeled "guidance only".
4. Strict prevention of future-data leakage in train/validation splits.
