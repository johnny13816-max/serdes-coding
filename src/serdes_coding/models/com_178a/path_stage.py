"""Annex 178A path-construction stage and version-owned COM primitives."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
from scipy.signal import lfilter

from ...utilities.link import LinkConfig, LinkSegment
from ...utilities.sparam import SparamModel
from ..com_dataclass_text import COMDataclassText, TextField, TextSection
from .config import (
    COMChannelConfig,
    COMConfig,
    COMDevicePackageConfig,
    COMDeviceTermConfig,
    COMFilterConfig,
    COMPartialHostConfig,
    COMPkgConfig,
)
from .errors import COMLengthMismatchError
from .status import COMPath, COMSharedPath

class IEEECOMSparam(SparamModel):
    """
    IEEE COM-specific S-parameter model builder.

    Class boundary
    --------------
    IEEECOMSparam owns S-parameter networks generated from IEEE COM equations.

    Versioned responsibilities:
    - COM primitive Sdd models used by 178A:
      shunt capacitance, series inductance, single package transmission line
    - COM Sdd cascade used by 178A
    - 178A package/model composition:
      device termination LC ladder, N-stage package transmission line, and
      partial host channel

    Generic S-parameter ingestion, storage, and scikit-rf operations remain in
    SparamModel. This class only adds spec-defined COM construction behavior.
    The established ``_93A`` method names remain compatibility wrappers only;
    178A stage code calls the canonical methods defined by this class.
    """

    @classmethod
    def shunt_capacitance(cls, freqs: np.ndarray, capacitance: float, R0: float=50.0) -> 'IEEECOMSparam':
        """
        Build the COM shunt capacitance Sdd two-port on freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.2, Eq. 93A-8.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        capacitance:
            Shunt capacitance in F.
        R0:
            Single-ended reference resistance used by Eq. 93A-8. The internal
            differential-mode Sdd Network uses z0 = 2 * R0.
        """
        C = float(capacitance)
        R0 = float(R0)
        freqs = LinkConfig.validate_freqs(freqs)
        if C < 0.0:
            raise ValueError('capacitance must be non-negative.')
        y = 1j * 2 * np.pi * freqs * C
        denom = 2 + y * R0
        s11 = -(y * R0) / denom
        s21 = 2 / denom
        sdd = np.stack([np.stack([s11, s21], axis=-1), np.stack([s21, s11], axis=-1)], axis=-2)
        return cls.from_sdd_array(freqs, sdd, z0=2 * R0)

    @classmethod
    def series_inductance(cls, freqs: np.ndarray, inductance: float, R0: float=50.0) -> 'IEEECOMSparam':
        """
        Build the COM series inductance Sdd two-port on freqs.

        Reference:
        - IEEE 802.3ck Annex 93A.1.2.2a, Eq. 93A-9a.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        inductance:
            Series inductance in H.
        R0:
            Single-ended reference resistance used by Eq. 93A-9a. The internal
            differential-mode Sdd Network uses z0 = 2 * R0.
        """
        L = float(inductance)
        R0 = float(R0)
        freqs = LinkConfig.validate_freqs(freqs)
        if L < 0.0:
            raise ValueError('inductance must be non-negative.')
        y = 1j * 2 * np.pi * freqs * L
        denom = 2 + y / R0
        s11 = y / R0 / denom
        s21 = 2 / denom
        sdd = np.stack([np.stack([s11, s21], axis=-1), np.stack([s21, s11], axis=-1)], axis=-2)
        return cls.from_sdd_array(freqs, sdd, z0=2 * R0)

    @classmethod
    def package_transmission_line(cls, freqs: np.ndarray, R0: float, zp: float, *, gamma0: float=0.0, a1: float=float(0.001734), a2: float=float(0.0001455), tau: float=float(0.006141), Zc: float=78.2) -> 'IEEECOMSparam':
        """
        Build the COM package transmission-line Sdd two-port on freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.3, Eq. 93A-9 through Eq. 93A-14.
        - IEEE 802.3ck Annex 93A.1.2.3 clarifies that formula frequency f is
          in GHz.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance.
        zp:
            Package line length in millimeters.
        gamma0, a1, a2, tau:
            COM propagation-coefficient model parameters. The formula uses
            f in GHz internally after converting from freqs in Hz; gamma0,
            a1, a2, and tau keep the 93A units associated with Table 93A-3.
        Zc:
            Package differential characteristic impedance in ohm.
        """
        f_hz = LinkConfig.validate_freqs(freqs)
        if np.any(f_hz < 0):
            raise ValueError('The package transmission-line model does not include f < 0.')
        R0 = float(R0)
        zp = float(zp)
        Zc = float(Zc)
        if R0 <= 0.0:
            raise ValueError('R0 must be positive.')
        if zp < 0.0:
            raise ValueError('zp must be non-negative.')
        if Zc <= 0.0:
            raise ValueError('Zc must be positive.')
        f = f_hz / 1000000000.0
        gamma = np.full_like(f, complex(gamma0), dtype=complex)
        gamma1 = a1 * (1 + 1j)
        positive = f > 0.0
        gamma2 = a2 * (1 - 1j * (2 / np.pi) * np.log(f[positive])) + 1j * 2 * np.pi * tau
        gamma[positive] = gamma0 + gamma1 * np.sqrt(f[positive]) + gamma2 * f[positive]
        rho = (Zc - 2 * R0) / (Zc + 2 * R0)
        y = np.exp(-(gamma * 2 * zp))
        y1 = np.exp(-(gamma * zp))
        denom = 1 - rho ** 2 * y
        s11 = rho * (1 - y) / denom
        s21 = (1 - rho ** 2) * y1 / denom
        sdd = np.stack([np.stack([s11, s21], axis=-1), np.stack([s21, s11], axis=-1)], axis=-2)
        return cls.from_sdd_array(f_hz, sdd, z0=2 * R0)

    @staticmethod
    def _cascade_sdd(sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
        """
        Cascade two Sdd arrays using IEEE COM equations.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.1, Eq. 93A-4 through Eq. 93A-7.

        Parameters
        ----------
        sx:
            First Sdd two-port in physical order, shape (N, 2, 2).
        sy:
            Second Sdd two-port in physical order, shape (N, 2, 2).
        """
        sx = np.asarray(sx, dtype=complex)
        sy = np.asarray(sy, dtype=complex)
        if sx.shape != sy.shape or sx.ndim != 3 or sx.shape[1:] != (2, 2):
            raise ValueError('sx and sy must both have shape (N, 2, 2).')
        x11, x12 = (sx[:, 0, 0], sx[:, 0, 1])
        x21, x22 = (sx[:, 1, 0], sx[:, 1, 1])
        y11, y12 = (sy[:, 0, 0], sy[:, 0, 1])
        y21, y22 = (sy[:, 1, 0], sy[:, 1, 1])
        denom = 1 - x22 * y11
        if np.any(np.isclose(denom, 0.0)):
            raise ZeroDivisionError('S-parameter cascade denominator is close to zero.')
        z11 = x11 + x12 * y11 * x21 / denom
        z12 = x12 * y12 / denom
        z21 = y21 * x21 / denom
        z22 = y22 + y21 * x22 * y12 / denom
        return np.stack([np.stack([z11, z12], axis=-1), np.stack([z21, z22], axis=-1)], axis=-2)

    def cascade_com(self, other: SparamModel) -> 'IEEECOMSparam':
        """
        Cascade two Sdd two-port networks using IEEE COM equations.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.1, Eq. 93A-4 through Eq. 93A-7.

        Parameters
        ----------
        other:
            Sdd two-port physically following self.

        Frequency-grid rule
        -------------------
        If the two models do not already share an identical frequency grid,
        both are resampled onto the overlapping subset of self.freqs. This keeps
        cascade in the measured/common S-parameter band and avoids high-frequency
        S-parameter extrapolation.
        """
        if not isinstance(other, SparamModel):
            raise TypeError('other must be an SparamModel.')
        if self.sdd.shape[1:] != (2, 2) or other.sdd.shape[1:] != (2, 2):
            raise ValueError('Both models must contain 2-port Sdd networks.')
        f_start = max(self.freqs[0], other.freqs[0])
        f_stop = min(self.freqs[-1], other.freqs[-1])
        common_freqs = self.freqs[(self.freqs >= f_start) & (self.freqs <= f_stop)]
        if len(common_freqs) < 2:
            raise ValueError('No overlapping frequency grid for COM S-parameter cascade.')
        left = self.resampled(common_freqs)
        right = other.resampled(common_freqs)
        left.validate_compatible_sparam(right)
        cascaded_sdd = self._cascade_sdd(left.sdd, right.sdd)
        return type(self).from_sdd_array(common_freqs, cascaded_sdd, z0=left.network.z0)

    @classmethod
    def device_termination(cls, freqs: np.ndarray, R0: float, dt_cfg: COMDeviceTermConfig) -> 'IEEECOMSparam':
        """
        Build the 178A device termination S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-7.

        Model convention
        ----------------
        The model is represented as an N-stage LC ladder plus the package bump
        capacitance. The L/C vectors describe per-stage device termination
        elements. The ladder is cascaded in reverse order so the returned
        two-port follows the physical order expected by the package/channel
        cascade.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance in ohm.
        dt_cfg:
            Device termination configuration. It owns the stage-aligned L/C
            vectors and the bump/interface capacitance.

        Returns
        -------
        IEEECOMSparam
            Cascaded N-stage LC ladder as a differential 2-port Sdd model.
        """
        if not isinstance(dt_cfg, COMDeviceTermConfig):
            raise TypeError('dt_cfg must be a COMDeviceTermConfig.')
        S_d = cls.shunt_capacitance(freqs, dt_cfg.C_b, R0)
        for l, c in zip(dt_cfg.L_s_seq[::-1], dt_cfg.C_d_seq[::-1]):
            S_C_temp = cls.shunt_capacitance(freqs, c, R0)
            S_L_temp = cls.series_inductance(freqs, l, R0)
            S_temp = S_C_temp.cascade_com(S_L_temp)
            S_d = S_temp.cascade_com(S_d)
        return S_d

    @classmethod
    def device_package(cls, freqs: np.ndarray, R0: float, dp_cfg: COMDevicePackageConfig) -> 'IEEECOMSparam':
        """
        Build the 178A device package S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-9.

        Model convention
        ----------------
        The model is represented as a package-side shunt capacitance followed
        by N transmission-line stages. COMDevicePackageConfig normalizes the
        propagation parameters to one value per transmission-line stage.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance in ohm.
        dp_cfg:
            Device package configuration. It owns package capacitance and all
            stage-aligned transmission-line parameters.

        Returns
        -------
        IEEECOMSparam
            Cascaded N-stage package TL as a differential 2-port Sdd model.
        """
        if not isinstance(dp_cfg, COMDevicePackageConfig):
            raise TypeError('dp_cfg must be a COMDevicePackageConfig.')
        S_p = cls.shunt_capacitance(freqs, dp_cfg.C_p, R0)
        for z_p, Z_c, gamma_0, a1, a2, tau in zip(dp_cfg.z_p_seq[::-1], dp_cfg.Z_c_seq[::-1], dp_cfg.gamma_0[::-1], dp_cfg.a1[::-1], dp_cfg.a2[::-1], dp_cfg.tau[::-1]):
            S_temp = cls.package_transmission_line(freqs, R0, z_p, Zc=Z_c, gamma0=gamma_0, a1=a1, a2=a2, tau=tau)
            S_p = S_temp.cascade_com(S_p)
        return S_p

    @classmethod
    def partial_host_channel(cls, freqs: np.ndarray, R0: float, ph_cfg: COMPartialHostConfig) -> 'IEEECOMSparam':
        """
        Build the 178A partial host channel S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-10.

        Model convention
        ----------------
        The partial host channel is represented as:
            C0 shunt capacitance -> host TL segment -> C1 shunt capacitance.

        This helper builds the synthetic partial-host block itself; it does not
        consume an external measured host S-parameter model.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance in ohm.
        ph_cfg:
            Partial host channel configuration. When ``enable`` is False,
            return the identity two-port without a partial host block.

        Returns
        -------
        IEEECOMSparam
            Synthetic partial host channel as a differential 2-port Sdd model.
        """
        if not isinstance(ph_cfg, COMPartialHostConfig):
            raise TypeError('ph_cfg must be a COMPartialHostConfig.')
        if not ph_cfg.enable:
            return cls.shunt_capacitance(freqs, 0.0, R0)
        S_0 = cls.shunt_capacitance(freqs, ph_cfg.C_0, R0)
        S_h = cls.package_transmission_line(freqs, R0, ph_cfg.z_h, Zc=ph_cfg.Z_h, gamma0=ph_cfg.gamma_0, a1=ph_cfg.a1, a2=ph_cfg.a2, tau=ph_cfg.tau)
        S_1 = cls.shunt_capacitance(freqs, ph_cfg.C_1, R0)
        return S_0.cascade_com(S_h).cascade_com(S_1)

    @classmethod
    def shunt_capacitance_93A(cls, freqs: np.ndarray, capacitance: float, R0: float=50.0) -> 'IEEECOMSparam':
        return cls.shunt_capacitance(freqs, capacitance, R0)

    @classmethod
    def series_inductance_93A(cls, freqs: np.ndarray, inductance: float, R0: float=50.0) -> 'IEEECOMSparam':
        return cls.series_inductance(freqs, inductance, R0)

    @classmethod
    def pkg_trans_line_93A(cls, freqs: np.ndarray, R0: float, zp: float, *, gamma0: float=float(0.0), a1: float=float(0.001734), a2: float=float(0.0001455), tau: float=float(0.006141), Zc: float=78.2) -> 'IEEECOMSparam':
        return cls.package_transmission_line(freqs, R0, zp, gamma0=gamma0, a1=a1, a2=a2, tau=tau, Zc=Zc)

    @staticmethod
    def _cascade_sdd_93A(sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
        return IEEECOMSparam._cascade_sdd(sx, sy)

    def cascade_com_93A(self, other: SparamModel) -> 'IEEECOMSparam':
        return self.cascade_com(other)

@dataclass(frozen=True, repr=False)
class COMBilinearCTLE(COMDataclassText):
    """Two-section digital CTLE used by the 178A reference pulse branch."""
    b1: np.ndarray
    a1: np.ndarray
    b2: np.ndarray
    a2: np.ndarray
    Fs: float

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (TextSection('Digital realization', (self._field('Fs', 'sample rate', stored_unit='Hz', display_unit='GHz', scale=1e-09), self._field('b1', 'section 1 numerator', stored_unit='dimensionless'), self._field('a1', 'section 1 denominator', stored_unit='dimensionless'), self._field('b2', 'section 2 numerator', stored_unit='dimensionless'), self._field('a2', 'section 2 denominator', stored_unit='dimensionless'))),)

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (self._field('Fs', 'sample rate', stored_unit='Hz', display_unit='GHz', scale=1e-09),)

    def __post_init__(self) -> None:
        for name in ('b1', 'a1', 'b2', 'a2'):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.ndim != 1 or value.size == 0 or (not np.all(np.isfinite(value))):
                raise ValueError(f'COMBilinearCTLE.{name} must be a finite 1-D array.')
            value = value.copy()
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        if not np.isfinite(float(self.Fs)) or float(self.Fs) <= 0.0:
            raise ValueError('COMBilinearCTLE.Fs must be finite and positive.')
        object.__setattr__(self, 'Fs', float(self.Fs))

    def filtered(self, ir: np.ndarray) -> np.ndarray:
        """Apply both causal IIR sections with zero initial state."""
        ir = np.asarray(ir, dtype=float)
        if ir.ndim != 1 or not np.all(np.isfinite(ir)):
            raise ValueError('COMBilinearCTLE input must be a finite 1-D array.')
        return np.asarray(lfilter(self.b2, self.a2, lfilter(self.b1, self.a1, ir)), dtype=float)

class IEEECOMFilter(LinkSegment):
    """
    IEEE 802.3 Annex 178A COM-specific scalar filter builders.

    Class boundary
    --------------
    IEEECOMFilter owns scalar transfer-function blocks defined by COM equations.
    The FFT/grid convention and scalar response conversion remain in
    LinkSegment.
    """

    @classmethod
    def rx_noise_filter(cls, cfg: LinkConfig, fr: float) -> 'IEEECOMFilter':
        """
        Build the receiver noise filter.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-20.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        fr:
            Receiver noise-filter bandwidth in Hz.
        """
        p1 = 3.414214
        p2 = 2.613126
        f = cfg.freqs
        H_r = 1.0 / (1.0 - p1 * (f / fr) ** 2 + (f / fr) ** 4 + 1j * p2 * (f / fr - (f / fr) ** 3))
        return cls.from_tf(f_meas=f, H_meas=H_r, cfg=cfg)

    @classmethod
    def tx_ffe(cls, cfg: LinkConfig, txfir: np.ndarray, num_pre: int) -> 'IEEECOMFilter':
        """
        Build the TX FFE transfer function.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-21.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        txfir:
            TX FFE tap coefficients, dimensionless.
        num_pre:
            Number of pre-cursor taps before the main cursor, in taps.
        """
        if np.argmax(np.abs(txfir)) != num_pre:
            raise ValueError('TX FFE main cursor index must equal num_pre.')
        f = cfg.freqs
        H_ffe = np.zeros_like(f, dtype=complex)
        for idx, c_i in enumerate(txfir):
            n = idx - num_pre
            H_ffe += c_i * np.exp(-1j * 2 * np.pi * n * f / cfg.fb)
        return cls.from_tf(f_meas=f, H_meas=H_ffe, cfg=cfg)

    @classmethod
    def rect_pulse(cls, cfg: LinkConfig, At: float) -> 'IEEECOMFilter':
        """
        Build the rectangular transmit pulse transfer function.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-23.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        At:
            Rectangular pulse amplitude in V.
        """
        f = cfg.freqs
        X_f = At * cfg.bt * np.sinc(f * cfg.bt)
        return cls.from_tf(f, X_f, cfg)

    @classmethod
    def transition_time_filter(cls, cfg: LinkConfig, Tr: float) -> 'IEEECOMFilter':
        """
        Build the transmitter transition-time filter.

        Reference:
        - IEEE 802.3 Annex 93A, Eq. 93A-46.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        Tr:
            20%-80% transition time in seconds.
        """
        p1 = 1.6832
        f = cfg.freqs
        Tr = float(Tr)
        H_t = np.exp(-2 * (np.pi * f * Tr / p1) ** 2)
        return cls.from_tf(f, H_t, cfg=cfg)

    @classmethod
    def rx_equalizer_93A(cls, cfg: LinkConfig, g_DC: float, g_DC2: float, f_z: float, f_LF: float, f_p1: float, f_p2: float) -> 'IEEECOMFilter':
        """
        Build the receiver equalizer transfer function.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-22.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        g_DC:
            First DC gain term in dB.
        g_DC2:
            Second DC gain term in dB.
        f_z, f_LF, f_p1, f_p2:
            Equalizer pole/zero frequencies in Hz.
        """
        f = cfg.freqs
        denom = (1 + 1j * f / f_p1) * (1 + 1j * f / f_p2) * (1 + 1j * f / f_LF)
        H_ctf = (10 ** (g_DC / 20) + 1j * f / f_z) * (10 ** (g_DC2 / 20) + 1j * f / f_LF) / denom
        return cls.from_tf(f, H_ctf, cfg)

    @classmethod
    def _from_finite_record_ir(cls, ir: np.ndarray, cfg: LinkConfig) -> 'IEEECOMFilter':
        """Store an intentional finite FFT record without causality correction.

        The reference bilinear-CTLE path keeps the raw IFFT record when
        causality enforcement is disabled.  This model-local constructor keeps
        that behavior out of the general ``LinkSegment.from_ir()`` contract.
        """
        segment = cls(cfg)
        record = segment.validate_ir(ir, correct_wrap=False)
        segment._raw_ir = record
        segment._causal_ir = record
        segment._causal_shift_samples = 0
        segment._ir = record
        return segment

    @classmethod
    def rx_equalizer(cls, cfg: LinkConfig, g_1: float, g_2: float, f_z1: float, f_z2: float, f_p1: float, f_p2: float, f_p3: float | None=None) -> 'IEEECOMFilter':
        """
        Build the 178A receiver equalizer transfer function.

        The IO uses the 178A spec-facing two-zero / three-pole names. When
        mapped from the aligned 93A Ad Hoc form, ``f_z2`` and ``f_p3`` both
        receive ``f_HP_PZ`` so they represent the same low-frequency term.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        g_1, g_2:
            178A CTF gain terms in dB.
        f_z1, f_z2:
            178A CTF zero frequencies in Hz.
        f_p1, f_p2:
            Required CTF pole frequencies in Hz.
        f_p3:
            Optional third pole frequency in Hz. ``None`` bypasses this pole.
        """
        f = cfg.freqs
        pole_values = (f_p1, f_p2) if f_p3 is None else (f_p1, f_p2, f_p3)
        if any((float(value) <= 0.0 or not np.isfinite(float(value)) for value in pole_values)):
            raise ValueError('CTF pole frequencies must be finite and positive.')
        denom = np.ones_like(f, dtype=complex)
        for pole in pole_values:
            denom *= 1 + 1j * f / float(pole)
        H_ctf = (10 ** (g_1 / 20) + 1j * f / f_z1) * (10 ** (g_2 / 20) + 1j * f / f_z2) / denom
        return cls.from_tf(f, H_ctf, cfg)

    @staticmethod
    def _bilinear_section_coefficients(cfg: LinkConfig, *, f_z: float, f_p1: float, g_dc: float, f_p2: Optional[float]=None) -> tuple[np.ndarray, np.ndarray]:
        """Build one causal CTLE section using the MATLAB TD_CTLE mapping."""
        values = {'f_z': f_z, 'f_p1': f_p1}
        if f_p2 is not None:
            values['f_p2'] = f_p2
        if any((not np.isfinite(float(value)) or float(value) <= 0.0 for value in values.values())):
            raise ValueError('Bilinear CTLE frequencies must be finite and positive.')
        if not np.isfinite(float(g_dc)):
            raise ValueError('Bilinear CTLE gain must be finite.')
        K = 2.0 * float(cfg.Fs)
        p1 = -2.0 * np.pi * float(f_p1)
        zero = -2.0 * np.pi * float(f_z) * 10.0 ** (float(g_dc) / 20.0)
        p1d = (K + p1) / (K - p1)
        zd = (K + zero) / (K - zero)
        if f_p2 is None:
            gain = (K - zero) / (K - p1) * float(f_p1) / float(f_z)
            b = gain * np.array([1.0, -zd], dtype=float)
            a = np.array([1.0, -p1d], dtype=float)
        else:
            p2 = -2.0 * np.pi * float(f_p2)
            p2d = (K + p2) / (K - p2)
            kd = (K - zero) / ((K - p1) * (K - p2)) * float(f_p1) / float(f_z)
            b = -p2 * kd * np.poly([zd, -1.0])
            a = np.poly([p1d, p2d])
        poles = np.roots(a)
        if not np.all(np.isfinite(poles)) or np.any(np.abs(poles) >= 1.0):
            raise ValueError('Bilinear CTLE section must have poles inside the unit circle.')
        return (np.asarray(b, dtype=float), np.asarray(a, dtype=float))

    @classmethod
    def apply_rx_equalizer_bilinear(cls, ir: np.ndarray, cfg: LinkConfig, *, g_1: float, g_2: float, f_z1: float, f_z2: float, f_p1: float, f_p2: float, f_p3: float) -> np.ndarray:
        """Apply two CTLE IIR sections to a normalized discrete-time kernel."""
        ir = np.asarray(ir, dtype=float)
        if ir.ndim != 1 or ir.size != cfg.Nfft or (not np.all(np.isfinite(ir))):
            raise ValueError('Bilinear CTLE input must be a finite full-grid discrete kernel.')
        b1, a1 = cls._bilinear_section_coefficients(cfg, f_z=f_z1, f_p1=f_p1, f_p2=f_p2, g_dc=g_1)
        b2, a2 = cls._bilinear_section_coefficients(cfg, f_z=f_z2, f_p1=f_p3, g_dc=g_2)
        return COMBilinearCTLE(b1=b1, a1=a1, b2=b2, a2=a2, Fs=cfg.Fs).filtered(ir)

    @classmethod
    def build_rx_equalizer_bilinear(cls, cfg: LinkConfig, *, g_1: float, g_2: float, f_z1: float, f_z2: float, f_p1: float, f_p2: float, f_p3: float) -> COMBilinearCTLE:
        """Build the shared two-section digital CTLE for one candidate."""
        b1, a1 = cls._bilinear_section_coefficients(cfg, f_z=f_z1, f_p1=f_p1, f_p2=f_p2, g_dc=g_1)
        b2, a2 = cls._bilinear_section_coefficients(cfg, f_z=f_z2, f_p1=f_p3, g_dc=g_2)
        return COMBilinearCTLE(b1=b1, a1=a1, b2=b2, a2=a2, Fs=cfg.Fs)

    @classmethod
    def rx_noise_filter_93A(cls, cfg: LinkConfig, fr: float) -> 'IEEECOMFilter':
        return cls.rx_noise_filter(cfg, fr)

    @classmethod
    def tx_ffe_93A(cls, cfg: LinkConfig, txfir: np.ndarray, num_pre: int) -> 'IEEECOMFilter':
        return cls.tx_ffe(cfg, txfir, num_pre)

    @classmethod
    def rect_pulse_93A(cls, cfg: LinkConfig, At: float) -> 'IEEECOMFilter':
        return cls.rect_pulse(cfg, At)

    @classmethod
    def transition_time_filter_93A(cls, cfg: LinkConfig, Tr: float) -> 'IEEECOMFilter':
        return cls.transition_time_filter(cfg, Tr)

def _build_txpkg(freqs: np.ndarray, txpkg_cfg: COMPkgConfig, *, isNext: bool=False) -> IEEECOMSparam:
    """
    Build the 178A TX package S-parameter model.

    The current 178A package contract is:
        device termination -> device package -> partial host channel
    """
    freqs = LinkConfig.validate_freqs(freqs)
    S_td = IEEECOMSparam.device_termination(freqs=freqs, R0=txpkg_cfg.R0, dt_cfg=txpkg_cfg.device_term)
    S_tp = IEEECOMSparam.device_package(freqs=freqs, R0=txpkg_cfg.R0, dp_cfg=txpkg_cfg.device_pkg)
    S_th = IEEECOMSparam.partial_host_channel(freqs=freqs, R0=txpkg_cfg.R0, ph_cfg=txpkg_cfg.partial_host)
    return S_td.cascade_com(S_tp).cascade_com(S_th)

def _build_rxpkg(freqs: np.ndarray, rxpkg_cfg: COMPkgConfig) -> IEEECOMSparam:
    """
    Build the 178A RX package S-parameter model.

    Build in die-to-channel order, then exchange the completed two-port's
    ports so the returned model is oriented channel-to-die.
    """
    freqs = LinkConfig.validate_freqs(freqs)
    S_rh = IEEECOMSparam.partial_host_channel(freqs=freqs, R0=rxpkg_cfg.R0, ph_cfg=rxpkg_cfg.partial_host)
    S_rp = IEEECOMSparam.device_package(freqs=freqs, R0=rxpkg_cfg.R0, dp_cfg=rxpkg_cfg.device_pkg)
    S_rd = IEEECOMSparam.device_termination(freqs=freqs, R0=rxpkg_cfg.R0, dt_cfg=rxpkg_cfg.device_term)
    S_rx_die_to_channel = S_rd.cascade_com(S_rp).cascade_com(S_rh)
    return S_rx_die_to_channel.reverse_ports()

def _build_H_ffe(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """Build the 178A victim/FEXT TX FFE filter."""
    ft_cfg.validate_txfir_main_cursor()
    return IEEECOMFilter.tx_ffe(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)

def _build_H_ffe_next(link_cfg: LinkConfig) -> IEEECOMFilter:
    """Build the 178A NEXT TX FFE filter."""
    ffe_next = np.array([0, 1, 0])
    return IEEECOMFilter.tx_ffe(link_cfg, ffe_next, num_pre=1)

def _build_H_t(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """Build the 178A transmitter transition-time filter."""
    return IEEECOMFilter.transition_time_filter(link_cfg, ft_cfg.Tr)

def _build_H_r(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """Build the 178A receiver noise filter."""
    return IEEECOMFilter.rx_noise_filter(link_cfg, ft_cfg.fr)

def _build_H_ctf(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build the 178A receiver equalizer / CTF filter.

    Maps COMFilterConfig178A directly to IEEECOMFilter.rx_equalizer().
    """
    required = {'g_1': ft_cfg.g_1, 'g_2': ft_cfg.g_2, 'f_z1': ft_cfg.f_z1, 'f_z2': ft_cfg.f_z2, 'f_p1': ft_cfg.f_p1, 'f_p2': ft_cfg.f_p2, 'f_p3': ft_cfg.f_p3}
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError('COMFilterConfig178A is missing required CTF fields: ' + ', '.join(missing))
    return IEEECOMFilter.rx_equalizer(link_cfg, required['g_1'], required['g_2'], required['f_z1'], required['f_z2'], required['f_p1'], required['f_p2'], required['f_p3'])

