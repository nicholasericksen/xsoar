import ast
import demisto_client
from demisto_sdk.commands.common.tools import print_error
import logging
import sys
import coloredlogs
import os
from HTMLLogger import HTMLFileHandler

ARTIFACTS_PATH = os.environ.get('CIRCLE_ARTIFACTS')


def update_server_configuration(client, server_configuration, error_msg):
    """updates server configuration

    Args:
        client (demisto_client): The configured client to use.
        server_configuration (dict): The server configuration to be added
        error_msg (str): The error message

    Returns:
        response_data: The response data
        status_code: The response status code
    """
    system_conf_response = demisto_client.generic_request_func(
        self=client,
        path='/system/config',
        method='GET'
    )
    system_conf = ast.literal_eval(system_conf_response[0]).get('sysConf', {})
    system_conf.update(server_configuration)
    data = {
        'data': system_conf,
        'version': -1
    }
    response_data, status_code, _ = demisto_client.generic_request_func(self=client, path='/system/config',
                                                                        method='POST', body=data)

    try:
        result_object = ast.literal_eval(response_data)
    except ValueError as err:
        print_error('failed to parse response from demisto. response is {}.\nError:\n{}'.format(response_data, err))
        return

    if status_code >= 300 or status_code < 200:
        message = result_object.get('message', '')
        msg = f'{error_msg} {status_code}\n{message}'
        print_error(msg)
    return response_data, status_code


def install_logging(log_file_name: str) -> None:
    """
    This method install the logging mechanism so that info level logs will be sent to the console and debug level logs
    will be sent to the log_file_name only.
    Args:
        log_file_name: The name of the file in which the debug logs will be saved
    """
    formatter = coloredlogs.ColoredFormatter(fmt='[%(asctime)s] - [%(threadName)s] - [%(levelname)s] - %(message)s',
                                             level_styles={
                                                 'critical': {'bold': True, 'color': 'red'},
                                                 'debug': {'color': 'cyan'},
                                                 'error': {'color': 'red'},
                                                 'info': {},
                                                 'warning': {'color': 'yellow'}})
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    fh = HTMLFileHandler(f'{ARTIFACTS_PATH}/logs/{log_file_name}')
    fh.setFormatter(formatter)
    ch.setLevel(logging.INFO)
    fh.setLevel(logging.DEBUG)
    logging.basicConfig(level=logging.DEBUG,
                        handlers=[ch, fh])
