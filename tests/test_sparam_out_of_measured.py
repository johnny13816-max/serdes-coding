import numpy as np
import pytest

from serdes_coding.utilities.link import LinkConfig
from serdes_coding.utilities.sparam import SparamModel


def test_sparam_to_linksegment_owns_measured_band_extension():
    cfg = LinkConfig(fb=2.0, per_ui=2, target_df=0.1)
    measured_freqs = np.array([0.0, 0.5, 1.0])
    sdd = np.zeros((measured_freqs.size, 2, 2), dtype=complex)
    sdd[:, 1, 0] = [0.8, 0.7 - 0.1j, 0.6 - 0.2j]
    model = SparamModel.from_sdd_array(measured_freqs, sdd, z0=100.0)

    cosine = model.to_LinkSegment(cfg, out_of_measured="cosine_decay")
    zero = model.to_LinkSegment(cfg, out_of_measured="zero_padding")
    default = model.to_LinkSegment(cfg)
    in_band = cfg.freqs <= measured_freqs[-1]
    beyond = ~in_band

    np.testing.assert_array_equal(cosine.tf, default.tf)
    np.testing.assert_array_equal(zero.tf[in_band], cosine.tf[in_band])
    np.testing.assert_array_equal(zero.tf[beyond], 0.0)
    assert np.any(np.abs(cosine.tf[beyond]) > 0.0)
    np.testing.assert_array_equal(model.sdd, sdd)

    with pytest.raises(ValueError, match="out_of_measured"):
        model.to_LinkSegment(cfg, out_of_measured="invalid")