def _reference_fd_to_td_record(measured_freqs: np.ndarray, measured_tf: np.ndarray, link_cfg: LinkConfig, *, relative_truncation_threshold: float=0.001) -> np.ndarray:
    """Realize the reference raw-IFFT finite record consumed by TD CTLE.

    This is the fixed numerical definition of ``bilinear_iir``: retain the
    measured frequency spacing, interpolate magnitude and unwrapped phase onto
    the nearest compatible Nyquist grid, zero above the measured band, perform
    a raw Hermitian IFFT with no causality correction, then retain through the
    last sample above 0.1% of the impulse peak.
    """
    freqs = LinkConfig.validate_freqs(measured_freqs)
    response = np.asarray(measured_tf, dtype=complex)
    if response.shape != freqs.shape or not np.all(np.isfinite(response)):
        raise ValueError('measured CTLE input TF must be finite and match its frequency grid.')
    if len(freqs) < 3:
        raise ValueError('reference FD-to-TD realization requires at least three frequency points.')
    measured_df = float(freqs[2] - freqs[1])
    if measured_df <= 0.0:
        raise ValueError('reference FD-to-TD realization requires positive frequency spacing.')
    n_steps = max(1, int(np.floor(link_cfg.f_nyq / measured_df + 0.5)))
    output_freqs = np.arange(n_steps + 1, dtype=float) * (link_cfg.f_nyq / n_steps)
    magnitude = np.abs(response)
    phase = np.unwrap(np.angle(response))
    if freqs[0] > 0.0:
        low_count = min(10, len(freqs))
        magnitude_at_dc = float(np.polyval(np.polyfit(freqs[:low_count], magnitude[:low_count], 1), 0.0))
        freqs = np.r_[0.0, freqs]
        magnitude = np.r_[max(magnitude_at_dc, np.finfo(float).eps), magnitude]
        phase = np.r_[0.0, phase]
    in_band = output_freqs <= freqs[-1]
    interpolated = np.zeros(output_freqs.shape, dtype=complex)
    magnitude_i = np.interp(output_freqs[in_band], freqs, magnitude)
    phase_i = np.interp(output_freqs[in_band], freqs, phase)
    interpolated[in_band] = magnitude_i * np.exp(1j * phase_i)
    interpolated[0] = interpolated[0].real + 0j
    interpolated[-1] = interpolated[-1].real + 0j
    raw_record = np.fft.irfft(interpolated, n=2 * n_steps)
    peak = float(np.max(np.abs(raw_record)))
    retained = np.flatnonzero(np.abs(raw_record) > peak * relative_truncation_threshold)
    if len(retained) == 0:
        return raw_record[:1].copy()
    return raw_record[:int(retained[-1]) + 1].copy()

