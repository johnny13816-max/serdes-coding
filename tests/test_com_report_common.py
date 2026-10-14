from pathlib import Path
from types import SimpleNamespace

import numpy as np

from serdes_coding.reporting.com_report_common import (
    plot_ct_pulse_and_samples,
    plot_combined_pmf_cdf,
    plot_equalizer_coefficients,
    plot_impairment_bars,
    plot_link_ir,
    plot_link_sr,
    plot_link_tf,
    plot_path_h21_overview,
    plot_path_il_overview,
    plot_path_pulse_overview,
    plot_path_sbr_overview,
    plot_sparam_il,
    plot_sparam_sdd,
    write_plot_manifest,
)


class _SModel:
    def __init__(self, freqs: np.ndarray):
        self.freqs = freqs
        self.sdd21 = 1.0 / (1.0 + 1j * freqs / 40e9)

    def plot_sdd(self, ax, **kwargs):
        ax.plot(self.freqs / 1e9, 20.0 * np.log10(np.abs(self.sdd21)), label="Sdd21")
        ax.set_xscale("log")

    def plot_IL(self, ax, **kwargs):
        ax.plot(
            self.freqs / 1e9,
            -20.0 * np.log10(1.0 + self.freqs / 1e9),
            label=kwargs.get("label"),
        )
        ax.set_xscale("log")

    def annotate_IL(self, ax, frequency_hz, **kwargs):
        ax.axvline(frequency_hz / 1e9, color="tab:red", linestyle="--")

    def frequency_at_sdd21_gain(self, gain_db):
        return 40e9

    def annotate_f(self, ax, frequency_hz, **kwargs):
        ax.axvline(frequency_hz / 1e9, color="tab:orange", linestyle=":")


class _Segment:
    def __init__(self, freqs: np.ndarray):
        self.freqs = freqs
        self.tf = 1.0 / (1.0 + 1j * freqs / 45e9)
        self.times = np.linspace(-1e-10, 4e-10, 401)
        self.ir = np.exp(-((self.times - 1e-10) / 3e-11) ** 2)
        self.sr = np.cumsum(self.ir)
        self.sr /= np.max(self.sr)

    def plot_tf(self, ax, **kwargs):
        ax.plot(
            self.freqs / 1e9,
            -10.0 * np.log10(1.0 + self.freqs / 1e9),
            label=kwargs.get("label"),
        )
        ax.set_xscale("log")

    def annotate_f(self, ax, frequency_hz, **kwargs):
        ax.axvline(frequency_hz / 1e9, color="tab:red", linestyle="--")

    def frequency_at_gain(self, gain_db):
        return 45e9

    def plot_ir(self, ax, **kwargs):
        ax.plot(self.times * 100e9, self.ir)

    def plot_sr(self, ax, **kwargs):
        ax.plot(self.times * 100e9, self.sr)


class _PMF:
    def __init__(self):
        self.x = np.linspace(-1.0, 1.0, 401)
        density = np.exp(-0.5 * (self.x / 0.2) ** 2)
        self.pmf = density / np.sum(density)
        self.cdf = np.cumsum(self.pmf)
        self.dx = float(self.x[1] - self.x[0])

    def plot(self, ax, quantity="pmf", **kwargs):
        values = self.cdf if quantity == "cdf" else self.pmf
        ax.plot(self.x, values, label=kwargs.get("label"))


def _fixture():
    freqs = np.linspace(0.0, 120e9, 121)
    times_ui = np.linspace(-10.0, 30.0, 401)
    ir = np.exp(-((times_ui - 1.0) / 0.7) ** 2)
    pulse = SimpleNamespace(
        ir=ir,
        sbr=np.cumsum(ir),
        cfg=SimpleNamespace(times_ui=times_ui),
    )
    path = SimpleNamespace(
        kind="victim",
        pulse=pulse,
        S_all=_SModel(freqs),
        H_21=_Segment(freqs),
    )
    imp = SimpleNamespace(
        R_LM=0.95,
        SNR_TX=30.0,
        sigma_RJ=0.01,
        A_DD=0.02,
        eta_0=1e-18,
        N_qb=6,
        P_qc=1e-3,
    )
    cfg = SimpleNamespace(
        link=SimpleNamespace(fb=100e9, per_ui=32, df=1e7),
        imp=imp,
    )
    return cfg, path


def _assert_png(path: str) -> None:
    target = Path(path)
    assert target.is_file()
    assert target.stat().st_size > 1000


def test_shared_renderers_create_canonical_artifact_tree(tmp_path):
    cfg, path = _fixture()
    for renderer in (
        plot_path_pulse_overview,
        plot_path_sbr_overview,
        plot_path_il_overview,
        plot_path_h21_overview,
    ):
        _, output = renderer(cfg, [path], tmp_path)
        _assert_png(output)
        assert Path(output).parent == tmp_path / "overview"

    _, sampled_output = plot_ct_pulse_and_samples(
        cfg,
        path.pulse.ir,
        path.pulse.ir[:: cfg.link.per_ui],
        selected_pos=0,
        selected_ts=int(np.argmax(path.pulse.ir)),
        root=tmp_path / "equalization",
    )
    _assert_png(sampled_output)

    _, coefficient_output = plot_equalizer_coefficients(
        cfg,
        [
            ("FFE", np.arange(-1, 2), np.asarray([0.1, 1.0, -0.2])),
            ("DFE", np.arange(1, 3), np.asarray([-0.1, 0.05])),
        ],
        tmp_path / "equalization",
        title="Equalizer Coefficients",
    )
    _assert_png(coefficient_output)

    outputs = plot_impairment_bars(
        cfg,
        ["ISI", "RX noise", "crosstalk"],
        [0.05, 0.01, 0.02],
        tmp_path / "impairment" / "final",
        title_prefix="Final",
    )
    assert set(outputs) == {"imp_summary", "imp_proportion"}
    for output in outputs.values():
        _assert_png(output)

    detail_root = tmp_path / "path_victim"
    detail_outputs = []
    _, output = plot_sparam_sdd(
        cfg, path.S_all, detail_root,
        filename="S_all_sdd.png", title="S_all", annotate_nyq=True,
    )
    detail_outputs.append(output)
    _, output = plot_sparam_il(
        cfg, path.S_all, detail_root,
        filename="S_all_IL.png", title="S_all IL",
    )
    detail_outputs.append(output)
    _, output = plot_link_tf(
        cfg, path.H_21, detail_root,
        filename="H_21_tf.png", title="H_21", annotate_nyq=True,
    )
    detail_outputs.append(output)
    _, output = plot_link_ir(
        cfg, path.H_21, detail_root,
        filename="H_21_ir.png", title="H_21 IR",
    )
    detail_outputs.append(output)
    _, output = plot_link_sr(
        cfg, path.H_21, detail_root,
        filename="H_t_sr.png", title="H_t SR", annotate_20_80=True,
    )
    detail_outputs.append(output)
    for output in detail_outputs:
        _assert_png(output)

    _, combined_output = plot_combined_pmf_cdf(
        _PMF(),
        tmp_path / "pmf",
        der0=1e-3,
        y0=-0.6,
        a_ni=0.6,
        com_value=3.2,
        keep_mass=1.0,
    )
    _assert_png(combined_output)

    report = {"detail": detail_outputs, "bars": outputs, "pmf": combined_output}
    manifest = Path(write_plot_manifest(report, tmp_path))
    assert manifest.is_file()
    assert '"count": 8' in manifest.read_text(encoding="utf-8")
