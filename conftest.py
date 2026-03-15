import os
import shutil
import pytest

@pytest.fixture(autouse=True)
def test_output_dir(request, tmp_path):
    """Give each test its own clean output directory: tests/output/<test_name>/"""
    output_dir = os.path.join(os.path.dirname(__file__), 'tests', 'output', request.node.name)
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)
    # Make it available via self._test_output_dir in unittest.TestCase subclasses
    if request.instance is not None:
        request.instance._test_output_dir = output_dir