def _evaluate_pre_ctle_on_measured_grid(S_all: SparamModel, link_cfg: LinkConfig, channel_cfg: COMChannelConfig, ft_cfg: COMFilterConfig, *, kind: Literal['victim', 'next', 'fext'], include_txffe: bool=True) -> tuple[np.ndarray, np.ndarray]:
    """Build the composite pre-CTLE TF on the measured S-parameter grid."""
    freqs = S_all.freqs
    H_21 = S_all.voltage_transfer_function(gamma_src=channel_cfg.gamma_src, gamma_load=channel_cfg.gamma_load)
    if not include_txffe:
        txfir = np.array([1.0])
        num_pre = 0
    elif kind == 'next':
        txfir = np.array([0.0, 1.0, 0.0])
        num_pre = 1
    else:
        txfir = np.asarray(ft_cfg.txfir, dtype=float)
        num_pre = int(ft_cfg.num_pre)
    H_ffe = np.zeros_like(freqs, dtype=complex)
    for tap_index, coefficient in enumerate(txfir):
        n = tap_index - num_pre
        H_ffe += coefficient * np.exp(-1j * 2.0 * np.pi * n * freqs / link_cfg.fb)
    H_t = np.exp(-2.0 * (np.pi * freqs * ft_cfg.Tr / 1.6832) ** 2)
    ratio = freqs / ft_cfg.fr
    H_r = 1.0 / (1.0 - 3.414214 * ratio ** 2 + ratio ** 4 + 1j * 2.613126 * (ratio - ratio ** 3))
    time_origin = np.exp(-1j * 2.0 * np.pi * freqs * (3.0 * ft_cfg.Tr))
    return (freqs, H_ffe * H_t * H_21 * H_r * time_origin)

