import numpy as np
from typing import Optional
from matplotlib.axes import Axes

# helpers
def snap_to_grid():
    pass

def fir_filtered_pmf(
    p: Pmf1D, 
    fir: np.ndarray, 
    *, 
    keep_mass: float = float(1-1e-5), 
    tap_rel_th: float = 0.0,
    max_taps: Optional[int] = None,
    name: Optional[str] = None
) -> Pmf1D:
    pass

def _truncate_keep_mass(p: Pmf1D, *, keep_mass: float) -> Pmf1D:
    pass

def _prune_fir_coeff(
    fir: np.ndarray,
    *,
    tap_rel_th: float = 0.0,
    max_taps: Optional[int] = None
) -> np.ndarray:
    pass

class Pmf1D:
    def __init__(self, dx: float, st_idx: int, pmf: np.ndarray, unit: str = "", name: str = ""):
        self.dx = dx
        self.st_idx = st_idx    # 以dx為單位的絕對座標起始位置
        self.x_st = st_idx * dx
        self.pmf = pmf
        self.unit = unit
        self.name = name

    @property
    def x(self) -> np.ndarray:
        "Don't save 'x' to save memory."
        return (self.x_st + np.arange(len(self.pmf))*self.dx )

    # --------------------------------
    # constructors
    # --------------------------------
    @classmethod
    def uniform(cls):
        pass

    @classmethod
    def gaussian(cls):
        pass

    @classmethod
    def multi_dirac(cls):
        pass


    # --------------------------------
    # methods
    # --------------------------------
    def normalize(self, eps: float = 0.0) -> 'Pmf1D':
        pass

    def resample_dx(self, dx_new: float, *, name: Optional[str]=None) -> 'Pmf1D':
        pass

    def combine(self, other: 'Pmf1D') -> 'Pmf1D':
        pass