import math


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_price(
    s0: float, strike: float, T: float, rate: float, vol: float, is_call: bool = True
) -> float:
    d1 = (math.log(s0 / strike) + (rate + vol**2 / 2) * T) / (vol * math.sqrt(T))
    d2 = d1 - vol * math.sqrt(T)
    if is_call:
        return s0 * norm_cdf(d1) - strike * math.exp(-rate * T) * norm_cdf(d2)
    return strike * math.exp(-rate * T) * norm_cdf(-d2) - s0 * norm_cdf(-d1)