def _realize_ctle_response(pre_ctle: LinkSegment, H_ctf: LinkSegment, link_cfg: LinkConfig, realization: Literal['continuous_tf', 'bilinear_iir'], ctle_iir: Optional[COMBilinearCTLE], *, measured_freqs: Optional[np.ndarray]=None, measured_tf: Optional[np.ndarray]=None) -> tuple[LinkSegment, Literal['frequency_tf', 'finite_record_ir']]:
    """Realize only the CTLE output from an already-built pre-CTLE response.

    TX FFE, channel/package cascade, receiver filtering, and symbol-pulse
    formation are outside this boundary.  The returned domain tag tells the
    common symbol-pulse helper how to preserve the selected realization's
    numerical convolution semantics.
    """
    if realization == 'continuous_tf':
        return (pre_ctle.cascade_tf(H_ctf), 'frequency_tf')
    if realization != 'bilinear_iir':
        raise ValueError('CTLE pulse realization must be continuous_tf or bilinear_iir.')
    if ctle_iir is None:
        raise ValueError('bilinear_iir realization requires shared.ctle_iir.')
    if not np.isclose(ctle_iir.Fs, link_cfg.Fs, rtol=0.0, atol=0.0):
        raise ValueError('shared.ctle_iir sample rate must match LinkConfig.Fs.')
    if measured_freqs is None or measured_tf is None:
        raise ValueError('bilinear_iir realization requires the measured pre-CTLE TF.')
    discrete_kernel = _reference_fd_to_td_record(measured_freqs, measured_tf, link_cfg)
    ctle_ir = ctle_iir.filtered(discrete_kernel)
    ctle_record = np.zeros(link_cfg.Nfft, dtype=float)
    if len(ctle_ir) > link_cfg.Nfft:
        raise COMLengthMismatchError(f'bilinear CTLE finite record exceeds LinkConfig.Nfft: len={len(ctle_ir)}, Nfft={link_cfg.Nfft}.')
    ctle_record[:len(ctle_ir)] = ctle_ir * link_cfg.Fs
    return (IEEECOMFilter._from_finite_record_ir(ctle_record, link_cfg), 'finite_record_ir')

