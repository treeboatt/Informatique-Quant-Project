from collections.abc import Callable


# only one variable moves (x), everything else is frozen in param.
# so the same class gives the delta, the vega or the rho: we just
# change the function we pass to it
class OneDimDerivative:
    def __init__(self, function: Callable[[object, float], float],
                 other_parameters: object, shift: float = 1.0):
        self.f = function
        self.param = other_parameters
        self.shift = shift

    # slope. we move on both sides of x so the errors compensate each other
    def first(self, x: float) -> float:
        up = self.f(self.param, x + self.shift)
        down = self.f(self.param, x - self.shift)
        return (up - down) / (2.0 * self.shift)

    # curvature: how much the slope changes. we need the middle point too
    def second(self, x: float) -> float:
        up = self.f(self.param, x + self.shift)
        mid = self.f(self.param, x)
        down = self.f(self.param, x - self.shift)
        return (up - 2.0 * mid + down) / (self.shift * self.shift)