from collections.abc import Callable


# one variable moves, the rest is frozen in param
class OneDimDerivative:
    def __init__(self, function: Callable[[object, float], float],
                 other_parameters: object, shift: float = 1.0):
        self.f = function
        self.param = other_parameters
        self.shift = shift

    # slope, centred on x
    def first(self, x: float) -> float:
        up = self.f(self.param, x + self.shift)
        down = self.f(self.param, x - self.shift)
        return (up - down) / (2.0 * self.shift)

    # curvature
    def second(self, x: float) -> float:
        up = self.f(self.param, x + self.shift)
        mid = self.f(self.param, x)
        down = self.f(self.param, x - self.shift)
        return (up - 2.0 * mid + down) / (self.shift * self.shift)
