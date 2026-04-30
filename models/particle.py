from typing import override

class Particle:
    def __init__(
        self,
        position,
        velocity,
        fitness_value,
    ):
        self.position = position.copy()
        self.velocity = velocity.copy()
        self.best_pos = self.position.copy()
        self.best_val = fitness_value

    @override
    def __str__(self) -> str:
        return f"Position: {self.position}\nValue: {self.best_val}"
