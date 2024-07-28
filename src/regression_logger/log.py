import logging
import logging.config
import json
import pathlib

# Global logs
LOG_HEADER = logging.getLogger('header_log')
LOG_LVL_1 = logging.getLogger('log_level_1')
LOG_LVL_2 = logging.getLogger('log_level_2')
LOG_LVL_3 = logging.getLogger('log_level_3')


def init_logs(log_path: str):
    config_file = pathlib.Path('src', 'regression_logger', 'config.json')
    with open(config_file) as f_in:
        config = json.load(f_in)

    for key, val in config['handlers'].items():
        if 'filename' in val.keys():
            config['handlers'][key]['filename'] = log_path

    logging.config.dictConfig(config=config)


def close_logs():
    LOG_HEADER.handlers.clear()
    LOG_LVL_1.handlers.clear()
    LOG_LVL_2.handlers.clear()
    LOG_LVL_3.handlers.clear()