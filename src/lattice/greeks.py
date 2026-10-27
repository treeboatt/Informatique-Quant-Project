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


# deux variables bougent ensemble, pour les grecques croisees comme le vanna
# (spot et volatilite). OneDimDerivative ne sait pas faire : il gele tout
# sauf une variable
class TwoDimDerivative:
    def __init__(self, function: Callable[[object, float, float], float],
                 other_parameters: object, shift_x: float = 1.0, shift_y: float = 0.01):
        self.f = function
        self.param = other_parameters
        self.shift_x = shift_x
        self.shift_y = shift_y

    # on price aux quatre coins d'un petit rectangle. les deux signes plus et
    # les deux signes moins annulent ce qui ne depend que d'une seule variable
    def cross(self, x: float, y: float) -> float:
        h, k = self.shift_x, self.shift_y
        haut_droite = self.f(self.param, x + h, y + k)
        haut_gauche = self.f(self.param, x + h, y - k)
        bas_droite = self.f(self.param, x - h, y + k)
        bas_gauche = self.f(self.param, x - h, y - k)
        return (haut_droite - haut_gauche - bas_droite + bas_gauche) / (4.0 * h * k)
