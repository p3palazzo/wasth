from glob import glob
import os
import pytest
import wasth.md2geojson

@pytest.fixture
def testfile():
    f = "testdata/casa/br_df-planaltina-casarao_azul.md"
    return f

def test_md2geojson(testfile):
    pass
