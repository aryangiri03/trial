import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

class ProjectSetup:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.project_dir = Path(self.config.get('project_name', 'my-app'))
        self.error_log = Path("setup_errors.log")
        self.server_process = None
        self.install_success = False
        self.template_commands = {
            "React": f"npm create vite@latest {self.project_dir} -- --template react",
            "Vite": f"npm create vite@latest {self.project_dir} -- --template react-ts",
            "Flask": f"python -m venv {self.project_dir}/venv",
            "Express": f"npm init -y"
        }

    def _load_config(self, config_path):
        with open(config_path) as f:
            return json.load(f)

    def _run_command(self, command, cwd=None):
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            return process
        except Exception as e:
            self._log_error(f"Command failed: {command}\nError: {str(e)}")
            return None

    def _log_error(self, message):
        try:
            with open(self.error_log, 'a') as f:
                f.write(f"ERROR: {message}\n")
        except Exception as e:
            print(f"Failed to write error log: {str(e)}", file=sys.stderr)

    def _monitor_process(self, process, success_message=None):
        output_buffer = []
        while True:
            output = process.stdout.readline()
            if output:
                output_buffer.append(output.strip())
                print(output.strip())
            if process.poll() is not None:
                remaining = process.stdout.read()
                if remaining:
                    print(remaining.strip())
                    output_buffer.append(remaining.strip())
                break
            time.sleep(0.1)
       
        success = process.returncode == 0
        if success and success_message:
            print(f"\n✅ {success_message}")
        return success, '\n'.join(output_buffer)

    def setup_project(self):
        try:
            if not self._create_template():
                return False

            self._merge_files()
            if not self._install_dependencies():
                return False

            return self._start_application()
        except Exception as e:
            self._log_error(f"Critical error: {str(e)}")
            return False

    def _create_template(self):
        print(f"🚀 Creating {self.config['project_type']} project...")
        cmd = self.template_commands.get(self.config['project_type'])
        if not cmd:
            return False

        process = self._run_command(cmd, cwd=Path.cwd())
        if process:
            return self._monitor_process(process, "Project template created")[0]
        return False

    def _merge_files(self):
        print("\n📂 Merging custom files...")
        self.project_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, content in self.config['files'].items():
            full_path = self.project_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            decoded_content = content.encode('utf-8').decode('unicode_escape')
            formatted_content = decoded_content.replace(';', ';\n')
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            print(f"✓ Updated {rel_path}")

    def _install_dependencies(self):
        print("\n🔧 Installing dependencies...")
        if not self.config.get('dependencies'):
            return True

        if self.config['project_type'] == "Flask":
            cmd = f"{self.project_dir}/venv/Scripts/pip install"
        else:
            cmd = "npm install"

        full_cmd = f"{cmd} {' '.join(self.config['dependencies'])}"
        process = self._run_command(full_cmd, cwd=self.project_dir)
       
        if process:
            spinner = threading.Event()
            spinner_thread = threading.Thread(target=self._show_spinner, args=(spinner,))
            spinner_thread.start()

            success, output = self._monitor_process(process)
            spinner.set()
            spinner_thread.join()

            if "http://" in output:
                print(f"\n🎉 Application running at: {output.split('http://')[-1].split()[0]}")
            return success
           
        return False

    def _show_spinner(self, stop_event):
        chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        while not stop_event.is_set():
            print(f"\rInstalling... {chars[i % len(chars)]}", end="")
            time.sleep(0.1)
            i += 1
        print("\r" + " " * 30 + "\r", end="")

    def _start_application(self):
        print("\n⚡ Starting application...")
        if self.config['project_type'] == "Flask":
            cmd = f"{self.project_dir}/venv/Scripts/python -m flask run"
        elif self.config['project_type'] in ["React", "Vite"]:
            cmd = "npm run dev"
        else:
            cmd = "node index.js"

        self.server_process = self._run_command(cmd, cwd=self.project_dir)
        if not self.server_process:
            return False

        def monitor_output():
            while True:
                output = self.server_process.stdout.readline()
                if output:
                    print(output.strip())
                    if "http://" in output:
                        print(f"\n🎉 Application running at: {output.strip()}")
                if self.server_process.poll() is not None:
                    break

        threading.Thread(target=monitor_output, daemon=True).start()

        print("\nPress Ctrl+C to stop the server...")
        try:
            while self.server_process.poll() is None:
                time.sleep(1)
        except KeyboardInterrupt:
            self.server_process.terminate()
            print("\nServer stopped")

        return True

if __name__ == "__main__":
    config_path = r"C:\Users\Asus\Downloads\file-generatorv4\Mcp_server _prathamesh\input.txt"
    if not Path(config_path).exists():
        print("Error: input.txt not found")
        sys.exit(1)

    try:
        setup = ProjectSetup(config_path)
        if setup.setup_project():
            print("\n✅ Setup completed successfully!")
            print(f"Project directory: {setup.project_dir}")
        else:
            print("\n❌ Setup failed. Check error logs:")
            print(f"-> {setup.error_log}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
