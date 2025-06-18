import pytest
from data_extraction import parse_subgenre_definitions # Corrected import relative to src
import os

# Create a temporary test file with sample subgenre definitions
SAMPLE_SUBGENRE_CONTENT = \
"""
AVANT-GARDE METAL
A Progressive Rock Sub-genre
From Progarchives.com, the ultimate progressive rock music website
Avant-garde Metal is a sub-genre of heavy metal music that is characterized by its use of experimentation and innovative, avant-garde elements.
FOOTNOTE:
This is a footnote.

EXPERIMENTAL ROCK
A Progressive Rock Sub-genre
From Progarchives.com, the ultimate progressive rock music website
Experimental Rock is a type of rock music that experiments with the basic elements of the genre.
"""

@pytest.fixture
def temp_subgenre_file(tmp_path):
    file_path = tmp_path / "temp_subgenres.txt"
    with open(file_path, "w") as f:
        f.write(SAMPLE_SUBGENRE_CONTENT)
    return str(file_path)

def test_parse_subgenre_definitions(temp_subgenre_file):
    expected_output = {
        "AVANT-GARDE METAL": "Avant-garde Metal is a sub-genre of heavy metal music that is characterized by its use of experimentation and innovative, avant-garde elements.",
        "EXPERIMENTAL ROCK": "Experimental Rock is a type of rock music that experiments with the basic elements of the genre."
    }
    actual_output = parse_subgenre_definitions(temp_subgenre_file)
    assert actual_output == expected_output

def test_parse_subgenre_definitions_empty_file(tmp_path):
    file_path = tmp_path / "empty_subgenres.txt"
    with open(file_path, "w") as f:
        f.write("")
    expected_output = {}
    actual_output = parse_subgenre_definitions(str(file_path))
    assert actual_output == expected_output

def test_parse_subgenre_definitions_no_definitions(tmp_path):
    file_path = tmp_path / "no_definitions_subgenres.txt"
    with open(file_path, "w") as f:
        f.write("SOME OTHER TEXT\nAND MORE TEXT")
    expected_output = {}
    actual_output = parse_subgenre_definitions(str(file_path))
    assert actual_output == expected_output

def test_parse_subgenre_definitions_real_file():
    # Assuming the real file is in a known location relative to the tests
    # Adjust the path as necessary
    real_file_path = os.path.join(os.path.dirname(__file__), "..", "ProgArchives Data", "ProgSubgenres")
    if not os.path.exists(real_file_path):
        pytest.skip(f"Real subgenre file not found at {real_file_path}")

    # This test doesn't assert specific content due to the file's size and variability
    # It primarily checks that the function runs without error and returns a dict
    result = parse_subgenre_definitions(real_file_path)
    assert isinstance(result, dict)
    # Optionally, check if some known keys are present if the file structure is stable
    # For example:
    # assert "AVANT-PROG" in result
    # assert "CANTERBURY SCENE" in result
    print(f"Parsed {len(result)} subgenres from the real file.")

