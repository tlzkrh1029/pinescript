"""Backtest of the BTC %ex (cost per transaction) in/out rules on daily data.

Data: Coin Metrics Community API (free, no key). Miner revenue is rebuilt as
(IssTotNtv + FeeTotNtv) * PriceUSD because RevUSD is not in the community tier.

Timing: Coin Metrics publishes day D after D closes. At the close of day D a trader
knows the price of D but only CPT up to D-1, and the position is held during D+1.
So for the return of day t: CPT state uses day t-2, the price filter uses day t-1.

Usage: python3 cpt_backtest.py [path/to/cache.csv]
"""
import io
import sys
import urllib.request

import numpy as np
import pandas as pd

URL = ('https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?assets=btc'
       '&metrics=TxCnt,PriceUSD,IssTotNtv,FeeTotNtv&frequency=1d&page_size=10000'
       '&start_time=2010-07-01&format=csv')
COST = 0.001  # per switch (one side)
START, END = '2014-01-01', None


def load(cache=None):
    if cache:
        raw = open(cache).read()
    else:
        raw = urllib.request.urlopen(URL, timeout=120).read().decode()
    df = pd.read_csv(io.StringIO(raw), na_values=['null'])
    df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None).dt.normalize()
    df = df.set_index('time')
    df['CPT'] = (df.IssTotNtv + df.FeeTotNtv) * df.PriceUSD / df.TxCnt
    return df


def normalize(s, n=100):
    lo, hi = s.rolling(n).min(), s.rolling(n).max()
    rng = hi - lo
    return ((s - lo) / rng).where(rng > 0)


def confirm(state, k):
    """Switch only after the raw state has held k consecutive days."""
    cur, cnt, out = False, 0, []
    for v in state.fillna(False).values:
        if v != cur:
            cnt += 1
            if cnt >= k:
                cur, cnt = v, 0
        else:
            cnt = 0
        out.append(cur)
    return pd.Series(out, index=state.index)


def strategy_returns(pos, ret):
    pos = pos.fillna(0).astype(float)
    return pos * ret - pos.diff().abs().fillna(0) * COST


def period_return(pos, ret, period):
    return (1 + strategy_returns(pos, ret).loc[period]).prod() - 1


def perf(pos, ret, start, end):
    pos = pos.loc[start:end].fillna(0).astype(float)
    trades = pos.diff().abs().fillna(0)
    sr = strategy_returns(pos, ret.loc[start:end])
    eq = (1 + sr).cumprod()
    yrs = len(sr) / 365.0
    return {'CAGR': eq.iloc[-1] ** (1 / yrs) - 1, 'MDD': (eq / eq.cummax() - 1).min(),
            'Sharpe': sr.mean() / sr.std() * np.sqrt(365), 'Exposure': pos.mean(),
            'Trades/yr': trades.sum() / yrs}


