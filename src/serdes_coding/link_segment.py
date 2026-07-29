import numpy as np
from typing import Union
from dataclasses import dataclass, field
import skrf as rf

# =========================
# helper
# =========================
def isFreqsEqual(f1: np.ndarray, f2: np.ndarray, rtol: float = 1e-9, atol: float = 1e-6) -> bool:
    f1 = np.asarray(f1, dtype=float)
    f2 = np.asarray(f2, dtype=float)

    if f1.shape != f2.shape:
        return False

    return np.allclose(f1, f2, rtol=rtol, atol=atol)

def resample_tf(
    H_meas: np.ndarray,
    freqs_meas: np.ndarray,
    freqs_new: np.ndarray,
    taper_ratio: float = 0.25,
    min_tail_points: int = 5,
) -> np.ndarray:
    """
    Resample a measured transfer function onto the target rfft frequency grid.

    In band => linear interpolate.
    Out band:
        extends phase using estimated group delay (constant group delay), 
        and smoothly tapers magnitude to zero.
    """
    def normalize_and_validate_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        H = np.asarray(H_meas, dtype=complex)
        f_meas = np.asarray(freqs_meas, dtype=float)
        f_new = np.asarray(freqs_new, dtype=float)

        if H.shape != f_meas.shape:
            raise ValueError("H_meas and freqs_meas must have the same shape.")

        if f_meas.ndim != 1 or f_new.ndim != 1:
            raise ValueError("freqs_meas and freqs_new must be 1D arrays.")

        if len(f_meas) < 2 or len(f_new) < 2:
            raise ValueError("Frequency axes must contain at least two points.")

        if not np.all(np.isfinite(f_meas)) or not np.all(np.isfinite(f_new)):
            raise ValueError("Frequency axes must be finite.")

        if not np.all(np.diff(f_meas) > 0):
            raise ValueError("freqs_meas must be strictly increasing.")

        if not np.all(np.diff(f_new) > 0):
            raise ValueError("freqs_new must be strictly increasing.")

        # Check that the target FFT frequency axis is uniformly spaced.
        LinkConfig.validate_uniform_freqs(f_new)

        if f_meas[0] > f_new[0]:
            raise ValueError("freqs_meas must include the target DC / low-frequency start.")

        return H, f_meas, f_new

    def extend_phase_with_group_delay() -> None:
        tail = max(min_tail_points, len(freqs_meas) // 10)
        tail = min(tail, len(freqs_meas))

        p = np.polyfit(freqs_meas[-tail:], phase_meas[-tail:], 1)
        dphi_df = p[0]
        tau = -dphi_df / (2 * np.pi)

        beyond = freqs_new > f_stop
        phase_at_stop = phase_meas[-1]
        phase_new[beyond] = phase_at_stop - 2 * np.pi * tau * (freqs_new[beyond] - f_stop)

    def extend_mag_with_taper() -> None:
        beyond = freqs_new > f_stop
        taper_bw = taper_ratio * f_stop
        if taper_bw <= 0:
            raise ValueError("taper bandwidth must be positive.")

        f_taper_end = min(f_nyq, f_stop + taper_bw)

        if f_taper_end <= f_stop:
            mag_new[beyond] = 0.0
            return

        taper_region = (freqs_new > f_stop) & (freqs_new < f_taper_end)
        zero_region = freqs_new >= f_taper_end

        mag_at_stop = mag_meas[-1]

        u = (freqs_new[taper_region] - f_stop) / (f_taper_end - f_stop)
        taper = 0.5 * (1 + np.cos(np.pi * u))

        mag_new[taper_region] = mag_at_stop * taper
        mag_new[zero_region] = 0.0

    H_meas, freqs_meas, freqs_new = normalize_and_validate_inputs()
    f_stop = freqs_meas[-1]
    f_nyq = freqs_new[-1]

    mag_meas = np.abs(H_meas)
    phase_meas = np.unwrap(np.angle(H_meas))

    # Base interpolation region.
    interp_freq = np.minimum(freqs_new, f_stop)

    mag_new = np.interp(interp_freq, freqs_meas, mag_meas)
    phase_new = np.interp(interp_freq, freqs_meas, phase_meas)

    # Case A: measurement covers target Nyquist.
    if f_stop >= f_nyq:
        H_new = mag_new * np.exp(1j * phase_new)
        H_new[0] = H_new[0].real + 0j
        H_new[-1] = H_new[-1].real + 0j
        return H_new

    # Case B: measurement does not cover target Nyquist.
    extend_phase_with_group_delay()
    extend_mag_with_taper()

    H_new = mag_new * np.exp(1j * phase_new)

    # Real-valued h(t) constraints for rfft/irfft with even Nfft.
    H_new[0] = H_new[0].real + 0j
    H_new[-1] = H_new[-1].real + 0j

    return H_new

def _network_from_smatrix(
    freqs: np.ndarray,
    smatrix: np.ndarray,
    z0: Union[float, np.ndarray] = 100.0,
) -> 'rf.Network':
    frequency = rf.Frequency.from_f(freqs, unit="hz")
    return rf.Network(frequency=frequency, s=smatrix, z0=z0)

def _s4p_to_sdd(
    s4p: np.ndarray,
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
    freqs: np.ndarray | None = None,
) -> np.ndarray:
    """
    Convert single-ended S4P to differential-mode Sdd.

    port_order gives (tx_p, tx_n, rx_p, rx_n). After reordering to this
    convention, the through term is:
        Sdd21 = 0.5 * (S31 - S32 - S41 + S42)
    """
    if freqs is None:
        s4p = np.asarray(s4p, dtype=complex)
        if s4p.ndim != 3 or s4p.shape[1:] != (4, 4):
            raise ValueError("s4p must have shape (N, 4, 4).")
        if not np.all(np.isfinite(s4p)):
            raise ValueError("s4p contains non-finite values.")
    else:
        s4p = sparamModel.validate_s4p(s4p, freqs)

    port_order = sparamModel.validate_port_order(port_order)
    s = s4p[:, port_order, :][:, :, port_order]

    S11, S12, S13, S14 = s[:, 0, 0], s[:, 0, 1], s[:, 0, 2], s[:, 0, 3]
    S21, S22, S23, S24 = s[:, 1, 0], s[:, 1, 1], s[:, 1, 2], s[:, 1, 3]
    S31, S32, S33, S34 = s[:, 2, 0], s[:, 2, 1], s[:, 2, 2], s[:, 2, 3]
    S41, S42, S43, S44 = s[:, 3, 0], s[:, 3, 1], s[:, 3, 2], s[:, 3, 3]

    Sdd11 = 0.5 * (S11 - S12 - S21 + S22)
    Sdd21 = 0.5 * (S31 - S32 - S41 + S42)
    Sdd12 = 0.5 * (S13 - S14 - S23 + S24)
    Sdd22 = 0.5 * (S33 - S34 - S43 + S44)

    return np.stack([
        np.stack([Sdd11, Sdd12], axis=-1),
        np.stack([Sdd21, Sdd22], axis=-1),
    ], axis=-2)

# ========================
# classes
# ========================

@dataclass
class LinkConfig:
    """
    Frequency/time grid definition shared by LinkSegment and COM S-param builders.

    Class boundary
    --------------
    LinkConfig owns only sampling-grid convention:
    - baud frequency and UI
    - samples per UI
    - FFT length and rfft frequency axis
    - time axis used by impulse/step/single-bit responses

    It should not own channel data, S-parameters, or response conversion logic.
    """
    fb: float = 53.125e9                            # unit: Hz
    per_ui: int = 64
    target_df: float = 1e8

    # ----- derived attributes -----
    bt: float = field(init=False)
    L_ui: int = field(init=False)

    # fft pair setup
    Nfft: int = field(init=False)                   # even points, s.t. freqs include H(f=Fs/2)
    Fs: float = field(init=False)
    f_nyq: float = field(init=False)
    dt: float = field(init=False)
    df: float = field(init=False)
    T_max: float = field(init=False)
    freqs: np.ndarray = field(init=False)           # unit: Hz, positive half side, np.arange(0,Fs/2+df,df)
    times: np.ndarray = field(init=False)           # unit: sec
    times_ui: np.ndarray = field(init=False)        # unit: UI

    def __post_init__(self):
        self.bt = 1.0 / self.fb
        self.dt = self.bt / self.per_ui
        self.Fs = 1.0 / self.dt
        self.f_nyq = self.Fs / 2
        if (int(self.Fs / self.target_df)%2 == 0):
            self.Nfft = int(self.Fs / self.target_df)
        else:
            self.Nfft = int(self.Fs / self.target_df) + 1
        self.df = self.Fs / self.Nfft
        self.T_max = 1.0 / self.df
        self.freqs = np.fft.rfftfreq(self.Nfft, d=self.dt)      
        self.times = np.arange(self.Nfft) * self.dt
        self.L_ui = int(self.Nfft / self.per_ui)
        self.times_ui = self.times / self.bt

        self.validate_uniform_freqs(self.freqs)

        if (self.freqs[-1] != self.f_nyq):
            raise Exception("Error @ __post_init__")
        if (self.times[-1] != self.T_max-self.dt):
            raise Exception("Error @ __post_init__")

    @staticmethod
    def validate_freqs(freqs: np.ndarray) -> np.ndarray:
        freqs = np.asarray(freqs, dtype=float)

        # Check that the frequency axis is one-dimensional.
        if freqs.ndim != 1:
            raise ValueError("freqs must be a 1D array.")

        # Check that the frequency axis has enough points for interpolation.
        if len(freqs) < 2:
            raise ValueError("freqs must contain at least two points.")

        # Check that all frequency values are finite.
        if not np.all(np.isfinite(freqs)):
            raise ValueError("freqs contains non-finite values.")

        # Check that the frequency axis is non-negative.
        if freqs[0] < 0:
            raise ValueError("freqs must be non-negative.")

        # Check that the frequency axis is strictly increasing.
        if not np.all(np.diff(freqs) > 0):
            raise ValueError("freqs must be strictly increasing.")

        return freqs 

    @staticmethod
    def validate_uniform_freqs(freqs: np.ndarray, rtol: float = 1e-9, atol: float = 1e-6) -> np.ndarray:
        freqs = LinkConfig.validate_freqs(freqs)
        df = np.diff(freqs)

        # Check that every frequency step is equal within numerical tolerance.
        if not np.allclose(df, df[0], rtol=rtol, atol=atol):
            raise ValueError("freqs must be uniformly spaced.")

        return freqs

    @staticmethod
    def validate_times(times: np.ndarray) -> np.ndarray:
        times = np.asarray(times, dtype=float)

        if times.ndim != 1:
            raise ValueError("times must be a 1D array.")

        if len(times) < 2:
            raise ValueError("times must contain at least two points.")

        if not np.all(np.isfinite(times)):
            raise ValueError("times contains non-finite values.")

        if not np.all(np.diff(times) > 0):
            raise ValueError("times must be strictly increasing.")

        return times

class sparamModel:
    """
    Generic scikit-rf Network wrapper for differential S-parameter data.

    Class boundary
    --------------
    sparamModel is the generic container for Sdd two-port data after any required
    input normalization. It owns:
    - array / Touchstone / rf.Network ingestion
    - input validation contract for frequency axes, Sdd, S4P, and port order
    - single-ended S4P to differential-mode Sdd conversion
    - generic Sdd two-port cascade operations through scikit-rf
    - conversion from Sdd to terminated voltage transfer H21(f), then LinkSegment

    Mutation policy
    ---------------
    In-place methods update self.network and return self for chaining:
    - renormalize()
    - resample()
    - extrapolate_to_dc()
    - renum()

    Immutable methods return a modified copy and leave self unchanged:
    - renormalized()
    - resampled()
    - extrapolated_to_dc()
    - renumbered()

    It should not own IEEE COM primitive model construction such as shunt
    capacitance, package transmission line, Tx package, Rx package builders, or
    IEEE COM-specific cascade formulas and primitive model builders belong in
    com_model.py, not in this generic container.

    Internal storage
    ----------------
    S-parameters are stored as an rf.Network whose network.s is always
    COM-style differential-mode Sdd:
    - differential-mode Sdd array with shape (N, 2, 2)
    - single-ended S4P array with shape (N, 4, 4), then converts to Sdd

    The stored Sdd matrix uses the COM-style two-port order:
        [[Sdd11, Sdd12],
         [Sdd21, Sdd22]]

    For S4P conversion, the default port order is:
        (tx_p, tx_n, rx_p, rx_n) = (0, 1, 2, 3)
    using Python zero-based indices.
    """

    def __init__(
        self,
        network: 'rf.Network',
        source_type: str,
        port_order: tuple[int, int, int, int] | None = None,
    ):
        self.network = self.validate_network(network)
        self.source_type = source_type
        self.port_order = port_order

    # -------------------
    # constructors
    # -------------------
    @classmethod
    def from_sdd_array(cls, freqs: np.ndarray, sdd: np.ndarray, z0: float = 100.0) -> 'sparamModel':
        """
        Build from a differential-mode Sdd array.

        Input contract:
        - freqs: 1D, finite, strictly increasing frequency axis in Hz
        - sdd: complex array with shape (len(freqs), 2, 2)
        - z0: reference impedance assigned to the internal rf.Network
        """
        freqs = LinkConfig.validate_freqs(freqs)
        sdd = cls.validate_sdd(sdd, freqs)
        return cls(_network_from_smatrix(freqs, sdd, z0=z0), source_type="sdd")

    @classmethod
    def from_s4p_array(
        cls,
        freqs: np.ndarray,
        s4p: np.ndarray,
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
        z0: float = 100.0,
    ) -> 'sparamModel':
        """
        Build from a single-ended 4-port S-parameter array.

        Input contract:
        - freqs: 1D, finite, strictly increasing frequency axis in Hz
        - s4p: complex array with shape (len(freqs), 4, 4)
        - port_order: zero-based (tx_p, tx_n, rx_p, rx_n)
        - z0: differential-mode reference impedance assigned after Sdd conversion
        """
        freqs = LinkConfig.validate_freqs(freqs)
        port_order = cls.validate_port_order(port_order)
        sdd = _s4p_to_sdd(s4p, port_order, freqs)
        return cls(_network_from_smatrix(freqs, sdd, z0=z0), source_type="s4p", port_order=port_order)

    @classmethod
    def from_network(
        cls,
        network: 'rf.Network',
        mode: str = "auto",
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
        z0: float = 100.0,
    ) -> 'sparamModel':
        """
        Build from an existing scikit-rf Network.

        Input contract:
        - mode="sdd": network.s must have shape (N, 2, 2)
        - mode="single_ended_s4p": network.s must have shape (N, 4, 4)
        - mode="auto": 2-port is treated as Sdd, 4-port as single-ended S4P

        mode:
        - "auto": 2-port is treated as Sdd, 4-port as single-ended S4P
        - "sdd": input network.s is already differential-mode Sdd
        - "single_ended_s4p": input network.s is converted to Sdd
        """

        if mode not in {"auto", "sdd", "single_ended_s4p"}:
            raise ValueError('mode must be "auto", "sdd", or "single_ended_s4p".')

        if mode == "auto":
            if network.s.shape[1:] == (2, 2):
                mode = "sdd"
            elif network.s.shape[1:] == (4, 4):
                mode = "single_ended_s4p"
            else:
                raise ValueError("Only 2-port Sdd and 4-port single-ended networks are supported.")

        if mode == "sdd":
            return cls.from_sdd_array(network.f, network.s, z0=z0)

        return cls.from_s4p_array(network.f, network.s, port_order=port_order, z0=z0)

    @classmethod
    def from_touchstone(
        cls,
        path: str,
        mode: str = "auto",
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
        z0: float = 100.0,
    ) -> 'sparamModel':
        ntwk = rf.Network(path)
        return cls.from_network(ntwk, mode=mode, port_order=port_order, z0=z0)

    # --------------------
    # validation methods
    # --------------------
    @staticmethod
    def validate_sdd(sdd: np.ndarray, freqs: np.ndarray) -> np.ndarray:
        sdd = np.asarray(sdd, dtype=complex)

        if sdd.shape != (len(freqs), 2, 2):
            raise ValueError("sdd must have shape (len(freqs), 2, 2).")

        if not np.all(np.isfinite(sdd)):
            raise ValueError("sdd contains non-finite values.")

        return sdd

    @staticmethod
    def validate_s4p(s4p: np.ndarray, freqs: np.ndarray) -> np.ndarray:
        s4p = np.asarray(s4p, dtype=complex)

        if s4p.shape != (len(freqs), 4, 4):
            raise ValueError("s4p must have shape (len(freqs), 4, 4).")

        if not np.all(np.isfinite(s4p)):
            raise ValueError("s4p contains non-finite values.")

        return s4p

    @staticmethod
    def validate_port_order(port_order: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        if len(port_order) != 4:
            raise ValueError("port_order must contain four zero-based port indices.")

        port_order = tuple(int(p) for p in port_order)
        if sorted(port_order) != [0, 1, 2, 3]:
            raise ValueError("port_order must be a permutation of (0, 1, 2, 3).")

        return port_order

    @staticmethod
    def validate_network(network: 'rf.Network') -> 'rf.Network':

        if not isinstance(network, rf.Network):
            raise TypeError("network must be an skrf.Network.")

        sdd = np.asarray(network.s, dtype=complex)
        if sdd.ndim != 3 or sdd.shape[1:] != (2, 2):
            raise ValueError("sparamModel.network must store Sdd with shape (N, 2, 2).")

        freqs = np.asarray(network.f, dtype=float)
        LinkConfig.validate_freqs(freqs)
        sparamModel.validate_sdd(sdd, freqs)

        return network

    def validate_compatible_sparam(self, other: 'sparamModel') -> None:
        if not isinstance(other, sparamModel):
            raise TypeError("other must be an sparamModel.")

        if self.sdd.shape[1:] != (2, 2) or other.sdd.shape[1:] != (2, 2):
            raise ValueError("Both sparamModel objects must contain 2-port Sdd networks.")

        if self.sdd.shape[0] != other.sdd.shape[0]:
            raise ValueError("Cannot cascade sparamModel objects with different frequency counts.")

        if not np.allclose(self.freqs, other.freqs):
            raise ValueError("Cannot cascade sparamModel objects with different frequency grids.")

        if not np.allclose(self.network.z0, other.network.z0):
            raise ValueError("Cannot cascade sparamModel objects with different z0.")

    def validate_resample_freqs(self, freqs: np.ndarray) -> np.ndarray:
        freqs = LinkConfig.validate_freqs(freqs)

        if freqs[-1] < self.freqs[0]:
            raise ValueError("resample() target grid is entirely below the measured frequency span.")

        return freqs

    def validate_renum_port_order(self, port_order: tuple[int, ...]) -> tuple[int, ...]:
        if len(port_order) != self.sdd.shape[1]:
            raise ValueError("port_order length must match the number of ports.")

        port_order = tuple(int(p) for p in port_order)
        expected = list(range(self.sdd.shape[1]))
        if sorted(port_order) != expected:
            raise ValueError(f"port_order must be a permutation of {tuple(expected)}.")

        return port_order

    # -------------------
    # proxy
    # -------------------
    @property
    def freqs(self) -> np.ndarray:
        return self.network.f

    @property
    def sdd(self) -> np.ndarray:
        return self.network.s

    @property
    def sdd11(self) -> np.ndarray:
        return self.sdd[:, 0, 0]

    @property
    def sdd12(self) -> np.ndarray:
        return self.sdd[:, 0, 1]

    @property
    def sdd21(self) -> np.ndarray:
        return self.sdd[:, 1, 0]

    @property
    def sdd22(self) -> np.ndarray:
        return self.sdd[:, 1, 1]

    # -------------------
    # public methods
    # -------------------
    # ---- immutable / copy-returning operations ----
    def cascade(self, other: 'sparamModel') -> 'sparamModel':
        """
        Return a new model by cascading two Sdd two-port networks.

        The physical order is:
            self -> other

        Both models must already use the same frequency grid and reference
        impedance. Resample / renormalize explicitly before cascade.
        """
        self.validate_compatible_sparam(other)
        cascaded_network = self.network ** other.network
        return type(self).from_network(cascaded_network, mode="sdd", z0=cascaded_network.z0)

    def renormalized(self, z0_new: Union[float, np.ndarray], s_def: str | None = None) -> 'sparamModel':
        """
        Return a copy with S-parameters renormalized to a new reference impedance.

        This changes the S-parameter values, not only the Network.z0 metadata.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        return model.renormalize(z0_new, s_def=s_def)

    def resampled(
        self,
        freqs: np.ndarray,
        basis: str = "s",
        coords: str = "cart",
        kind: str | None = None,
        dc_method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        dc_kind: str = "linear",
        dc_coords: str = "cart",
    ) -> 'sparamModel':
        """
        Return a copy sampled on the requested grid within the measured span.

        If the requested grid starts below the measured low-frequency point,
        the copy first performs DC extrapolation. The returned model only keeps
        requested points up to the measured f_stop; high-frequency S-parameter
        extrapolation is intentionally not performed here.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        return model.resample(
            freqs,
            basis=basis,
            coords=coords,
            kind=kind,
            dc_method=dc_method,
            dc_sparam=dc_sparam,
            dc_kind=dc_kind,
            dc_coords=dc_coords,
        )

    def extrapolated_to_dc(
        self,
        method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        kind: str = "linear",
        coords: str = "cart",
    ) -> 'sparamModel':
        """
        Return a copy with a DC point added when the measurement lacks DC.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        return model.extrapolate_to_dc(method=method, dc_sparam=dc_sparam, kind=kind, coords=coords)

    def renumbered(self, port_order: tuple[int, ...]) -> 'sparamModel':
        """
        Return a copy with ports reordered.

        port_order gives old port indices in the desired new order. For example,
        port_order=(1, 0) swaps a two-port Sdd network.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        return model.renum(port_order)

    # ---- in-place operations ----
    def renormalize(self, z0_new: Union[float, np.ndarray], s_def: str | None = None) -> 'sparamModel':
        """
        Renormalize self.network to a new reference impedance in place.

        This changes the S-parameter values, not only the Network.z0 metadata.
        The method returns self for chaining.
        """
        self.network.renormalize(z0_new, s_def=s_def)
        self.network = self.validate_network(self.network)
        return self

    def resample(
        self,
        freqs: np.ndarray,
        basis: str = "s",
        coords: str = "cart",
        kind: str | None = None,
        dc_method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        dc_kind: str = "linear",
        dc_coords: str = "cart",
    ) -> 'sparamModel':
        """
        Resample self.network in place on the requested grid within the measured span.

        If the requested grid starts below the measured low-frequency point,
        this method first calls extrapolate_to_dc(). After that it only keeps
        requested points up to the measured f_stop. It intentionally does not
        extrapolate S-parameters above the measured bandwidth. The method
        returns self for chaining.
        """
        freqs = self.validate_resample_freqs(freqs)

        if freqs[0] < self.freqs[0]:
            self.extrapolate_to_dc(
                method=dc_method,
                dc_sparam=dc_sparam,
                kind=dc_kind,
                coords=dc_coords,
            )

        f_stop = self.freqs[-1]
        freqs_inband = freqs[freqs <= f_stop]
        if len(freqs_inband) < 2:
            raise ValueError("resample() target grid must contain at least two in-band frequency points.")

        if freqs_inband[0] < self.freqs[0]:
            raise ValueError("resample() target grid starts below the available frequency span after DC handling.")

        self.network = self.network.interpolate(freqs_inband, basis=basis, coords=coords, kind=kind)
        self.network = self.validate_network(self.network)
        return self

    def extrapolate_to_dc(
        self,
        method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        kind: str = "linear",
        coords: str = "cart",
    ) -> 'sparamModel':
        """
        Add a DC point to self.network in place when the measurement lacks DC.

        method="skrf" delegates to skrf.Network.extrapolate_to_dc(). Other
        DC models from the sparam_to_sbr reference can be added here later.
        The method returns self for chaining.
        """
        if np.isclose(self.freqs[0], 0.0):
            return self

        if method != "skrf":
            raise NotImplementedError('Only method="skrf" is implemented for DC extrapolation.')

        self.network = self.network.extrapolate_to_dc(
            dc_sparam=dc_sparam,
            kind=kind,
            coords=coords,
        )
        self.network = self.validate_network(self.network)
        return self

    def voltage_transfer_function(
        self,
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
    ) -> np.ndarray:
        """
        Compute the terminated voltage transfer function H21(f).

        Reference:
        - IEEE 802.3 Annex 93A.1.3, Eq. 93A-18.

        gamma_src and gamma_load are the reflection coefficients seen at port 1
        and port 2. With matched terminations, both are zero and H21(f)=Sdd21(f).
        """
        gamma_src = np.asarray(gamma_src, dtype=complex)
        gamma_load = np.asarray(gamma_load, dtype=complex)

        delta_s = self.sdd11 * self.sdd22 - self.sdd12 * self.sdd21
        denom = (
            1
            - self.sdd11 * gamma_src
            - self.sdd22 * gamma_load
            + gamma_src * gamma_load * delta_s
        )
        if np.any(np.isclose(denom, 0.0)):
            raise ZeroDivisionError("H21 denominator is close to zero.")

        return self.sdd21 * (1 - gamma_src) * (1 + gamma_load) / denom

    def renum(self, port_order: tuple[int, ...]) -> 'sparamModel':
        """
        Reorder self.network ports in place.

        port_order gives old port indices in the desired new order. For example,
        port_order=(1, 0) swaps a two-port Sdd network.

        Internally this maps to scikit-rf Network.renumber(from_ports, to_ports):
            from_ports = port_order
            to_ports = range(n_ports)

        The method returns self for chaining.
        """
        port_order = self.validate_renum_port_order(port_order)
        self.network.renumber(
            from_ports=list(port_order),
            to_ports=list(range(len(port_order))),
        )
        self.network = self.validate_network(self.network)
        return self
    
    # ---- derived scalar conversion ----
    def to_LinkSegment(
        self,
        cfg: 'LinkConfig',
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
        basis: str = "s",
        coords: str = "cart",
        kind: str | None = None,
        dc_method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        dc_kind: str = "linear",
        dc_coords: str = "cart",
    ) -> 'LinkSegment':
        """
        Build a scalar LinkSegment from the terminated voltage transfer H21(f).

        This method does not mutate self. It uses a temporary resampled copy in
        S-matrix domain, then converts that copy to H21(f).

        Flow:
        1. resample the Sdd network onto cfg.freqs inside the measured bandwidth
        2. compute H21(f) with impedance mismatch using Eq. 93A-18
        3. let LinkSegment.from_tf() extend the scalar transfer function to
           cfg.f_nyq using the project's TF extension rule
        """
        resampled = self.resampled(
            cfg.freqs,
            basis=basis,
            coords=coords,
            kind=kind,
            dc_method=dc_method,
            dc_sparam=dc_sparam,
            dc_kind=dc_kind,
            dc_coords=dc_coords,
        )
        H21 = resampled.voltage_transfer_function(gamma_src=gamma_src, gamma_load=gamma_load)
        return LinkSegment.from_tf(resampled.freqs, H21, cfg)

class LinkSegment:
    """
    Scalar channel response container on a LinkConfig grid.

    Class boundary
    --------------
    LinkSegment owns scalar transfer-function / impulse-response /
    step-response / single-bit-response representations of one LTI segment.
    It also owns the conversion rules between those scalar representations,
    including continuous-domain FFT/IFFT scaling convention.

    It should not own two-port S-parameter storage, S4P-to-Sdd conversion,
    mixed-mode conversion, or IEEE COM package primitive construction. Those
    belong in sparamModel or com_model.py before a scalar response is selected.
    """

    def __init__(self, cfg: 'LinkConfig'):
        self.cfg = cfg

        # transfer function: positive half side, with extension to cfg.f_nyq
        self._tf = None

        # time-domain response
        #   t-axis starts from 0, with step = dt = bt / per_ui
        #   no fftshift/circular shift, the delay element should be determined before using
        self._ir = None         # impulse response
        self._sr = None         # step response
        self._sbr = None        # single-bit response

    # ----- constructors -----
    @classmethod
    def from_tf(cls, f_meas: np.ndarray, H_meas: np.ndarray, cfg: 'LinkConfig') -> 'LinkSegment':
        if not(isFreqsEqual(f_meas, cfg.freqs)):
            H_meas = resample_tf(H_meas, f_meas, cfg.freqs)

        seg = cls(cfg)
        seg._tf = H_meas
        return seg

    @classmethod
    def from_sr(cls) -> 'LinkSegment':
        pass

    # ----- proxy & lazy evaluation -----
    @property
    def tf(self) -> np.ndarray:
        if (self._tf is None):
            assert self._sr is not None
            self._tf = self.sr2tf(self._sr)
        return self._tf

    @property
    def sr(self) -> np.ndarray:
        if (self._sr is None):
            assert self._tf is not None
            self._sr = self.tf2sr(self._tf)
        return self._sr

    @property
    def ir(self) -> np.ndarray:
        if (self._ir is None):
            if (self._tf is not None):
                self._ir = self.tf2ir(self._tf)
            elif (self._sr is not None):
                self._ir = self.sr2ir(self._sr)
            else:
                raise Exception("Error @ calling LinkSegment.ir ...")
        return self._ir

    @property
    def sbr(self) -> np.ndarray:
        if (self._sbr is None):
            self._sbr = self.sr2sbr(self.sr)
        return self._sbr

    # ============================
    # methods
    # ============================
    def cascade_tf(self, other: 'LinkSegment') -> 'LinkSegment':
        """
        Cascade two scalar transfer-function LinkSegment objects in frequency domain.

        This is an LTI transfer-function cascade:
            H_total(f) = H_self(f) * H_other(f)

        It is not a two-port S-parameter cascade. S-parameter package/channel
        cascade must be handled before constructing a scalar LinkSegment tf.
        """
        self.validate_compatible_segment(other)

        seg = LinkSegment(self.cfg)
        seg._tf = self.validate_tf(self.tf * other.tf)
        return seg

    def cascade_ir(self, other: 'LinkSegment') -> 'LinkSegment':
        pass

    def find_main_delay(self, energy_window_ui: float = 1.0) -> dict[str, float | int]:
        """
        Estimate the main delay from the impulse-response peak.

        The primary delay is reported from the largest |ir[n]| sample. An optional
        local energy centroid around that peak is also reported as a smoother delay
        estimate. This method only reports timing; it does not shift the response.

        Output parameters
        ---------------------
            peak_index:           =argmax(abs(ir))
            energy_window_ui:     以peak_idx為中心的energy window的UI寬度
            centroid_index:       energy window 中的重心
        """
        ir = self.ir
        mag = np.abs(ir)
        energy = mag**2
        total_energy = float(np.sum(energy))

        if total_energy <= 0.0:
            raise ValueError("Cannot find main delay because impulse-response energy is zero.")

        peak_index = int(np.argmax(mag))
        peak_time = float(self.cfg.times[peak_index])
        peak_time_ui = float(self.cfg.times_ui[peak_index])
        peak_amplitude = float(mag[peak_index])

        half_window = max(1, int(round(energy_window_ui * self.cfg.per_ui / 2)))
        lo = max(0, peak_index - half_window)
        hi = min(len(ir), peak_index + half_window + 1)

        local_energy = energy[lo:hi]
        local_energy_sum = float(np.sum(local_energy))

        if local_energy_sum > 0.0:
            local_indices = np.arange(lo, hi)
            centroid_index = float(np.sum(local_indices * local_energy) / local_energy_sum)
            centroid_time = centroid_index * self.cfg.dt
            centroid_time_ui = centroid_time / self.cfg.bt
        else:
            centroid_index = float(peak_index)
            centroid_time = peak_time
            centroid_time_ui = peak_time_ui

        return {
            "peak_index": peak_index,
            "peak_time": peak_time,
            "peak_time_ui": peak_time_ui,
            "peak_amplitude": peak_amplitude,
            "centroid_index": centroid_index,
            "centroid_time": float(centroid_time),
            "centroid_time_ui": float(centroid_time_ui),
            "energy_window_start_index": int(lo),
            "energy_window_stop_index": int(hi),
            "energy_window_ui": float(energy_window_ui),
            "energy_ratio_in_window": float(local_energy_sum / total_energy),
        }

    def estimate_phase_delay(
        self,
        f_min: float | None = None,
        f_max: float | None = None,
        mag_floor_ratio: float = 1e-4,
    ) -> dict[str, Union[float, int]]:
        """
        Estimate bulk delay from the unwrapped TF phase slope.

        For a pure delay H(f)=A(f)exp(-j2*pi*f*tau), the unwrapped phase slope is:
            dphi/df = -2*pi*tau
        This method fits phase versus frequency over a usable band and reports:
            tau = -slope / (2*pi)

        The result is a bulk/group-delay estimate used to judge whether cfg.T_max
        is long enough to avoid DFT wrap-around. It does not modify the response.
        """
        tf = self.validate_tf(self.tf)
        freqs = self.cfg.freqs
        mag = np.abs(tf)
        phase = np.unwrap(np.angle(tf))

        if f_min is None:
            f_min = self.cfg.df
        if f_max is None:
            f_max = min(self.cfg.f_nyq, self.cfg.fb)

        mag_threshold = float(np.max(mag) * mag_floor_ratio)
        mask = (
            (freqs >= f_min) &
            (freqs <= f_max) &
            (mag >= mag_threshold) &
            np.isfinite(phase)
        )

        if np.count_nonzero(mask) < 2:
            raise ValueError("Not enough valid frequency points to estimate phase delay.")

        fit = np.polyfit(freqs[mask], phase[mask], 1)
        slope = float(fit[0])
        intercept = float(fit[1])
        tau = -slope / (2 * np.pi)

        phase_fit = slope * freqs[mask] + intercept
        residual = phase[mask] - phase_fit
        rms_phase_error = float(np.sqrt(np.mean(residual**2)))

        return {
            "delay": float(tau),
            "delay_ui": float(tau / self.cfg.bt),
            "fit_f_min": float(f_min),
            "fit_f_max": float(f_max),
            "fit_points": int(np.count_nonzero(mask)),
            "phase_slope_rad_per_hz": slope,
            "phase_intercept_rad": intercept,
            "rms_phase_error_rad": rms_phase_error,
            "mag_floor_ratio": float(mag_floor_ratio),
        }

    def debug_time_axis(self, head_ui: float = 1.0, tail_ui: float = 1.0) -> dict[str, Union[bool, float, int]]:
        """
        Report whether the configured time/frequency axes are internally consistent.

        This checks the cfg grid itself, estimates bulk delay from TF phase, and
        reports head/tail impulse-response energy ratios as warning indicators
        for wrap-around or insufficient time-window length. It does not
        automatically circular-shift the response.
        """
        ir = self.ir
        energy = np.abs(ir)**2
        total_energy = float(np.sum(energy))

        head_len = max(1, int(round(head_ui * self.cfg.per_ui)))
        tail_len = max(1, int(round(tail_ui * self.cfg.per_ui)))
        head_len = min(head_len, len(ir))
        tail_len = min(tail_len, len(ir))

        if total_energy > 0.0:
            head_energy_ratio = float(np.sum(energy[:head_len]) / total_energy)
            tail_energy_ratio = float(np.sum(energy[-tail_len:]) / total_energy)
        else:
            head_energy_ratio = 0.0
            tail_energy_ratio = 0.0

        main_delay = self.find_main_delay()
        phase_delay = self.estimate_phase_delay()

        expected_fs = 1.0 / self.cfg.dt
        expected_df = self.cfg.Fs / self.cfg.Nfft
        expected_t_max = self.cfg.Nfft * self.cfg.dt
        expected_l_ui = expected_t_max / self.cfg.bt
        remaining_time_after_phase_delay = self.cfg.T_max - phase_delay["delay"]

        return {
            "Nfft": int(self.cfg.Nfft),
            "Fs": float(self.cfg.Fs),
            "f_nyq": float(self.cfg.f_nyq),
            "df": float(self.cfg.df),
            "dt": float(self.cfg.dt),
            "T_max": float(self.cfg.T_max),
            "L_ui": float(expected_l_ui),
            "freq_axis_reaches_nyquist": bool(np.allclose(self.cfg.freqs[-1], self.cfg.f_nyq)),
            "fs_matches_dt": bool(np.allclose(self.cfg.Fs, expected_fs)),
            "df_matches_fft_grid": bool(np.allclose(self.cfg.df, expected_df)),
            "tmax_matches_fft_grid": bool(np.allclose(self.cfg.T_max, expected_t_max)),
            "head_ui": float(head_ui),
            "tail_ui": float(tail_ui),
            "head_energy_ratio": head_energy_ratio,
            "tail_energy_ratio": tail_energy_ratio,
            "phase_delay": float(phase_delay["delay"]),
            "phase_delay_ui": float(phase_delay["delay_ui"]),
            "phase_delay_fit_points": int(phase_delay["fit_points"]),
            "phase_delay_fit_f_min": float(phase_delay["fit_f_min"]),
            "phase_delay_fit_f_max": float(phase_delay["fit_f_max"]),
            "phase_delay_rms_phase_error_rad": float(phase_delay["rms_phase_error_rad"]),
            "remaining_time_after_phase_delay": float(remaining_time_after_phase_delay),
            "remaining_ui_after_phase_delay": float(remaining_time_after_phase_delay / self.cfg.bt),
            "phase_delay_within_time_window": bool(0.0 <= phase_delay["delay"] < self.cfg.T_max),
            "main_delay_peak_index": int(main_delay["peak_index"]),
            "main_delay_peak_time": float(main_delay["peak_time"]),
            "main_delay_peak_time_ui": float(main_delay["peak_time_ui"]),
            "main_delay_centroid_time": float(main_delay["centroid_time"]),
            "main_delay_centroid_time_ui": float(main_delay["centroid_time_ui"]),
        }

    def debug_round_trip(
        self,
        pair: str,
        x: np.ndarray | None = None,
        rtol: float = 1e-10,
        atol: float = 1e-12,
        raise_on_fail: bool = True,
    ) -> dict[str, Union[str, bool, float]]:
        """
        Check whether a conversion pair can round-trip within numerical tolerance.

        This debug check compares only the round-trip result:
            source -> target -> recovered_source
        It does not compare against an external expected target response. If x is
        provided, x replaces the instance-owned source response for this check.

        The pass/fail logic uses a global max-error criterion:
            abs_err = max(abs(recovered_source - source))
            source_scale = max(max(abs(source)), atol)
            rel_err = abs_err / source_scale
            tolerance = max(atol, rtol * source_scale)
            passed = abs_err <= tolerance
        This is intentional because continuous-scaled impulse responses can have
        large absolute values even when the relative numerical error is tiny.

        Supported pairs:
        - "tf2ir" and "ir2tf"
          Reversible when tf is on cfg.freqs, has real DC/Nyquist bins, and the
          inverse path uses the same cfg.Nfft/cfg.Fs scaling convention.
        - "tf2sr" and "sr2tf"
          Reversible under the same tf constraints plus the step-response
          initial condition sr[n<0] = 0 used by sr2ir().
        - "ir2sr" and "sr2ir"
          Reversible for finite cfg.times-length arrays when sr2ir() uses the
          same left boundary condition sr[-1 before t=0] = 0.
        - "sr2sbr" and "sbr2sr"
          Reversible for finite cfg.times-length arrays when both directions use
          D = cfg.per_ui samples as exactly one UI and assume sr[n<0] = 0.

        If x is None, the source representation is taken from this instance.
        """
        pair_map = {
            "tf2ir": ("tf", "ir", self.validate_tf, self.tf2ir, self.ir2tf),
            "ir2tf": ("ir", "tf", lambda v: self.validate_time_response(v, "ir"), self.ir2tf, self.tf2ir),
            "tf2sr": ("tf", "sr", self.validate_tf, self.tf2sr, self.sr2tf),
            "sr2tf": ("sr", "tf", lambda v: self.validate_time_response(v, "sr"), self.sr2tf, self.tf2sr),
            "ir2sr": ("ir", "sr", lambda v: self.validate_time_response(v, "ir"), self.ir2sr, self.sr2ir),
            "sr2ir": ("sr", "ir", lambda v: self.validate_time_response(v, "sr"), self.sr2ir, self.ir2sr),
            "sr2sbr": ("sr", "sbr", lambda v: self.validate_time_response(v, "sr"), self.sr2sbr, self.sbr2sr),
            "sbr2sr": ("sbr", "sr", lambda v: self.validate_time_response(v, "sbr"), self.sbr2sr, self.sr2sbr),
        }

        if pair not in pair_map:
            supported = ", ".join(pair_map)
            raise ValueError(f"Unsupported round-trip pair: {pair}. Supported pairs: {supported}")

        source_name, target_name, validate_source, forward, backward = pair_map[pair]

        if x is None:
            x = getattr(self, source_name)

        source = validate_source(x)
        target = forward(source)
        recovered = backward(target)

        abs_err = float(np.max(np.abs(recovered - source)))
        source_scale = max(float(np.max(np.abs(source))), atol)
        rel_err = abs_err / source_scale
        tolerance = max(atol, rtol * source_scale)
        passed = bool(abs_err <= tolerance)

        if raise_on_fail and not passed:
            raise AssertionError(
                f"{pair} round-trip failed: "
                f"{source_name}->{target_name}->{source_name}, "
                f"abs_err={abs_err:.3e}, rel_err={rel_err:.3e}, tolerance={tolerance:.3e}"
            )

        return {
            "pair": pair,
            "source": source_name,
            "target": target_name,
            "passed": passed,
            "roundtrip_abs_err": abs_err,
            "roundtrip_rel_err": rel_err,
            "roundtrip_tolerance": tolerance,
        }

    # ---------------------------
    # validation methods
    # ---------------------------
    def validate_tf(self, tf: np.ndarray) -> np.ndarray:
        tf = np.asarray(tf, dtype=complex)

        if tf.shape != self.cfg.freqs.shape:
            raise ValueError("tf must have the same shape as cfg.freqs.")

        if not np.all(np.isfinite(tf)):
            raise ValueError("tf contains non-finite values.")

        if not np.allclose(tf[0].imag, 0.0):
            raise ValueError("tf[0] must be real for a real-valued impulse response.")

        if not np.allclose(tf[-1].imag, 0.0):
            raise ValueError("tf[-1] must be real because cfg.Nfft is even and this is the Nyquist bin.")

        return tf

    def validate_time_response(self, x: np.ndarray, name: str) -> np.ndarray:
        x = np.asarray(x, dtype=float)

        if x.shape != self.cfg.times.shape:
            raise ValueError(f"{name} must have the same shape as cfg.times.")

        if not np.all(np.isfinite(x)):
            raise ValueError(f"{name} contains non-finite values.")

        return x

    def validate_compatible_segment(self, other: 'LinkSegment') -> None:
        if not isinstance(other, LinkSegment):
            raise TypeError("other must be a LinkSegment.")

        if self.cfg.Nfft != other.cfg.Nfft:
            raise ValueError("Cannot cascade LinkSegment objects with different Nfft.")

        if not np.allclose(self.cfg.freqs, other.cfg.freqs):
            raise ValueError("Cannot cascade LinkSegment objects with different frequency grids.")

        if not np.allclose(self.cfg.times, other.cfg.times):
            raise ValueError("Cannot cascade LinkSegment objects with different time grids.")

    # ---------------------------
    # response transformation
    # ---------------------------
    # tf -> ir -> sr
    def tf2ir(self, tf: np.ndarray) -> np.ndarray:
        """
        Convert one-sided continuous-domain transfer function samples to impulse response.

        NumPy irfft returns the DFT-normalized sequence. Multiplying by cfg.Fs converts
        the inverse sum into a continuous inverse Fourier integral approximation.

        Round-trip boundary condition with ir2tf():
        - tf must be sampled on cfg.freqs.
        - tf[0] and tf[-1] must be real so irfft represents a real time response.
        - ir2tf() must divide by the same cfg.Fs used here.
        """
        tf = self.validate_tf(tf)
        return np.fft.irfft(tf, n=self.cfg.Nfft) * self.cfg.Fs

    def ir2sr(self, ir: np.ndarray) -> np.ndarray:
        """
        Convert impulse response to step response using continuous-time integration.

        Round-trip boundary condition with sr2ir():
        - ir and sr are cfg.times-length arrays.
        - sr is defined with zero prehistory: sr[n<0] = 0.
        - The inverse uses the same cfg.dt.
        """
        ir = self.validate_time_response(ir, "ir")
        return np.cumsum(ir) * self.cfg.dt

    def tf2sr(self, tf: np.ndarray) -> np.ndarray:
        """
        Convert transfer function to step response through the continuous-scaled impulse response.

        Round-trip boundary condition with sr2tf():
        - Requires the tf2ir/ir2tf and ir2sr/sr2ir boundary conditions.
        - In particular, sr2tf() treats the sample before t=0 as zero.
        """
        return self.ir2sr(self.tf2ir(tf))

    # sr -> ir -> tf
    def sr2ir(self, sr: np.ndarray) -> np.ndarray:
        """
        Convert step response to impulse response by finite difference.

        Boundary condition:
        - Prepends sr[-1 before t=0] = 0 via np.r_[0, sr].
        - This makes ir2sr(sr2ir(sr)) reversible only for step responses that use
          the same zero-prehistory convention.
        """
        sr = self.validate_time_response(sr, "sr")
        return np.diff(np.r_[0, sr]) / self.cfg.dt

    def ir2tf(self, ir: np.ndarray) -> np.ndarray:
        """
        Convert continuous-scaled impulse response samples back to one-sided TF samples.

        Round-trip boundary condition with tf2ir():
        - ir must be cfg.times-length and continuous-scaled.
        - The forward FFT divides by cfg.Fs to undo tf2ir()'s continuous scaling.
        - The returned DC/Nyquist bins are forced real for rfft/irfft consistency.
        """
        ir = self.validate_time_response(ir, "ir")
        tf = np.fft.rfft(ir, n=self.cfg.Nfft) / self.cfg.Fs
        tf[0] = tf[0].real + 0j
        tf[-1] = tf[-1].real + 0j
        return tf
    
    def sr2tf(self, sr: np.ndarray) -> np.ndarray:
        """
        Convert step response to transfer function through sr2ir() and ir2tf().

        Boundary condition:
        - Uses sr2ir()'s zero-prehistory convention at t=0.
        """
        return self.ir2tf(self.sr2ir(sr))

    # sr <-> sbr
    def sr2sbr(self, sr: np.ndarray) -> np.ndarray:
        """
        Convert step response to single-bit response.

        Definition:
            sbr[n] = sr[n] - sr[n-D]
            D = cfg.per_ui samples = one UI
            sr[n-D] = 0 for n < D

        Time-axis convention:
        - sbr has the same shape as cfg.times.
        - sbr[n] is aligned to cfg.times[n]; no center crop or cursor alignment is
          applied here. Any main-cursor alignment should be a separate operation.

        Round-trip boundary condition with sbr2sr():
        - Both directions must use the same D = cfg.per_ui.
        - The step response prehistory before t=0 is assumed zero.
        """
        sr = self.validate_time_response(sr, "sr")
        delay = self.cfg.per_ui     # per_ui points in cfg.times = cfg.bt
        sbr = sr.copy()
        sbr[delay:] -= sr[:-delay]

        return sbr

    def sbr2sr(self, sbr: np.ndarray) -> np.ndarray:
        """ 
        Convert single-bit response back to step response.

        Inverse recurrence:
            sr[n] = sbr[n]              for n < D
            sr[n] = sbr[n] + sr[n-D]    for n >= D
            D = cfg.per_ui samples = one UI

        Round-trip boundary condition with sr2sbr():
        - sbr must be cfg.times-length.
        - Uses the same D = cfg.per_ui as sr2sbr().
        - Assumes sr[n<0] = 0; finite-window truncation is part of the convention.
        """
        sbr = self.validate_time_response(sbr, "sbr")
        D = self.cfg.per_ui
        sr = np.zeros_like(sbr)
        for n in range(len(sbr)):
            sr[n] = sbr[n]
            if n >= D:
                sr[n] += sr[n - D]

        return sr

