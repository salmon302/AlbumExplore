import pytest
from pathlib import Path
from albumexplore.data.parsers.html_parser import ProgArchivesParser

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
def tmp_html_file(tmp_path, sample_html):
    html_file = tmp_path / "test_album.html"
    html_file.write_text(sample_html)
    return html_file

def test_parse_album(sample_html):
    parser = ProgArchivesParser(Path("."))
    result = parser.parse_album(sample_html)
    
    assert result["title"] == "Sample Album"
    assert result["artist"] == "Test Artist"
    assert result["genre"] == "Progressive Metal"
    assert result["rating"] == 4.5

def test_parse_directory(tmp_path, tmp_html_file):
    parser = ProgArchivesParser(tmp_path)
    df = parser.parse_directory()
    
    assert len(df) == 1
    assert df.iloc[0]["title"] == "Sample Album"
    assert df.iloc[0]["artist"] == "Test Artist"

def test_invalid_html():
    parser = ProgArchivesParser(Path("."))
    result = parser.parse_album("<invalid>html</invalid>")
    
    # Should return dictionary with None values rather than failing
    assert all(v is None for v in result.values())