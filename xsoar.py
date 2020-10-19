import os
import sys
import docker
import requests
import yaml
import subprocess
from cmd import Cmd

class XSOARShell(Cmd):
    def __init__(self, **kwargs):
        Cmd.__init__(self, **kwargs)
        self.prompt = "XSOAR:> "
    def do_quit(self, args):
        print("Exiting...")
        raise SystemExit
    def do_enable(self, args):
        print("Which integration should be enabled? ")
        pack = input()
        path = f"Packs/{pack}/Integrations/"
        
        # SAFE_MODE if True assumes standard file naming conventions
        SAFE_MODE = False
        if SAFE_MODE:
            print(os.listdir(path))
            integration = input("Name of the integration: ")
            integration_path = path + integration
            print(os.listdir(integration_path))
            integration_code = input("Name of integration code file: ") 
            integration_config = input("Name of integration config file: ")

            integration_code_path = integration_path + '/' + integration_code
            integration_config_path = integration_path + '/' + integration_config
        else:
            integration_code_path = f"{path}{pack}/{pack}.py"
            integration_config_path = f"{path}{pack}/{pack}.yml"
        with open(integration_config_path, "r") as stream:
            try:
                yml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        print(yml["configuration"])
        params = {}
        print("Enter integration parameters: \n")
        for param in yml["configuration"]:
            params[param['name']] = input(f"{param['name']}: ")
        print(params)
        
        mock_param_code = "def params():\n"
        mock_param_code += f"    return {params}\n"    

        with open("Packs/Whois/Integrations/Whois/demistomock_whois_params.py", "w") as f:
            f.write(mock_param_code)

    def do_run(self, args):
        docker_image = "demisto/ippysocks:1.0.0.11896"
        command = "whois"
        args = {"query": "google.com"}
        
        mock_command_code = "def command():\n"
        mock_command_code += f"    return '{command}'\n"

        mock_args_code = "def args():\n"
        mock_args_code += f"    return {args}\n"

        mock_results_code = "def results(results):\n"
        mock_results_code += f"    print(str(results['Contents']))\n"

        with open("Packs/Whois/Integrations/Whois/demistomock_whois_params.py", "r") as f:
            mock_params_code = f.read()
        with open("Packs/Whois/Integrations/Whois/demistomock.py", "w") as f:
            f.write(mock_params_code)
            f.write(mock_command_code)
            f.write(mock_args_code)
            f.write(mock_results_code)
        client = docker.from_env()
        volumes = {
            "/home/pnl/Documents/dev/xsoar/Packs/Whois/Integrations/Whois/": {"bind": "/tmp", "mode": "ro"}
        }

        container = client.containers.run(docker_image, tty=True, detach=True, name="whois-xsoar", auto_remove=True, volumes=volumes)
        execute = subprocess.check_output(['docker', 'exec', 'whois-xsoar', "/usr/local/bin/python", "/tmp/Whois.py"], universal_newlines=True)
        print(execute)
        """
        exit_code, logs = container.exec_run("/usr/local/bin/python /tmp/Whois.py", stream=True)
        for log in logs:
            print(log)
        container.stop()
        """
if __name__ == '__main__':
    shell = XSOARShell()

    description = "XSOAR CLI utility"

    shell.cmdloop(intro=description)
