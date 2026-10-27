from pathlib import Path

import numpy as np
import pytest

from serdes_coding.utilities.link import LinkConfig, LinkSegment


def segment_with_sbr(sbr: np.ndarray, *, per_ui: int = 4) -> LinkSegment:
    cfg = LinkConfig.from_Nfft(fb=1.0, per_ui=per_ui, Nfft=len(sbr))
    segment = LinkSegment(cfg)
    segment._sbr = np.asarray(sbr, dtype=float)
    return segment


def direct_trace(
    symbols: np.ndarray,
    sbr: np.ndarray,
    *,
    symbol_index: int,
    per_ui: int,
    half_window: int,
    alignment_sample: int,
) -> np.ndarray:
    samples = symbol_index * per_ui + alignment_sample + np.arange(-half_window, half_window + 1)
    result = np.zeros(len(samples), dtype=float)
    for output_index, sample in enumerate(samples):
        for input_index, amplitude in enumerate(symbols):
            response_index = sample - input_index * per_ui
            if 0 <= response_index < len(sbr):
                result[output_index] += amplitude * sbr[response_index]
    return result


def test_eye_traces_match_direct_sbr_superposition_and_main_cursor_alignment():
    sbr = np.zeros(16)
    sbr[3:8] = [0.1, 0.4, 1.0, 0.3, -0.1]
    symbols = np.asarray([-1.0, 1.0, 1.0, -1.0, 1.0])
    segment = segment_with_sbr(sbr)

    time_ui, traces = segment.eye_traces(symbols, ui_span=2, alignment="main_cursor")

    np.testing.assert_array_equal(time_ui, np.linspace(-1.0, 1.0, 9))
    assert traces.shape == (len(symbols), 9)
    main_cursor = int(np.argmax(np.abs(sbr)))
    for index in range(len(symbols)):
        expected = direct_trace(
            symbols,
            sbr,
            symbol_index=index,
            per_ui=4,
            half_window=4,
            alignment_sample=main_cursor,
        )
        np.testing.assert_allclose(traces[index], expected, atol=1e-14, rtol=0)


def test_eye_traces_record_start_and_discard_contract():
    sbr = np.zeros(16)
    sbr[:3] = [1.0, 0.5, 0.25]
    symbols = np.asarray([1.0, -1.0, 1.0, -1.0, 1.0])
    segment = segment_with_sbr(sbr)

    _, traces = segment.eye_traces(
        symbols, ui_span=2, alignment="record_start", discard_ui=1,
    )

    assert traces.shape == (3, 9)
    for row, index in enumerate(range(1, 4)):
        expected = direct_trace(
            symbols,
            sbr,
            symbol_index=index,
            per_ui=4,
            half_window=4,
            alignment_sample=0,
        )
        np.testing.assert_allclose(traces[row], expected, atol=1e-14, rtol=0)


@pytest.mark.parametrize(
    ("symbols", "kwargs", "message"),
    [
        (np.asarray([]), {}, "nonempty"),
        (np.asarray([[1.0]]), {}, "one-dimensional"),
        (np.asarray([1.0, np.nan]), {}, "non-finite"),
        (np.asarray([1.0]), {"ui_span": 0}, "positive integer"),
        (np.asarray([1.0]), {"discard_ui": -1}, "non-negative integer"),
        (np.asarray([1.0, -1.0]), {"discard_ui": 1}, "every available"),
        (np.asarray([1.0]), {"alignment": "invalid"}, "alignment"),
    ],
)
def test_eye_traces_validate_inputs(symbols, kwargs, message):
    segment = segment_with_sbr(np.r_[1.0, np.zeros(15)])
    with pytest.raises(ValueError, match=message):
        segment.eye_traces(symbols, **kwargs)


def test_eye_traces_require_a_center_sample_for_the_requested_grid():
    segment = segment_with_sbr(np.r_[1.0, np.zeros(17)], per_ui=3)
    with pytest.raises(ValueError, match="must be even"):
        segment.eye_traces(np.asarray([1.0, -1.0]), ui_span=1)


def test_plot_eye_uses_the_same_traces_and_writes_png(tmp_path: Path):
    import matplotlib.pyplot as plt

    sbr = np.zeros(16)
    sbr[4] = 1.0
    symbols = np.asarray([-1.0, 1.0, -1.0, 1.0])
    segment = segment_with_sbr(sbr)
    time_ui, traces = segment.eye_traces(symbols)
    output = tmp_path / "eye.png"

    fig, ax = plt.subplots()
    returned = segment.plot_eye(symbols, ax=ax, save_path=output, show=False)

    assert returned is ax
    assert output.is_file()
    assert len(ax.lines) == len(traces)
    for line, expected in zip(ax.lines, traces):
        np.testing.assert_array_equal(line.get_xdata(), time_ui)
        np.testing.assert_array_equal(line.get_ydata(), expected)
    plt.close(fig)


def test_eye_generation_does_not_modify_linksegment_responses():
    sbr = np.r_[0.0, 1.0, 0.25, np.zeros(13)]
    segment = segment_with_sbr(sbr)
    before = segment.sbr.copy()
    segment.eye_traces(np.asarray([-1.0, 1.0, -1.0]))
    np.testing.assert_array_equal(segment.sbr, before)
