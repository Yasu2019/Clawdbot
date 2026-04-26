from app.guards import assert_read_only_sql
import pytest

def test_select_allowed():
    assert_read_only_sql('SELECT * FROM table1')

def test_delete_blocked():
    with pytest.raises(ValueError):
        assert_read_only_sql('DELETE FROM table1')
