import json
import re
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

class ProjectSetup:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.project_dir = self._get_project_name()
        self.error_log = self.project_dir / "setup_errors.log"
        self.server_process = None
        self.url_opened = False
        self.template_commands = {
            "React": ["npm", "create", "vite@latest", str(self.project_dir), "--", "--template", "react"]
        }

    def _get_project_name(self):
        default_name = self.config.get('project_name', 'my-app')
        name = input(f"Enter project name [{default_name}]: ").strip()
        return Path(name if name else default_name)

    def _load_config(self, config_path):
        with open(config_path) as f:
            return json.load(f)

    def _run_command(self, command, cwd=None):
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            return process
        except Exception as e:
            self._log_error(f"Command failed: {' '.join(command)}\nError: {str(e)}")
            return None

    def _log_error(self, message):
        self.error_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.error_log, 'a') as f:
            f.write(f"ERROR: {message}\n")

    def _monitor_process(self, process, success_message=None):
        output_buffer = []
        while True:
            output = process.stdout.readline()
            if output:
                clean_output = output.strip()
                output_buffer.append(clean_output)
                print(clean_output)
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

            print("\n✅ Setup completed successfully!")
            print(f"Project directory: {self.project_dir}")
            return self._start_application()
        except Exception as e:
            self._log_error(f"Critical error: {str(e)}")
            return False

    def _create_template(self):
        print(f"\n🚀 Creating {self.config['project_type']} project...")
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
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content.replace(';', ';\n'))
            print(f"✓ Updated {rel_path}")

    def _install_dependencies(self):
        print("\n🔧 Installing dependencies...")
        if not self.config.get('dependencies'):
            return True

        if (self.project_dir / "node_modules").exists():
            print("✓ Dependencies already installed")
            return True

        cmd = ["npm", "install", "--legacy-peer-deps"]
        process = self._run_command(cmd + self.config['dependencies'], cwd=self.project_dir)
        
        if process:
            success, _ = self._monitor_process(process, "Dependencies installed")
            return success
        return False

    def _start_application(self):
        print("\n⚡ Starting application...")
        cmd = ["npm", "run", "dev"]
        self.server_process = self._run_command(cmd, cwd=self.project_dir)
        
        if not self.server_process:
            return False

        threading.Thread(target=self._monitor_server_output, daemon=True).start()
        print("\nPress Ctrl+C to stop the server...")

        try:
            self.server_process.wait()
        except KeyboardInterrupt:
            self.server_process.terminate()
            print("\n🛑 Server stopped")
        
        return True

    def _monitor_server_output(self):
        url_pattern = re.compile(r'(Local|Network):\s+(https?://\S+)')
        while True:
            output = self.server_process.stdout.readline()
            if output:
                print(output.strip())
                if not self.url_opened:
                    match = url_pattern.search(output)
                    if match:
                        url = match.group(2)
                        print(f"\n🌐 Opening {url} in browser...")
                        webbrowser.open(url)
                        self.url_opened = True
            if self.server_process.poll() is not None:
                break

if __name__ == "__main__":
    if not Path("input.txt").exists():
        print("Error: input.txt not found")
        sys.exit(1)

    try:
        setup = ProjectSetup("input.txt")
        if setup.setup_project():
            sys.exit(0)
        else:
            print("\n❌ Setup failed. Check error logs:")
            print(f"-> {setup.error_log}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ Operation cancelled by user")
        sys.exit(1)
