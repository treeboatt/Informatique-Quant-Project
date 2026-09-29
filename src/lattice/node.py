import datetime

# Tolerance on probabilities outside [0, 1], to absorb rounding errors
PROBA_TOLERANCE = 1e-12


class Node:
    # The use of __slots__ is important to not break the RAM
    __slots__ = ['price', 'tree', 'up', 'down', 'next_up', 'next_mid', 'next_down', 
                 'p_up', 'p_mid', 'p_down', 'proba_reach', 'option_value']

    def __init__(self, price: float, tree):
        self.price = price
        self.tree = tree
        
        self.up = None
        self.down = None
        
        self.next_up = None
        self.next_mid = None
        self.next_down = None
        
        # Probabilities
        self.p_up = 0.0
        self.p_mid = 0.0
        self.p_down = 0.0
        
        # Pruning et pricing
        self.proba_reach = 0.0
        self.option_value = None

    def get_or_create_up(self):
        """
        Returns the node directly above this one.
        If it does not exist, it creates it and links both nodes.
        """
        if self.up is not None:
            return self.up
            
        # Calculate the price for the upper node using alpha
        new_price = self.price * self.tree.alpha
        new_node = Node(new_price, self.tree)
        
        # Link the nodes together
        self.up = new_node
        new_node.down = self
        
        return new_node

    def get_or_create_down(self):
        """
        Returns the node directly below this one.
        If it does not exist, it creates it and links both nodes.
        """
        if self.down is not None:
            return self.down
            
        # Calculate the price for the lower node using alpha
        new_price = self.price / self.tree.alpha
        new_node = Node(new_price, self.tree)
        
        # Link the nodes together
        self.down = new_node
        new_node.up = self
        
        return new_node

    def find_closest(self, target: float):
        """
        Finds the closest node to the target forward price. 
        Moves up or down the column by creating nodes if necessary.
        """
        assert target > 0, "forward negatif : ce noeud doit etre elague"
        current = self
        alpha = self.tree.alpha
        
        # Move up as long as the target is closer to the upper node
        # Threshold formula: target > S * (1 + alpha) / 2
        while target > current.price * (1.0 + alpha) / 2.0:
            current = current.get_or_create_up()
            
        # Move down as long as the target is closer to the lower node
        # Threshold formula: target < S * (1 + 1/alpha) / 2
        while target < current.price * (1.0 + 1.0 / alpha) / 2.0:
            current = current.get_or_create_down()
            
        return current

    def compute_probabilities(self, fwd: float, var: float):
        """
        Computes trinomial probabilities
        """
        alpha = self.tree.alpha
        s_mid = self.next_mid.price
        
        # Stable form formula for p_down
        numerator = (
            (var + (fwd + s_mid) * (fwd - s_mid)) / (s_mid ** 2)
            - (alpha + 1.0) * (fwd / s_mid - 1.0)
        )
        denominator = (1.0 - alpha) * (alpha ** -2 - 1.0)
        self.p_down = numerator / denominator
        
        # Formula for p_up based on p_down and expected value match
        self.p_up = ((fwd / s_mid - 1.0) - (1.0 / alpha - 1.0) * self.p_down) / (alpha - 1.0)
        
        # The sum of probabilities must be exactly 1
        self.p_mid = 1.0 - self.p_up - self.p_down

        if not self.has_valid_probabilities():
            self.prune_invalid()

    def set_constant_probabilities(self):
        """
        Copies the probabilities computed once in the tree.
        Valid when there is no dividend in the period: next_mid is then aligned
        on the forward, and the probabilities are the same for every node.
        """
        self.p_up = self.tree.p_up
        self.p_mid = self.tree.p_mid
        self.p_down = self.tree.p_down

    def has_valid_probabilities(self) -> bool:
        """
        Returns True if the three probabilities are in [0, 1],
        up to a small rounding tolerance.
        """
        low, high = -PROBA_TOLERANCE, 1.0 + PROBA_TOLERANCE
        return (low <= self.p_up <= high
                and low <= self.p_mid <= high
                and low <= self.p_down <= high)

    def prune_invalid(self):
        """
        Handles a node whose moments cannot be matched (probability outside [0, 1]
        or forward <= 0: large dividend at the very bottom of the tree).
        If the node is practically unreachable, it goes to next_mid with
        probability 1 and is counted in tree.nb_invalid_nodes; otherwise the
        tree cannot price this case and a ValueError is raised.
        """
        if self.proba_reach >= self.tree.prune_threshold:
            raise ValueError(
                f"probabilites hors de [0, 1] (p_up = {self.p_up:.4%}, "
                f"p_mid = {self.p_mid:.4%}, p_down = {self.p_down:.4%}) "
                f"sur un noeud atteignable (prix {self.price:.6f}, "
                f"proba d'atteinte {self.proba_reach:.2e})"
            )
        self.p_up = 0.0
        self.p_mid = 1.0
        self.p_down = 0.0
        self.tree.nb_invalid_nodes += 1


class TrunkNode(Node):
    # We add only attributes for TrunkNode
    __slots__ = ['prec_mid', 'column_date', 'is_div_in_next_period']

    def __init__(self, price: float, tree, prec_mid=None, column_date: datetime.datetime=None):
        super().__init__(price, tree)
        self.prec_mid = prec_mid
        self.column_date = column_date
        # True if column_date < div_ex_date <= next_date, with a tolerance on dates
        ex_date = tree.market.div_ex_date
        next_date = self.next_date()
        self.is_div_in_next_period = (
            ex_date is not None
            and column_date is not None
            and not self.are_same_dates(column_date, ex_date)
            and column_date < ex_date
            and (ex_date < next_date or self.are_same_dates(ex_date, next_date))
        )

    def next_date(self) -> datetime.datetime:
        """
        Returns the exact date of the next column.
        """
        if self.column_date is not None and self.tree.step_timedelta is not None:
            return self.column_date + self.tree.step_timedelta
        return None

    def are_same_dates(self, d1: datetime.datetime, d2: datetime.datetime) -> bool:
        """
        Returns True if the two dates are closer than a small fraction of time
        with Tolerance: < 1 day / N / 1000.

        """
        if d1 is None or d2 is None:
            return False
            
        # Tolerance definition to handle discrete date equality robustly
        tolerance = datetime.timedelta(days=1) / (self.tree.nb_steps * 1000.0)
        
        # Note: If d1 and d2 are datetime or pandas timestamps, subtraction yields a timedelta.
        # We assume d1 and d2 support subtraction yielding a timedelta-like object.
        return abs(d1 - d2) < tolerance