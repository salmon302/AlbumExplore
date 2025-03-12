import pytest
import pandas as pd
import json
import logging
from pathlib import Path
from albumexplore.data.preprocessing.progarchives_preprocessor import save_data, main, setup_arg_parser

@pytest.fixture
def sample_dataframe():
    return pd.DataFrame({
        'title': ['Album 1', 'Album 2'],
        'artist': ['Artist 1', 'Artist 2'],
        'genre': ['Progressive Metal', 'Progressive Rock'],
        'record_type': ['Studio', 'EP'],
        'year': [2023, 2024],
        'rating': [4.5, 4.0]
    })

@pytest.fixture
def sample_html_directory(tmp_path):
    # Create sample HTML files
    html_content = """
    <html>
        <body>
            <h1 class="album-title">Test Album</h1>
            <div class="artist-name">Test Artist</div>
            <div class="genre">Progressive Rock</div>
            <div class="album-info">Studio Album, 2024</div>
            <div class="rating">4.5</div>
        </body>
    </html>
    """
    html_dir = tmp_path / "html_files"
    html_dir.mkdir()
    (html_dir / "album1.html").write_text(html_content)
    return html_dir

def test_save_data_csv(tmp_path, sample_dataframe):
    output_file = tmp_path / "test_output.csv"
    save_data(sample_dataframe, str(output_file))
    
    # Read back and verify
    df = pd.read_csv(output_file)
    assert len(df) == 2
    assert list(df.columns) == ['title', 'artist', 'genre', 'record_type', 'year', 'rating']
    assert df['title'].tolist() == ['Album 1', 'Album 2']

def test_save_data_json(tmp_path, sample_dataframe):
    output_file = tmp_path / "test_output.json"
    save_data(sample_dataframe, str(output_file))
    
    # Read back and verify
    with open(output_file) as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]['title'] == 'Album 1'
    assert data[1]['title'] == 'Album 2'

def test_save_data_xlsx(tmp_path, sample_dataframe):
    output_file = tmp_path / "test_output.xlsx"
    save_data(sample_dataframe, str(output_file))
    
    # Read back and verify
    df = pd.read_excel(output_file)
    assert len(df) == 2
    assert list(df.columns) == ['title', 'artist', 'genre', 'record_type', 'year', 'rating']
    assert df['genre'].tolist() == ['Progressive Metal', 'Progressive Rock']

def test_save_data_invalid_format(tmp_path, sample_dataframe):
    output_file = tmp_path / "test_output.invalid"
    with pytest.raises(ValueError, match="Unsupported file format"):
        save_data(sample_dataframe, str(output_file))

def test_save_data_permission_error(tmp_path, sample_dataframe, monkeypatch):
    output_file = tmp_path / "test_output.csv"
    
    def mock_to_csv(*args, **kwargs):
        raise PermissionError("Permission denied")
    
    monkeypatch.setattr(pd.DataFrame, "to_csv", mock_to_csv)
    
    with pytest.raises(Exception):
        save_data(sample_dataframe, str(output_file))

def test_main_successful_run(tmp_path, sample_html_directory, capsys):
    output_file = tmp_path / "output.json"
    parser = setup_arg_parser()
    args = parser.parse_args([
        '--input-dir', str(sample_html_directory),
        '--output-file', str(output_file)
    ])
    
    main(args)
    
    assert output_file.exists()
    
    # Load and verify saved data
    with open(output_file) as f:
        data = json.load(f)
    assert len(data) > 0
    assert data[0]['title'] == 'Test Album'
    assert data[0]['genre'] == 'Progressive Rock'

def test_main_invalid_input_dir(tmp_path):
    nonexistent_dir = tmp_path / "nonexistent"
    output_file = tmp_path / "output.json"
    parser = setup_arg_parser()
    args = parser.parse_args([
        '--input-dir', str(nonexistent_dir),
        '--output-file', str(output_file)
    ])
    
    with pytest.raises(SystemExit):
        main(args)

def test_argument_parser():
    parser = setup_arg_parser()
    args = parser.parse_args(['--input-dir', 'input', '--output-file', 'output.csv'])
    
    assert args.input_dir == 'input'
    assert args.output_file == 'output.csv'

def test_argument_parser_missing_args():
    parser = setup_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(['--input-dir', 'input'])