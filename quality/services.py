from math import sqrt, erf
import numpy as np

def mean(x):
    return float(np.mean(x)) if len(x) else float('nan')

def stdev_sample(x):
    return float(np.std(x, ddof=1)) if len(x) > 1 else float('nan')

def stdev_pop(x):
    return float(np.std(x, ddof=0)) if len(x) else float('nan')

def normal_cdf(z):
    return 0.5 * (1 + erf(z / sqrt(2)))

def capability(xs, lsl, usl):
    xs = np.array(xs, dtype=float)
    mu = mean(xs)
    s = stdev_sample(xs)
    s_pop = stdev_pop(xs)
    cp = (usl - lsl) / (6 * s) if s and s == s else float('nan')
    cpk = min((usl - mu) / (3 * s), (mu - lsl) / (3 * s)) if s and s == s else float('nan')
    pp = (usl - lsl) / (6 * s_pop) if s_pop and s_pop == s_pop else float('nan')
    ppk = min((usl - mu) / (3 * s_pop), (mu - lsl) / (3 * s_pop)) if s_pop and s_pop == s_pop else float('nan')
    sigma_level = 3 * cpk if cpk and cpk == cpk else float('nan')
    return {'mu': mu, 's_sample': s, 's_pop': s_pop, 'cp': cp, 'cpk': cpk, 'pp': pp, 'ppk': ppk, 'sigma_level': sigma_level}

def xbar_r_groups(xs, group_size=5):
    import numpy as np
    xs = np.array(xs, dtype=float)
    groups = [xs[i:i+group_size] for i in range(0, len(xs), group_size) if len(xs[i:i+group_size])==group_size]
    if not groups:
        return {'groups': [], 'xbar': [], 'r': []}
    xb = [float(np.mean(g)) for g in groups]
    rs = [float(np.max(g) - np.min(g)) for g in groups]
    const = {
        2: (1.880, 0.577, 0),
        3: (1.023, 0, 2.574),
        4: (0.729, 0, 2.282),
        5: (0.577, 0, 2.114),
        6: (0.483, 0, 2.004),
        7: (0.419, 0.076, 1.924),
        8: (0.373, 0.136, 1.864),
        9: (0.337, 0.184, 1.816),
        10:(0.308, 0.223, 1.777)
    }
    A2, D3, D4 = const.get(group_size, (0.577, 0, 2.114))
    xbarbar = float(np.mean(xb))
    rbar = float(np.mean(rs))
    ucl_x = xbarbar + A2 * rbar
    lcl_x = xbarbar - A2 * rbar
    ucl_r = D4 * rbar
    lcl_r = D3 * rbar
    return {'groups': groups,'xbar': xb,'r': rs,'xbarbar': xbarbar,'rbar': rbar,'ucl_x': ucl_x,'lcl_x': lcl_x,'ucl_r': ucl_r,'lcl_r': lcl_r}

def histogram_bins(xs, bins=12):
    import numpy as np
    xs = np.array(xs, dtype=float)
    hist, edges = np.histogram(xs, bins=bins)
    centers = list((edges[:-1] + edges[1:]) / 2)
    return {'counts': list(map(int, hist)), 'centers': list(map(float, centers)), 'edges': list(map(float, edges))}

def pareto(defect_counts: dict):
    total = sum(defect_counts.values()) or 1
    items = sorted(defect_counts.items(), key=lambda kv: kv[1], reverse=True)
    cum = 0
    series = []
    for k, v in items:
        cum += v
        series.append({'category': k, 'count': v, 'cum_perc': round(100 * cum / total, 2)})
    return series

# ======= UTILIDADES SIX SIGMA (ALINEADAS A TU BD REAL) =======
from math import isnan
from typing import Dict
try:
    from scipy.stats import norm
except Exception:
    norm = None

def sigma_from_dpmo(dpmo: float) -> float | None:
    """
    Aproximación clásica: Sigma ≈ NORMSINV(1 - DPMO/1e6) + 1.5
    Devuelve None si no hay SciPy o dpmo inválido.
    """
    if dpmo is None or dpmo < 0:
        return None
    if norm is None:
        return None
    p = max(1e-12, 1.0 - (dpmo / 1_000_000.0))
    z = norm.ppf(p)
    return round(z + 1.5, 2)

def aggregate_scrap(scrap_rows, opportunities_per_unit: int = 1) -> Dict:
    """
    Recibe filas de la tabla SCRAP (fecha, total_producido, total_defectuoso)
    y calcula serie de rendimiento (yield%), DPMO y Sigma por día, más totales.
    """
    trend = []
    tot_u = 0
    tot_d = 0
    for r in scrap_rows:
        u = int(r.get('total_producido') or 0)
        d = int(r.get('total_defectuoso') or 0)
        tot_u += u
        tot_d += d
        y = (u - d) / u * 100 if u > 0 else 0.0
        dpu = (d / u) if u > 0 else 0.0
        dpmo = dpu * opportunities_per_unit * 1_000_000.0
        trend.append({
            'fecha': r['fecha'],
            'units': u,
            'defects': d,
            'yield_perc': round(y, 3),
            'dpmo': round(dpmo, 2),
            'sigma': sigma_from_dpmo(dpmo)
        })
    overall_dpmo = ((tot_d / tot_u) * opportunities_per_unit * 1_000_000.0) if tot_u else None
    return {
        'trend': trend,
        'overall': {
            'total_units': tot_u,
            'total_defects': tot_d,
            'overall_yield': round((tot_u - tot_d) / tot_u * 100, 3) if tot_u else 0.0,
            'overall_dpmo': round(overall_dpmo, 2) if overall_dpmo is not None else None,
            'overall_sigma': sigma_from_dpmo(overall_dpmo) if overall_dpmo is not None else None,
        }
    }
