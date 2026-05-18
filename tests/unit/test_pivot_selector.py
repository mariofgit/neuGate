import pytest

from neugate.services.pivot_selector import PivotSelector

pytestmark = pytest.mark.unit


def test_rotation_cycles_templates(project_config) -> None:
    selector = PivotSelector()
    first = selector.next_template(project_config)
    second = selector.next_template(project_config)
    third = selector.next_template(project_config)

    assert first == "Test pivot response A."
    assert second == "Test pivot response B."
    assert third == "Test pivot response A."
