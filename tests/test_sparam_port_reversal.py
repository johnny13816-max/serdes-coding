import numpy as np

from serdes_coding.models.com_model_178A import (
    COMDevicePackageConfig,
    COMDeviceTermConfig,
    COMPartialHostConfig,
    COMPkgConfig,
    IEEECOMSparam,
    _build_rxpkg,
    _build_txpkg,
)
from serdes_coding.utilities.sparam import SparamModel


def test_reverse_ports_swaps_smatrix_and_reference_impedance():
    freqs = np.asarray([1e9, 2e9])
    sdd = np.asarray([
        [[0.1 + 0.01j, 0.2 + 0.02j], [0.3 + 0.03j, 0.4 + 0.04j]],
        [[0.5 + 0.05j, 0.6 + 0.06j], [0.7 + 0.07j, 0.8 + 0.08j]],
    ])
    z0 = np.asarray([[90.0, 110.0], [91.0, 111.0]])
    model = SparamModel.from_sdd_array(freqs, sdd, z0=z0)

    reversed_model = model.reverse_ports()

    np.testing.assert_array_equal(reversed_model.sdd, sdd[:, ::-1, ::-1])
    np.testing.assert_array_equal(reversed_model.network.z0, z0[:, ::-1])
    np.testing.assert_array_equal(reversed_model.reverse_ports().sdd, sdd)
    np.testing.assert_array_equal(reversed_model.reverse_ports().network.z0, z0)


def test_reverse_ports_preserves_sparam_subclass():
    model = IEEECOMSparam.from_sdd_array(
        np.asarray([1e9, 2e9]),
        np.asarray(
            [
                [[0.1, 0.2], [0.3, 0.4]],
                [[0.2, 0.3], [0.4, 0.5]],
            ],
            dtype=complex,
        ),
        z0=100.0,
    )

    assert isinstance(model.reverse_ports(), IEEECOMSparam)


def test_178a_rx_package_is_forward_package_with_ports_reversed():
    freqs = np.linspace(0.0, 60e9, 101)
    cfg = COMPkgConfig(
        device_term=COMDeviceTermConfig(
            C_d_seq=[4e-14, 9e-14, 1.1e-13],
            L_s_seq=[1.3e-10, 1.5e-10, 1.4e-10],
            C_b=3e-14,
        ),
        device_pkg=COMDevicePackageConfig(
            z_p_seq=[12.0, 1.8],
            Z_c_seq=[87.5, 95.0],
            gamma_0=5e-4,
            a1=8.9e-4,
            a2=2e-4,
            tau=6.141e-3,
            C_p=4e-14,
        ),
        partial_host=COMPartialHostConfig(
            enable=True,
            C_0=2e-14,
            C_1=6e-14,
            z_h=9.0,
            Z_h=92.5,
            gamma_0=0.0,
            a1=5.95e-4,
            a2=2.6e-5,
            tau=5.79e-3,
        ),
        R0=46.25,
    )

    forward = _build_txpkg(freqs, cfg)
    rx = _build_rxpkg(freqs, cfg)

    np.testing.assert_allclose(rx.sdd, forward.sdd[:, ::-1, ::-1], atol=1e-14)
