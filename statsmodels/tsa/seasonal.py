"""
Seasonal Decomposition by Moving Averages
"""
from statsmodels.compat.pandas import deprecate_kwarg

import numpy as np
import pandas as pd
from pandas.core.nanops import nanmean as pd_nanmean
from statsmodels.tsa._stl import STL

from statsmodels.tools.validation import array_like, PandasWrapper
from statsmodels.tsa.tsatools import freq_to_period
from .filters.filtertools import convolution_filter

__all__ = ['STL', 'seasonal_decompose', 'seasonal_mean', 'DecomposeResult']


def _extrapolate_trend(trend, npoints):
    """
    Replace nan values on trend's end-points with least-squares extrapolated
    values with regression considering npoints closest defined points.
    """
    front = next(i for i, vals in enumerate(trend)
                 if not np.any(np.isnan(vals)))
    back = trend.shape[0] - 1 - next(i for i, vals in enumerate(trend[::-1])
                                     if not np.any(np.isnan(vals)))
    front_last = min(front + npoints, back)
    back_first = max(front, back - npoints)

    k, n = np.linalg.lstsq(
        np.c_[np.arange(front, front_last), np.ones(front_last - front)],
        trend[front:front_last], rcond=-1)[0]
    extra = (np.arange(0, front) * np.c_[k] + np.c_[n]).T
    if trend.ndim == 1:
        extra = extra.squeeze()
    trend[:front] = extra

    k, n = np.linalg.lstsq(
        np.c_[np.arange(back_first, back), np.ones(back - back_first)],
        trend[back_first:back], rcond=-1)[0]
    extra = (np.arange(back + 1, trend.shape[0]) * np.c_[k] + np.c_[n]).T
    if trend.ndim == 1:
        extra = extra.squeeze()
    trend[back + 1:] = extra

    return trend


@deprecate_kwarg('freq', 'period')
def seasonal_mean(x, period):
    """
    Return means for each period in x. period is an int that gives the
    number of periods per cycle. E.g., 12 for monthly. NaNs are ignored
    in the mean.
    """
    return np.array([pd_nanmean(x[i::period], axis=0) for i in range(period)])


