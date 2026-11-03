def test_config_loads():
    from assistant import config
    assert config.TOP_K > 0
    assert config.DISCLAIMER