def _apply_rectangular_unit_pulse(post_ctle: LinkSegment, X: LinkSegment, link_cfg: LinkConfig, amplitude: float, domain: Literal['frequency_tf', 'finite_record_ir']) -> LinkSegment:
    """Apply the common one-UI rectangular symbol pulse after CTLE realization."""
    if domain == 'frequency_tf':
        return post_ctle.cascade_tf(X)
    if domain != 'finite_record_ir':
        raise ValueError('CTLE response domain must be frequency_tf or finite_record_ir.')
    discrete_kernel = post_ctle.ir / link_cfg.Fs
    support = np.flatnonzero(discrete_kernel != 0.0)
    discrete_kernel = discrete_kernel[:int(support[-1]) + 1] if len(support) else discrete_kernel[:1]
    pulse_ir = lfilter(np.ones(link_cfg.per_ui, dtype=float), np.array([1.0]), discrete_kernel) * float(amplitude)
    pulse_record = np.zeros(link_cfg.Nfft, dtype=float)
    if len(pulse_ir) > link_cfg.Nfft:
        raise COMLengthMismatchError(f'bilinear CTLE symbol pulse exceeds LinkConfig.Nfft: len={len(pulse_ir)}, Nfft={link_cfg.Nfft}.')
    pulse_record[:len(pulse_ir)] = pulse_ir
    return IEEECOMFilter._from_finite_record_ir(pulse_record, link_cfg)