@deprecate_kwarg('freq', 'period')
def seasonal_decompose(x, model="additive", filt=None, period=None,
                       two_sided=True, extrapolate_trend=0):
    """
    Seasonal decomposition using moving averages

    Parameters
    ----------
    x : array_like
        Time series. If 2d, individual series are in columns. x must contain 2
        complete cycles.
    model : str {"additive", "multiplicative"}
        Type of seasonal component. Abbreviations are accepted.
    filt : array_like
        The filter coefficients for filtering out the seasonal component.
        The concrete moving average method used in filtering is determined by
        two_sided.
    period : int, optional
        Period of the series. Must be used if x is not a pandas object or if
        the index of x does not have  a frequency. Overrides default
        periodicity of x if x is a pandas object with a timeseries index.
    two_sided : bool
        The moving average method used in filtering.
        If True (default), a centered moving average is computed using the
        filt. If False, the filter coefficients are for past values only.
    extrapolate_trend : int or 'freq', optional
        If set to > 0, the trend resulting from the convolution is
        linear least-squares extrapolated on both ends (or the single one
        if two_sided is False) considering this many (+1) closest points.
        If set to 'freq', use `freq` closest points. Setting this parameter
        results in no NaN values in trend or resid components.

    Returns
    -------
    results : DecomposeResult
        A object with seasonal, trend, and resid attributes.

    Notes
    -----
    This is a naive decomposition. More sophisticated methods should
    be preferred.

    The additive model is Y[t] = T[t] + S[t] + e[t]

    The multiplicative model is Y[t] = T[t] * S[t] * e[t]

    The seasonal component is first removed by applying a convolution
    filter to the data. The average of this smoothed series for each
    period is the returned seasonal component.

    See Also
    --------
    statsmodels.tsa.filters.bk_filter.bkfilter
    statsmodels.tsa.filters.cf_filter.xffilter
    statsmodels.tsa.filters.hp_filter.hpfilter
    statsmodels.tsa.filters.convolution_filter
    statsmodels.tsa.seasonal.STL
    """
    pfreq = period
    pw = PandasWrapper(x)
    if period is None:
        pfreq = getattr(getattr(x, 'index', None), 'inferred_freq', None)

    x = array_like(x, 'x', maxdim=2)
    nobs = len(x)

    if not np.all(np.isfinite(x)):
        raise ValueError("This function does not handle missing values")
    if model.startswith('m'):
        if np.any(x <= 0):
            raise ValueError("Multiplicative seasonality is not appropriate "
                             "for zero and negative values")

    if period is None:
        if pfreq is not None:
            pfreq = freq_to_period(pfreq)
            period = pfreq
        else:
            raise ValueError("You must specify a period or x must be a "
                             "pandas object with a DatetimeIndex with "
                             "a freq not set to None")
    if x.shape[0] < 2 * pfreq:
        raise ValueError('x must have 2 complete cycles requires {0} '
                         'observations. x only has {1} '
                         'observation(s)'.format(2 * pfreq, x.shape[0]))

    if filt is None:
        if period % 2 == 0:  # split weights at ends
            filt = np.array([.5] + [1] * (period - 1) + [.5]) / period
        else:
            filt = np.repeat(1. / period, period)

    nsides = int(two_sided) + 1
    trend = convolution_filter(x, filt, nsides)

    if extrapolate_trend == 'freq':
        extrapolate_trend = period - 1

    if extrapolate_trend > 0:
        trend = _extrapolate_trend(trend, extrapolate_trend + 1)

    if model.startswith('m'):
        detrended = x / trend
    else:
        detrended = x - trend

    period_averages = seasonal_mean(detrended, period)

    if model.startswith('m'):
        period_averages /= np.mean(period_averages, axis=0)
    else:
        period_averages -= np.mean(period_averages, axis=0)

    seasonal = np.tile(period_averages.T, nobs // period + 1).T[:nobs]

    if model.startswith('m'):
        resid = x / seasonal / trend
    else:
        resid = detrended - seasonal

    results = []
    for s, name in zip((seasonal, trend, resid, x),
                       ('seasonal', 'trend', 'resid', None)):
        results.append(pw.wrap(s.squeeze(), columns=name))
    return DecomposeResult(seasonal=results[0], trend=results[1],
                           resid=results[2], observed=results[3])


class DecomposeResult(object):
    def __init__(self, observed, seasonal, trend, resid, weights=None):
        self._seasonal = seasonal
        self._trend = trend
        if weights is None:
            weights = np.ones_like(observed)
            if isinstance(observed, pd.Series):
                weights = pd.Series(weights, index=observed.index,
                                    name='weights')
        self._weights = weights
        self._resid = resid
        self._observed = observed

    @property
    def observed(self):
        """Observed data"""
        return self._observed

    @property
    def seasonal(self):
        """The estimated seasonal component"""
        return self._seasonal

    @property
    def trend(self):
        """The estimated trend component"""
        return self._trend

    @property
    def resid(self):
        """The estimated residuals"""
        return self._resid

    @property
    def weights(self):
        """The weights used in the robust estimation"""
        return self._weights

    @property
    def nobs(self):
        """Number of observations"""
        return self._observed.shape

    def plot(self, observed=True, seasonal=True, trend=True, resid=True,
             weights=False):
        """
        Plot estimated components

        Parameters
        ----------
        observed: bool
            Include the observed series in the plot
        seasonal: bool
            Include the seasonal component in the plot
        trend: bool
            Include the trend component in the plot
        resid: bool
            Include the residual in the plot
        weights: bool
            Include the weights in the plot (if any)

        Returns
        -------
        fig : matplotlib.figure.Figure
            The figure instance that containing the plot
        """
        from statsmodels.graphics.utils import _import_mpl
        from pandas.plotting import register_matplotlib_converters
        plt = _import_mpl()
        register_matplotlib_converters()
        series = [(self._observed, 'Observed')] if observed else []
        series += [(self.trend, 'trend')] if trend else []
        series += [(self.seasonal, 'seasonal')] if seasonal else []
        series += [(self.resid, 'residual')] if resid else []
        series += [(self.weights, 'weights')] if weights else []

        if isinstance(self._observed, (pd.DataFrame, pd.Series)):
            nobs = self._observed.shape[0]
            xlim = self._observed.index[0], self._observed.index[nobs - 1]
        else:
            xlim = (0, self._observed.shape[0] - 1)

        fig, axs = plt.subplots(len(series), 1)
        for i, (ax, (series, def_name)) in enumerate(zip(axs, series)):
            if def_name != 'residual':
                ax.plot(series)
            else:
                ax.plot(series, marker='o', linestyle='none')
                ax.plot(xlim, (0, 0), color='#000000', zorder=-3)
            name = getattr(series, 'name', def_name)
            if def_name != 'Observed':
                name = name.capitalize()
            title = ax.set_title if i == 0 and observed else ax.set_ylabel
            title(name)
            ax.set_xlim(xlim)

        fig.tight_layout()
        return fig
