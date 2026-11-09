import pytest
import uuid
from src.proxessor.core.win32_api import PRIORITY_MAP, IO_PRIORITY_MAP
from src.proxessor.core.power_manager import SCHEME_GUID_MAP, uuid_to_guid_struct

def test_priority_constants():
    assert "HIGH" in PRIORITY_MAP
    assert "BELOW_NORMAL" in PRIORITY_MAP
    assert PRIORITY_MAP["NORMAL"] == 0x20
    assert IO_PRIORITY_MAP["HIGH"] == 3

def test_power_guid_conversion():
    u = SCHEME_GUID_MAP["HIGH_PERFORMANCE"]
    guid = uuid_to_guid_struct(u)
    assert guid.Data1 != 0