def _build_channel_under_test(channel_cfg: COMChannelConfig, renormalization_order: Literal['sdd_first', 's4p_first']='sdd_first') -> list[SparamModel]:
    """
    Build 178A measured-domain channel-under-test S-parameter models.

    Output contract:
    - index 0: victim
    - following indices: NEXT channels, then FEXT channels
    """
    if renormalization_order not in ('sdd_first', 's4p_first'):
        raise ValueError('renormalization_order must be sdd_first or s4p_first.')
    if channel_cfg.victim_s4p_path is None:
        raise ValueError('channel_cfg.victim_s4p_path must be provided.')
    paths = [channel_cfg.victim_s4p_path, *channel_cfg.next_s4p_paths, *channel_cfg.fext_s4p_paths]
    if renormalization_order == 'sdd_first':
        channels = [
            IEEECOMSparam.from_touchstone(
                path,
                mode='s4p',
                port_order=channel_cfg.port_order,
                z0=2.0 * channel_cfg.R0,
                frequency_limit_Hz=channel_cfg.sparam_frequency_limit_Hz,
            )
            for path in paths
        ]
    else:
        channels = [
            SparamModel.from_touchstone(
                path,
                mode='s4p',
                port_order=channel_cfg.port_order,
                z0=2.0 * channel_cfg.R0,
                renormalization_order='s4p_first',
                frequency_limit_Hz=channel_cfg.sparam_frequency_limit_Hz,
            )
            for path in paths
        ]
    common_freqs = channel_cfg.align_grid(channels)
    return [channel.resampled(common_freqs) for channel in channels]

