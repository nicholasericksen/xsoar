import os
import sys
import docker
import requests
import yaml
import json
import subprocess
import shutil
from cmd import Cmd



class XSOARShell(Cmd):
    def __init__(self, **kwargs):
        Cmd.__init__(self, **kwargs)
        self.prompt = "XSOAR:> "
    def do_quit(self, args):
        print("Exiting...")
        raise SystemExit
    def do_enable(self, args):
        """
        Enable an integration

        Run this command to enter and save the parameters required to 
        run an integration.
        Parameters will be prompted for.

        SAFE_MODE=true can be passed to require typing the file names
          for the config and code locations in case non standard 
          naming conventions are used.

        Example:
          XSOAR:> enable
        """
        SAFE_MODE = False
        if args:
            args = args.split(" ")
            command = args[0]
            dArgs = {}
            
            for arg in args:
                tmp = arg.split("=")
                k = tmp[0]
                v = tmp[1]

                if "," in v:
                    v = v.split(",")
                else:
                    v = tmp[1]
                dArgs[k] = v
            if 'SAFE_MODE' in dArgs and dArgs['SAFE_MODE'] == 'true':
                SAFE_MODE = True
        print("Which Pack should be enabled? ")
        pack = input()
        config_key = pack.lower()

        with open('config.json', 'r') as f:
            CONFIG = json.loads(f.read())
        if not config_key in CONFIG:
            path = f"Packs/{pack}/Integrations/"
            
            # SAFE_MODE if True assumes standard file naming conventions
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
                integration_path = f"{path}{pack}/"
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


            config = {
                "config": integration_config_path,
                "code": integration_code_path,
                "path": integration_path,
                "image_name": f"{config_key}-xsoar"
            }

            CONFIG[config_key] = config

            with open("config.json", "w") as f:
                f.write(json.dumps(CONFIG))

            with open(f"{integration_path}/demistomock_params.py", "w") as f:
                f.write(mock_param_code)

            # Copy CommonServerPython into integration directory
            shutil.copy('Packs/Base/Scripts/CommonServerPython/CommonServerPython.py', f"{integration_path}/")
            # Create blank CommonServerUserPython file in integration directory

        else:
            print("Already configured")

    def do_run(self, args):
        """
        Run the specified command

        Example:
          XSOAR:> run <pack> <command> <args>
          XSOAR:> run whois whois query=google.com
        """
        args = args.split(" ")
        pack = args[0]
        command = args[1]
        #docker_image = "demisto/ippysocks:1.0.0.11896"
        #command = "whois"
        dArgs = {}
        for arg in args[2:]:
            tmp = arg.split("=")
            k = tmp[0]
            v = tmp[1]
            if "," in v:
                v = v.split(",")
            else:
                v = tmp[1]
            dArgs[k] = v
        #= {"query": "google.com"}
        try:
            with open('config.json', 'r') as f:
                CONFIG = json.loads(f.read())
            CONFIG[pack]
        except:
            print("Command not configured yet. Try running 'enable' command first")


        with open(CONFIG[pack]["config"], "r") as stream:
            try:
                yml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)


        docker_image = yml["script"]["dockerimage"]



        mock_command_code = "def command():\n"
        mock_command_code += f"    return '{command}'\n"

        mock_args_code = "def args():\n"
        mock_args_code += f"    return {dArgs}\n"

        mock_results_code = "def results(results):\n"
        mock_results_code += f"    print(str(results['Contents']))\n"

        mock_results_code += "def error(results):\n"
        mock_results_code += f"    print(str(results))\n"
        mock_results_code += "def info(results):\n"
        mock_results_code += f"    print(str(results))\n"
        mock_results_code += "callingContext = {}\n"

        with open(f"{CONFIG[pack]['path']}/demistomock_params.py", "r") as f:
            mock_params_code = f.read()
        with open(f"{CONFIG[pack]['path']}/demistomock.py", "w") as f:
            f.write(mock_params_code)
            f.write(mock_command_code)
            f.write(mock_args_code)
            f.write(mock_results_code)
        client = docker.from_env()
        volume_path = os.getcwd() + '/' + CONFIG[pack]['path']
        volumes = {
            volume_path: {"bind": "/tmp", "mode": "ro"}
        }
        try:
            container = client.containers.get(container_id=CONFIG[pack]['image_name'])
        except Exception:
            container = None
        if not container:
            container = client.containers.run(docker_image, tty=True, detach=True, name=CONFIG[pack]['image_name'], auto_remove=True, volumes=volumes)
        execute = subprocess.check_output(['docker', 'exec', CONFIG[pack]['image_name'], "/usr/local/bin/python", f"/tmp/{CONFIG[pack]['code'].split('/')[-1]}"], universal_newlines=True)
        print(execute)
        #raw = json.loads(execute.replace("'", "\""))
        #print(execute.replace("\",", "\n").replace("{", "\n").replace("}", "").replace("\\n", "\n").replace("[", "\n").replace("]", "\n").replace(", \"", "\n").replace("\"","").replace("\',","\n"))
        #for data in raw: 
        #md = json_to_report(raw[0])
        #print(md)

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
