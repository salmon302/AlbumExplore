import pytest
from pathlib import Path
from albumexplore.data.parsers.progarchives_parser import ProgArchivesParser

@pytest.fixture
def sample_html():
    return """
    <html>
        <body>
            <h1 class="album-title">Sample Album</h1>
            <div class="artist-name">Test Artist</div>
            <div class="genre">Progressive Metal</div>
            <div class="album-info">Studio Album, 2023</div>
            <div class="rating">4.5</div>
        </body>
    </html>
    """

@pytest.fixture
def sample_html_ep():
    return """
    <html>
        <body>
            <h1 class="album-title">EP Album</h1>
            <div class="artist-name">Test Artist</div>
            <div class="genre">Progressive Rock</div>
            <div class="album-info">EP, 2024</div>
            <div class="rating">4.0</div>
        </body>
    </html>
    """

@pytest.fixture
def tmp_html_file(tmp_path, sample_html):
    html_file = tmp_path / "test_album.html"
    html_file.write_text(sample_html)
    return html_file

@pytest.fixture
def tmp_html_files(tmp_path, sample_html, sample_html_ep):
    file1 = tmp_path / "test_album1.html"
    file2 = tmp_path / "test_album2.html"
    file1.write_text(sample_html)
    file2.write_text(sample_html_ep)
    return [file1, file2]

def test_parse_album(sample_html):
    parser = ProgArchivesParser(Path("."))
    result = parser.parse_album(sample_html)
    
    assert result["title"] == "Sample Album"
    assert result["artist"] == "Test Artist"
    assert result["genre"] == "Progressive Metal"
    assert result["record_type"] == "Studio"
    assert result["year"] == 2023
    assert result["rating"] == 4.5

def test_parse_album_ep(sample_html_ep):
    parser = ProgArchivesParser(Path("."))
    result = parser.parse_album(sample_html_ep)
    
    assert result["title"] == "EP Album"
    assert result["genre"] == "Progressive Rock"
    assert result["record_type"] == "EP"
    assert result["year"] == 2024
    assert result["rating"] == 4.0

def test_parse_directory(tmp_path, tmp_html_files):
    parser = ProgArchivesParser(tmp_path)
    df = parser.parse()
    
    assert len(df) == 2
    assert "Studio" in df["record_type"].values
    assert "EP" in df["record_type"].values
    assert all(year in df["year"].values for year in [2023, 2024])

def test_invalid_html():
    parser = ProgArchivesParser(Path("."))
    result = parser.parse_album("<invalid>html</invalid>")
    
    assert all(v is None for v in result.values())

def test_parse_record_info():
    parser = ProgArchivesParser(Path("."))
    
    test_cases = [
        ("Studio Album, 2023", ("Studio", 2023)),
        ("EP Release, 2024", ("EP", 2024)),
        ("Fan Club Release 1999", ("Fan Club", 1999)),
        ("Promo Single 2022", ("Promo", 2022)),
        ("Live Album 2021", (None, 2021)),  # Live albums should be skipped
    ]
    
    for input_text, expected in test_cases:
        record_type, year = parser._parse_record_info(input_text)
        assert (record_type, year) == expected