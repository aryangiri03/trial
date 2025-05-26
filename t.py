import json
import os
import sys
import subprocess
import pexpect
from pathlib import Path
import platform

class ProjectSetup:
    def __init__(self, config_path):
        self.config = self._load_config(config_path)
        self.project_dir = Path(self.config.get('project_name', 'my-app')).resolve()
        self.error_log = self.project_dir / "setup_errors.log"
        self.os_type = platform.system().lower()
        self.venv_path = self.project_dir / "venv"
        
        # OS-specific configurations
        self.pip_path = self.venv_path / ("Scripts/pip.exe" if self.os_type == "windows" else "bin/pip")
        self.python_path = self.venv_path / ("Scripts/python.exe" if self.os_type == "windows" else "bin/python")

    def _load_config(self, config_path):
        with open(config_path) as f:
            return json.load(f)

    def _log_error(self, message):
        self.error_log.parent.mkdir(parents=True, exist_ok=True)
        with open(self.error_log, 'a') as f:
            f.write(f"ERROR: {message}\n")

    def _run_interactive(self, command, cwd=None):
        try:
            child = pexpect.spawn(
                command,
                cwd=str(cwd) if cwd else None,
                encoding='utf-8',
                timeout=300
            )
            child.logfile = sys.stdout
            child.expect(pexpect.EOF)
            child.close()
            return child.exitstatus == 0
        except Exception as e:
            self._log_error(f"Command failed: {command}\nError: {str(e)}")
            return False

    def _check_dependencies(self):
        required = {
            'node': ['node', '--version'],
            'npm': ['npm', '--version'],
            'python': ['python', '--version']
        }
        
        print("\n🔍 Checking system dependencies:")
        missing = []
        for name, cmd in required.items():
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"✓ {name} installed")
            except (subprocess.CalledProcessError, FileNotFoundError):
                missing.append(name)
                print(f"❌ {name} missing")
        
        if missing:
            print(f"\n🚨 Missing required dependencies: {', '.join(missing)}")
            print("Please install them before proceeding")
            sys.exit(1)

    def setup_project(self):
        try:
            self._check_dependencies()
            self._create_project()
            self._merge_files()
            self._install_dependencies()
            return self._start_application()
        except Exception as e:
            self._log_error(f"Critical error: {str(e)}")
            return False

    def _create_project(self):
        print(f"\n🚀 Creating {self.config['project_type']} project...")
        if self.config['project_type'] == "React":
            cmd = f"npm create vite@latest {self.project_dir} -- --template react"
            return self._run_interactive(cmd, cwd=Path.cwd())
        return False

    def _merge_files(self):
        print("\n📂 Merging custom files...")
        self.project_dir.mkdir(parents=True, exist_ok=True)
        for rel_path, content in self.config['files'].items():
            full_path = self.project_dir / rel_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
            print(f"✓ Updated {rel_path}")

    def _install_dependencies(self):
        print("\n🔧 Installing dependencies...")
        if not self.config.get('dependencies'):
            return True

        cmd = f"npm install {' '.join(self.config['dependencies'])}"
        return self._run_interactive(cmd, cwd=self.project_dir)

    def _start_application(self):
        print("\n⚡ Starting application...")
        if self.config['project_type'] in ["React", "Vite"]:
            child = pexpect.spawn(
                "npm run dev",
                cwd=str(self.project_dir),
                encoding='utf-8'
            )
            
            try:
                child.expect('Local:\s+(http://[^\s]+)', timeout=60)
                url = child.match.group(1)
                print(f"\n🎉 Application running at: {url}")
                print("Press Ctrl+C to stop the server")
                child.interact()
            except pexpect.TIMEOUT:
                print("\n⚠️  Failed to detect URL, check output manually")
                child.interact()
            return True
        return False

if __name__ == "__main__":
    if not Path("input.txt").exists():
        print("Error: input.txt not found")
        sys.exit(1)

    try:
        setup = ProjectSetup("input.txt")
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