def main():
    df = load(sys.argv[1] if len(sys.argv) > 1 else None)
    px, ret = df.PriceUSD, df.PriceUSD.pct_change()
    end = END or str(df.index[-1].date())
    norm = normalize(df.CPT)
    ma = {n: norm.rolling(n).mean() for n in (5, 7, 50, 200)}
    pnorm = normalize(px)
    above50 = px > px.rolling(50).mean()
    above200 = px > px.rolling(200).mean()

    cpt_5_200 = ma[5] > ma[200]
    cpt_strict = (ma[5] > ma[50]) & (ma[5] > ma[200])
    cpt_7_200 = ma[7] > ma[200]
    # position held on day t
    rules = {
        'A  CPT 5>200 (chart view, 1-day look-ahead)': cpt_5_200.shift(1),
        'A  CPT 5>200': cpt_5_200.shift(2),
        'A2 CPT 5>50 & 5>200': cpt_strict.shift(2),
        'B  CPT 5>200 + close>SMA50': cpt_5_200.shift(2) & above50.shift(1),
        'C  CPT 7>200 + close>SMA50': cpt_7_200.shift(2) & above50.shift(1),
        'D  B, 3-day confirm': confirm(cpt_5_200.shift(1) & above50, 3).shift(1),
        'P  price-stoch 5>200 (same transform on price)':
            (pnorm.rolling(5).mean() > pnorm.rolling(200).mean()).shift(1),
        'G  close>SMA50 & close>SMA200': (above50 & above200).shift(1),
        'H  close>SMA50': above50.shift(1),
        'Buy & hold': pd.Series(True, index=px.index),
    }
    fmt = {'CAGR': '{:.1%}'.format, 'MDD': '{:.1%}'.format, 'Sharpe': '{:.2f}'.format,
           'Exposure': '{:.0%}'.format, 'Trades/yr': '{:.1f}'.format}
    pd.set_option('display.width', 200)
    for s, e in [(START, end), ('2014-01-01', '2017-12-31'), ('2018-01-01', '2021-12-31'),
                 ('2022-01-01', end), ('2024-01-01', end)]:
        t = pd.DataFrame({k: perf(v, ret, s, e) for k, v in rules.items()}).T
        print(f'\n=== {s} ~ {e}  (cost {COST:.1%} per switch)')
        print(t.to_string(formatters=fmt))

    print('\n=== Calendar-year returns')
    cols = ['Buy & hold', 'A  CPT 5>200', 'B  CPT 5>200 + close>SMA50',
            'C  CPT 7>200 + close>SMA50', 'G  close>SMA50 & close>SMA200']
    years = range(2014, int(end[:4]) + 1)
    yr = {y: {k: period_return(rules[k], ret, str(y)) for k in cols} for y in years}
    print(pd.DataFrame(yr).T.to_string(float_format=lambda x: f'{x:+.0%}'))

    # What drives CPT: log CPT = log price + log(BTC revenue) - log(tx count)
    print('\n=== Share of log-CPT variance by component (2023 ~)')
    lp, lr, lt, lc = (np.log(x).loc['2023':] for x in
                      (px, df.IssTotNtv + df.FeeTotNtv, df.TxCnt, df.CPT))
    for h in (1, 30, 100):
        v = lc.diff(h).var()
        print(f'  {h:3d}-day changes: price {lc.diff(h).cov(lp.diff(h)) / v:.2f}, '
              f'tx count {lc.diff(h).cov(-lt.diff(h)) / v:.2f}, BTC revenue {lc.diff(h).cov(lr.diff(h)) / v:.2f}')

    # Lead/lag: 20-day change of MA5 vs 20-day BTC log return ending k days later
    print('\n=== Cross-correlation, 20d change of CPT MA5 vs 20d BTC return shifted k days (k>0: indicator first)')
    x, y = ma[5].diff(20), np.log(px).diff(20)
    ks = [-20, -10, -5, 0, 5, 10, 20]
    print('  k    ' + ' '.join(f'{k:+5d}' for k in ks))
    print('  corr ' + ' '.join(f'{pd.concat([x, y.shift(-k)], axis=1).loc[START:].dropna().corr().iloc[0, 1]:+5.2f}' for k in ks))

    # Price path around state flips (flip seen on day D, tradable from D+1)
    print('\n=== Mean BTC move around CPT 5>200 flips (2014 ~)')
    lpx = np.log(px)
    flips = cpt_5_200.astype(int).diff()
    for name, val in (('to ON ', 1), ('to OFF', -1)):
        idx = [lpx.index.get_loc(d) for d in flips[flips == val].loc[START:].index]
        idx = [i for i in idx if 60 <= i < len(lpx) - 61]
        before = np.mean([lpx.iloc[i] - lpx.iloc[i - 60] for i in idx])
        after = np.mean([lpx.iloc[i + 61] - lpx.iloc[i + 1] for i in idx])
        print(f'  {name}: n={len(idx)}, prior 60d {np.expm1(before):+.1%}, next 60d {np.expm1(after):+.1%}')

    # Forward 30-day return by state. Non-overlapping samples depend on the starting day,
    # so the test is repeated for all 30 offsets; the tx-count-only version isolates the on-chain part.
    print('\n=== Forward 30d BTC return, ON minus OFF, non-overlapping samples over all 30 offsets (2014 ~)')
    fwd = lpx.shift(-31) - lpx.shift(-1)
    tnorm = normalize(1 / df.TxCnt)
    for name, st in (('CPT 5>200', cpt_5_200),
                     ('1/tx count only 5>200', tnorm.rolling(5).mean() > tnorm.rolling(200).mean()),
                     ('price-stoch 5>200', pnorm.rolling(5).mean() > pnorm.rolling(200).mean()),
                     ('close>SMA200', above200)):
        z = pd.concat([st.shift(1).rename('s'), fwd.rename('f')], axis=1).loc[START:].dropna()
        z['s'] = z.s.astype(bool)
        diffs, ts = [], []
        for off in range(30):
            w = z.iloc[off::30]
            on, of = w.f[w.s], w.f[~w.s]
            diffs.append(on.mean() - of.mean())
            ts.append(diffs[-1] / np.sqrt(on.var() / len(on) + of.var() / len(of)))
        print(f'  {name:22s} ON-OFF {np.median(diffs):+.1%} (median), t median {np.median(ts):+.2f}, '
              f'range {min(ts):+.2f} ~ {max(ts):+.2f}')

    print('\n=== Halvings: CPT drop and share of the next 120 days in OFF (CPT 5>200)')
    for h in ('2016-07-09', '2020-05-11', '2024-04-20'):
        d = pd.Timestamp(h)
        cpt_chg = df.CPT.loc[d + pd.Timedelta(days=1):d + pd.Timedelta(days=14)].mean() / \
            df.CPT.loc[d - pd.Timedelta(days=14):d - pd.Timedelta(days=1)].mean() - 1
        off = 1 - cpt_5_200.loc[d:d + pd.Timedelta(days=120)].mean()
        print(f'  {h}: CPT {cpt_chg:+.0%}, OFF {off:.0%} of next 120d, BTC next 120d '
              f'{px.loc[d + pd.Timedelta(days=120)] / px.loc[d] - 1:+.0%}')

    print('\n=== Weekday pattern: log CPT vs centered 7-day mean (2023 ~)')
    c = np.log(df.CPT).loc['2023':]
    dev = (c - c.rolling(7, center=True).mean()).groupby(c.index.dayofweek).mean()
    print('  ' + ', '.join(f'{d} {v:+.1%}' for d, v in zip(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'], dev)))

    print('\n=== Sharpe of CPT MA(short) > MA(long) alone over the full period (rows short, cols long)')
    grid = {sh: {lg: perf((norm.rolling(sh).mean() > norm.rolling(lg).mean()).shift(2), ret, START, end)['Sharpe']
                 for lg in (100, 150, 200, 250, 300)} for sh in (3, 5, 7, 10, 14)}
    print(pd.DataFrame(grid).T.round(2).to_string())


if __name__ == '__main__':
    main()
