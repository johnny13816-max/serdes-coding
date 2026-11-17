from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from serdes_coding.utilities.link import LinkSegment
from serdes_coding.utilities.sparam import SparamModel


def test_plot_ir_normalization_only_changes_display():
    ir = np.array([0.25, -2.0, 1.0])
    draw = Mock(return_value="axes")
    segment = SimpleNamespace(ir=ir, _plot_time_response=draw)

    assert LinkSegment.plot_ir(segment, normalize_main_cursor=True) == "axes"
    np.testing.assert_array_equal(draw.call_args.kwargs["response"], [0.125, -1.0, 0.5])
    assert draw.call_args.kwargs["ylabel"] == "h(t) / main cursor"
    np.testing.assert_array_equal(ir, [0.25, -2.0, 1.0])
    LinkSegment.plot_ir(segment)
    np.testing.assert_array_equal(draw.call_args.kwargs["response"], ir)
    assert draw.call_args.kwargs["ylabel"] == "h(t)"


def test_plot_ir_normalization_accepts_tiny_nonzero_main_cursor():
    ir = np.array([1e-12, -2e-12])
    draw = Mock(return_value="axes")
    segment = SimpleNamespace(ir=ir, _plot_time_response=draw)

    assert LinkSegment.plot_ir(segment, normalize_main_cursor=True) == "axes"
    np.testing.assert_array_equal(draw.call_args.kwargs["response"], [0.5, -1.0])
    np.testing.assert_array_equal(ir, [1e-12, -2e-12])


@pytest.mark.parametrize("ir", [np.zeros(3), np.array([0.0, np.nan])])
def test_plot_ir_invalid_normalization(ir):
    segment = SimpleNamespace(ir=ir, _plot_time_response=Mock())
    with pytest.raises(ValueError, match="Cannot normalize IR"):
        LinkSegment.plot_ir(segment, normalize_main_cursor=True)
    segment._plot_time_response.assert_not_called()


def test_sparam_plot_ir_forwards_normalization():
    segment = SimpleNamespace(plot_ir=Mock(return_value="axes"))
    model = SimpleNamespace(_debug_LinkSegment=Mock(return_value=segment))
    assert SparamModel.plot_ir(model, cfg=object(), normalize_main_cursor=True) == "axes"
    assert segment.plot_ir.call_args.kwargs["normalize_main_cursor"] is True
