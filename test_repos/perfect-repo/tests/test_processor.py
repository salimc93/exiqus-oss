import pytest
from src.processor import DataProcessor


class TestDataProcessor:
    def test_initialization(self):
        processor = DataProcessor()
        assert processor.config == {}

    def test_transform(self):
        processor = DataProcessor()
        data = {"key": "value"}
        result = processor.transform(data)
        assert result == data

    def test_with_config(self):
        config = {"option": True}
        processor = DataProcessor(config)
        assert processor.config == config

    def test_error_handling(self):
        processor = DataProcessor()
        with pytest.raises(TypeError):
            processor.transform(None)