def _build_path(link_cfg: LinkConfig, channel_cfg: COMChannelConfig, ft_cfg: COMFilterConfig, txpkg_cfg: COMPkgConfig, shared: COMSharedPath, kind: Literal['victim', 'next', 'fext'], S_ch: SparamModel, out_of_measured: Literal['cosine_decay', 'zero_padding'], ctle_pulse_realization: Literal['continuous_tf', 'bilinear_iir']) -> COMPath:
    """
    Build one 178A COM signal path from a measured-domain channel-under-test model.

    The package, CTF, and pulse realization are version-owned by this stage.
    """
    if not np.allclose(S_ch.freqs, shared.S_rx.freqs):
        raise ValueError('S_ch.freqs must match shared.S_rx.freqs for measured-domain cascade.')
    if kind == 'next':
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg, isNext=True)
        H_ffe = shared.H_ffe_next
        amplitude = ft_cfg.A_ne
        X = IEEECOMFilter.rect_pulse(link_cfg, amplitude)
    elif kind == 'fext':
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        amplitude = ft_cfg.A_fe
        X = IEEECOMFilter.rect_pulse(link_cfg, amplitude)
    elif kind == 'victim':
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        amplitude = ft_cfg.A_v
        X = IEEECOMFilter.rect_pulse(link_cfg, amplitude)
    else:
        raise ValueError(f'Unsupported COM path kind: {kind}')
    S_all = S_tx.cascade_com(S_ch).cascade_com(shared.S_rx)
    H_21 = S_all.to_LinkSegment(link_cfg, gamma_src=channel_cfg.gamma_src, gamma_load=channel_cfg.gamma_load, dc=channel_cfg.missing_dc_policy, out_of_measured=out_of_measured)
    H_pre = H_ffe.cascade_tf(shared.H_t).cascade_tf(H_21).cascade_tf(shared.H_r)
    H_all = H_pre.cascade_tf(shared.H_ctf)
    measured_freqs = None
    measured_pre_ctle = None
    if ctle_pulse_realization == 'bilinear_iir':
        measured_freqs, measured_pre_ctle = _evaluate_pre_ctle_on_measured_grid(S_all, link_cfg, channel_cfg, ft_cfg, kind=kind)
    post_ctle, pulse_domain = _realize_ctle_response(H_pre, shared.H_ctf, link_cfg, ctle_pulse_realization, shared.ctle_iir, measured_freqs=measured_freqs, measured_tf=measured_pre_ctle)
    pulse = _apply_rectangular_unit_pulse(post_ctle, X, link_cfg, amplitude, pulse_domain)
    return COMPath(kind=kind, shared=shared, S_tx=S_tx, S_ch=S_ch, S_all=S_all, H_21=H_21, H_all=H_all, X=X, pulse=pulse)

