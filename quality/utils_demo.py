# backend/quality/utils_demo.py
import numpy as np

# Parámetros "demo" por dimensión (las que pide tu frontend)
_PARAMS = {
    'diameter_mm':  {'mu': 16.0,  'sigma': 0.18},
    'thickness_mm': {'mu': 2.20,  'sigma': 0.07},
    'weight_g':     {'mu': 120.0, 'sigma': 5.0},
    # También soportamos las "reales" como demo, por si el front las pide
    'promedio':     {'mu': 60.0,  'sigma': 5.0},   # ciclo (seg) solo como prueba
    'th':           {'mu': 60.0,  'sigma': 8.0},   # tubos/hora solo como prueba
}

def synth_series(dimension: str, n: int):
    """
    Genera una serie normal para la 'dimension' solicitada.
    Lanza KeyError si la dimension no está soportada (lo capturamos en la view).
    """
    if dimension not in _PARAMS:
        raise KeyError(f'Dimension not supported in demo: {dimension}')
    p = _PARAMS[dimension]
    return np.random.normal(p['mu'], p['sigma'], size=int(n))
