import shutil
from pathlib import Path
import pytest
from etal.config import load_config
from etal import schema

FIXTURE = Path(__file__).parent / "fixtures" / "vault"

@pytest.fixture
def vault_path(tmp_path):
    dest = tmp_path / "vault"
    shutil.copytree(FIXTURE, dest)
    return dest

@pytest.fixture
def data(vault_path):
    return schema.load(load_config(vault_path))
