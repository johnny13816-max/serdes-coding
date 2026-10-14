"""Reference-only 178A channel renormalization A/B; never changes model defaults.

Project path: S4P -> Sdd at measured differential Z0 -> Sdd renormalization.
SiCoPR path: renormalize the full single-ended S4P to R0 -> Sdd conversion.
"""

from __future__ import annotations

import argparse
import json
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path

import numpy as np
import skrf as rf

from serdes_coding.io.com_excel_io import excel_to_config_178A
import serdes_coding.models.com_model_178A as model
from serdes_coding.utilities.link import _s4p_to_sdd
from serdes_coding.utilities.sparam import SparamModel


def build_sicopr_order_channels(channel_cfg):
    """Build measured Sdd using SiCoPR's single-ended-first order for A/B only."""
    paths = [
        channel_cfg.victim_s4p_path,
        *channel_cfg.next_s4p_paths,
        *channel_cfg.fext_s4p_paths,
    ]
    if paths[0] is None:
        raise ValueError("A victim S4P path is required.")

    channels = []
    for path in paths:
        network = rf.Network(path)
        network.renormalize(channel_cfg.R0)
        sdd = _s4p_to_sdd(network.s, channel_cfg.port_order, network.f)
        channels.append(
            SparamModel.from_sdd_array(network.f, sdd, z0=2 * channel_cfg.R0)
        )

    common_freqs = channel_cfg.align_grid(channels)
    return [channel.resampled(common_freqs) for channel in channels]


@contextmanager
def sicopr_order_for_one_run():
    """Temporarily select the reference channel reader; restore it on exit."""
    original = model._build_channel_under_test
    model._build_channel_under_test = build_sicopr_order_channels
    try:
        yield
    finally:
        model._build_channel_under_test = original


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path, help="178A project config.xlsx")
    parser.add_argument("--run-mse", action="store_true", help="Run the full phase sweep")
    parser.add_argument(
        "--reference-mat", type=Path,
        help="SiCoPR locked-case MAT with pulse_ctle_ffe for SBR comparison",
    )
    parser.add_argument("--plot", type=Path, help="Output SBR overlay PNG")
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    args = parser.parse_args()
    if args.plot and not args.reference_mat:
        parser.error("--plot requires --reference-mat")

    cfg = excel_to_config_178A(args.config)
    canonical = model.COM(cfg).build_all_paths()
    with sicopr_order_for_one_run():
        branch = model.COM(cfg).build_all_paths()

    result = {
        "method": "SiCoPR single-ended S4P first; reference-only",
        "s_ch_max_complex_by_path": [
            float(np.max(np.abs(a.S_ch.sdd - b.S_ch.sdd)))
            for a, b in zip(canonical, branch, strict=True)
        ],
    }
    if args.reference_mat:
        from scipy.io import loadmat

        reference = np.asarray(
            loadmat(args.reference_mat)["pulse_ctle_ffe"]
        ).ravel()
        per_ui = cfg.link.per_ui
        offset_ui = 12
        offsets = np.arange(-offset_ui * per_ui, offset_ui * per_ui + 1)
        taps = np.arange(-offset_ui, offset_ui + 1)
        tap_indices = offset_ui * per_ui + taps * per_ui
        # This locked SiCoPR case uses a 3*Tr transition delay and a sampled
        # per-UI boxcar. Align time origins for comparison; change neither model.
        time_shift = 3 * cfg.filter.Tr + (per_ui - 1) / (2 * cfg.link.Fs)

        def aligned_pulse(path):
            spectrum = path.pulse.tf * np.exp(
                -1j * 2 * np.pi * cfg.link.freqs * time_shift
            )
            pulse = np.fft.irfft(spectrum, n=cfg.link.Nfft) * cfg.link.Fs
            peak = int(np.argmax(np.abs(pulse)))
            return pulse[peak + offsets], peak

        ref_peak = int(np.argmax(np.abs(reference)))
        ref_window = reference[ref_peak + offsets]
        ref_main = float(ref_window[offset_ui * per_ui])
        if ref_main == 0:
            raise ValueError("Reference main cursor is zero.")
        ref_norm = ref_window / ref_main
        project_norm = {}
        peak_indices = {"reference": ref_peak}
        for name, path in (("canonical", canonical[0]), ("sicopr_order", branch[0])):
            window, peak = aligned_pulse(path)
            norm = window / ref_main
            project_norm[name] = norm
            peak_indices[name] = peak
            result[f"{name}_sbr"] = {
                "peak_ratio": float(norm[offset_ui * per_ui]),
                "ui_max_norm": float(np.max(np.abs(norm[tap_indices] - ref_norm[tap_indices]))),
                "ui_rms_norm": float(np.sqrt(np.mean((norm[tap_indices] - ref_norm[tap_indices]) ** 2))),
            }
        result["sbr_time_shift_ps"] = float(time_shift * 1e12)
        result["sbr_peak_indices"] = peak_indices
        if args.plot:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            figure, axes = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
            axes[0].plot(offsets / per_ui, ref_norm, label="SiCoPR pre-RXFFE")
            for name, norm in project_norm.items():
                axes[0].plot(offsets / per_ui, norm, label=name)
                axes[1].plot(taps, norm[tap_indices] - ref_norm[tap_indices], "o-", label=name)
            axes[0].set(xlim=(-4, 9), ylabel="Pulse / reference main cursor")
            axes[1].set(xlim=(-4, 9), xlabel="UI from main cursor", ylabel="SBR difference")
            for axis in axes:
                axis.grid(alpha=0.2)
                axis.legend()
            figure.savefig(args.plot, dpi=180)
            plt.close(figure)
    if args.run_mse:
        cfg.execution.single_run = replace(cfg.execution.single_run, target="mse")
        with sicopr_order_for_one_run():
            status = model.COM(cfg).run(progress=False)
        result.update(
            selected_pos=int(status.dte.pos),
            selected_ts=int(status.dte.ts),
            mse=float(status.dte.mse),
            w_lim=status.dte.w_lim.tolist(),
            b_lim=status.dte.b_lim.tolist(),
            mse_by_pos=status.run.mse_by_pos,
        )

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