def _build_shared_path(cfg: COMConfig, freqs: np.ndarray) -> COMSharedPath:
    """
    Build 178A path-shared COM models.

    The returned COMSharedPath keeps the same fields as 93A:
    H_ffe, H_ffe_next, H_t, S_rx, H_r, H_ctf.
    """
    link_cfg = cfg.link
    ft_cfg = cfg.filter
    H_ctf = _build_H_ctf(link_cfg, ft_cfg)
    ctle_iir = None
    if cfg.policy.ctle_pulse_realization == 'bilinear_iir':
        required = {'g_1': ft_cfg.g_1, 'g_2': ft_cfg.g_2, 'f_z1': ft_cfg.f_z1, 'f_z2': ft_cfg.f_z2, 'f_p1': ft_cfg.f_p1, 'f_p2': ft_cfg.f_p2, 'f_p3': ft_cfg.f_p3}
        missing = [name for name, value in required.items() if value is None]
        if missing:
            raise ValueError('COMFilterConfig178A is missing required bilinear CTF fields: ' + ', '.join(missing))
        ctle_iir = IEEECOMFilter.build_rx_equalizer_bilinear(link_cfg, g_1=required['g_1'], g_2=required['g_2'], f_z1=required['f_z1'], f_z2=required['f_z2'], f_p1=required['f_p1'], f_p2=required['f_p2'], f_p3=required['f_p3'])
    return COMSharedPath(H_ffe=_build_H_ffe(link_cfg, ft_cfg), H_ffe_next=_build_H_ffe_next(link_cfg), H_t=_build_H_t(link_cfg, ft_cfg), S_rx=_build_rxpkg(freqs, cfg.rxpkg), H_r=_build_H_r(link_cfg, ft_cfg), H_ctf=H_ctf, ctle_iir=ctle_iir)

def _build_paths(cfg: COMConfig, shared: COMSharedPath, channels: list[SparamModel]) -> list[COMPath]:
    """
    Build 178A path-specific COM models from aligned channel-under-test models.

    Preserve victim, NEXT, and FEXT ordering defined by COMChannelConfig.
    """
    link_cfg = cfg.link
    ch_cfg = cfg.channel
    ft_cfg = cfg.filter
    expected_count = 1 + len(ch_cfg.next_s4p_paths) + len(ch_cfg.fext_s4p_paths)
    if len(channels) != expected_count:
        raise COMLengthMismatchError(f'channels length must match victim + NEXT + FEXT path count. Expected {expected_count}, got {len(channels)}.')
    paths = [_build_path(link_cfg=link_cfg, channel_cfg=ch_cfg, ft_cfg=ft_cfg, txpkg_cfg=cfg.txpkg_victim, shared=shared, kind='victim', S_ch=channels[0], out_of_measured=cfg.policy.out_of_measured, ctle_pulse_realization=cfg.policy.ctle_pulse_realization)]
    next_count = len(ch_cfg.next_s4p_paths)
    next_channels = channels[1:1 + next_count]
    fext_channels = channels[1 + next_count:]
    for S_ch in next_channels:
        paths.append(_build_path(link_cfg=link_cfg, channel_cfg=ch_cfg, ft_cfg=ft_cfg, txpkg_cfg=cfg.txpkg_next, shared=shared, kind='next', S_ch=S_ch, out_of_measured=cfg.policy.out_of_measured, ctle_pulse_realization=cfg.policy.ctle_pulse_realization))
    for S_ch in fext_channels:
        paths.append(_build_path(link_cfg=link_cfg, channel_cfg=ch_cfg, ft_cfg=ft_cfg, txpkg_cfg=cfg.txpkg_fext, shared=shared, kind='fext', S_ch=S_ch, out_of_measured=cfg.policy.out_of_measured, ctle_pulse_realization=cfg.policy.ctle_pulse_realization))
    return paths

__all__ = [
    "COMBilinearCTLE", "IEEECOMFilter", "IEEECOMSparam",
    "_build_H_ctf", "_build_H_ffe", "_build_H_ffe_next", "_build_H_r", "_build_H_t",
    "_build_channel_under_test", "_build_path", "_build_paths", "_build_rxpkg",
    "_build_shared_path", "_build_txpkg",
]
