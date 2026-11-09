import pytest
from src.proxessor.core.cpu_topology import CPUTopology

def test_cpu_topology_initialization():
    topo = CPUTopology()
    assert topo.logical_cores_count >= 1
    assert len(topo.p_core_indices) >= 1
    assert topo.get_all_cores_mask() > 0

def test_cpu_topology_masks():
    topo = CPUTopology()
    all_mask = topo.get_all_cores_mask()
    p_mask = topo.get_p_cores_mask()
    e_mask = topo.get_e_cores_mask()

    assert all_mask == (1 << topo.logical_cores_count) - 1
    assert p_mask <= all_mask
    assert e_mask <= all_mask

def test_parse_affinity_mask():
    topo = CPUTopology()
    all_mask = topo.get_all_cores_mask()
    p_mask = topo.get_p_cores_mask()
    e_mask = topo.get_e_cores_mask()

    assert topo.parse_affinity_mask("ALL_CORES") == all_mask
    assert topo.parse_affinity_mask("P_CORES") == p_mask
    assert topo.parse_affinity_mask("E_CORES") == e_mask
    assert topo.parse_affinity_mask("0x3") == 0x3
    assert topo.parse_affinity_mask("7") == 7
    # Invalid defaults to all cores
    assert topo.parse_affinity_mask("INVALID_STRING") == all_mask
