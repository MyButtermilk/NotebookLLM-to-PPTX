#!/usr/bin/env python3
"""
SlideRefactor - Cross-Platform Launcher

This script automatically installs dependencies and starts both
the backend and frontend servers.

Usage:
    python launcher.py
"""

import os
import sys
import subprocess
import time
import webbrowser
import platform
from pathlib import Path
from typing import Optional

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a colored header."""
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}{text}{Colors.ENDC}")

def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def check_command(command: str) -> bool:
    """Check if a command is available in PATH."""
    try:
        use_shell = platform.system() == "Windows"
        subprocess.run(
            [command, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            shell=use_shell
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def run_command(command: list, cwd: Optional[Path] = None, quiet: bool = True) -> bool:
    """Run a command and return success status."""
    try:
        use_shell = platform.system() == "Windows"
        if quiet:
            subprocess.run(
                command,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                shell=use_shell
            )
        else:
            subprocess.run(command, cwd=cwd, check=True, shell=use_shell)
        return True
    except subprocess.CalledProcessError:
        return False

def check_prerequisites():
    """Check if Python and Node.js are installed."""
    print_header("Checking prerequisites...")

    # Check Python
    print("Checking Python installation...", end=" ")
    if not check_command("python"):
        print_error("Python is not installed or not in PATH")
        print_info("Please install Python 3.9+ from https://www.python.org/downloads/")
        sys.exit(1)
    python_version = subprocess.check_output(["python", "--version"]).decode().strip()
    print_success(f"{python_version} found!")

    # Check Node.js
    print("Checking Node.js installation...", end=" ")
    if not check_command("node"):
        print_error("Node.js is not installed or not in PATH")
        print_info("Please install Node.js 18+ from https://nodejs.org/")
        sys.exit(1)
    node_version = subprocess.check_output(["node", "--version"]).decode().strip()
    print_success(f"Node.js {node_version} found!")

    # Check npm
    if not check_command("npm"):
        print_error("npm is not installed")
        print_info("Please reinstall Node.js from https://nodejs.org/")
        sys.exit(1)

def install_python_dependencies():
    """Install Python dependencies."""
    print_header("Installing Python dependencies...")
    print_info("This may take a few minutes on first run...")

    # Install core dependencies
    print("Installing core dependencies...", end=" ", flush=True)
    if not run_command(["pip", "install", "-r", "requirements.txt", "--quiet"]):
        print_error("Failed to install core dependencies")
        sys.exit(1)
    print_success("Done!")

    # Install server dependencies
    print("Installing server dependencies...", end=" ", flush=True)
    if not run_command(["pip", "install", "-r", "server/requirements.txt", "--quiet"]):
        print_error("Failed to install server dependencies")
        sys.exit(1)
    print_success("Done!")

def install_node_dependencies():
    """Install Node.js dependencies."""
    print_header("Installing Node.js dependencies...")

    frontend_dir = Path("frontend")
    node_modules = frontend_dir / "node_modules"

    if not node_modules.exists():
        print_info("This may take a few minutes on first run...")
        print("Installing frontend dependencies...", end=" ", flush=True)
        if not run_command(["npm", "install", "--silent"], cwd=frontend_dir):
            print_error("Failed to install Node.js dependencies")
            sys.exit(1)
        print_success("Done!")
    else:
        print_success("Dependencies already installed, skipping...")

def check_configuration():
    """Check if .env file exists and has API keys."""
    print_header("Checking configuration...")

    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists():
        print_warning(".env file not found!")
        print_info("Creating .env from template...")
        env_file.write_text(env_example.read_text())
        print()
        print_warning("IMPORTANT: Please edit .env and add your API keys:")
        print_info("  - DATALAB_API_KEY (for PDF extraction)")
        print_info("  - GEMINI_API_KEY (for AI processing)")
        print()

        # Try to open in default editor
        if platform.system() == "Windows":
            os.system(f"notepad {env_file}")
        elif platform.system() == "Darwin":  # macOS
            os.system(f"open -e {env_file}")
        else:  # Linux
            os.system(f"${EDITOR:-nano} {env_file}")

        input("After adding your API keys, press Enter to continue...")
        print()

    print_success("Configuration OK!")

def cleanup_old_instances():
    """Clean up old instances running on our ports."""
    print_header("Checking for old instances...")
    
    ports = [8000, 3001]
    system = platform.system()
    
    for port in ports:
        try:
            if system == "Windows":
                # Find PID using netstat
                # Filter by port and typical listening indicators (0.0.0.0 or [::]) to be language-independent
                cmd = f'netstat -aon | findstr :{port}'
                output = subprocess.check_output(cmd, shell=True).decode()
                for line in output.splitlines():
                    # We look for lines containing 0.0.0.0:PORT or [::]:PORT which are standard for listening sockets
                    if f":{port}" in line and ("0.0.0.0" in line or "[::]" in line or "127.0.0.1" in line):
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            if pid != "0":
                                print(f"  Closing old process {pid} on port {port}...")
                                subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # Unix/Mac
                # lsof -ti:PORT returns the PID
                try:
                    pids = subprocess.check_output(["lsof", "-t", f"-i:{port}"], stderr=subprocess.DEVNULL).decode().split()
                    for pid in pids:
                        if pid:
                            print(f"  Closing old process {pid} on port {port}...")
                            subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # lsof not found or no process on port
                    pass
        except Exception:
            pass
    
    print_success("Port cleanup complete!")

def start_servers():
    """Start backend and frontend servers."""
    print_header("Starting SlideRefactor...")
    print()
    print_info("Backend server: http://localhost:8000")
    print_info("Frontend UI:    http://localhost:3001")
    print()
    print_warning("Press Ctrl+C to stop both servers")
    print()

    # Start backend
    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "server.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000"
    ]

    print("Starting backend server...")
    backend_process = subprocess.Popen(
        backend_cmd,
        cwd=None,  # Run from project root
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Wait for backend to start
    print("Waiting for backend to start...", end=" ", flush=True)
    time.sleep(5)
    print_success("Backend running!")

    # Start frontend
    frontend_cmd = ["npm", "run", "dev"]

    print("Starting frontend server...")
    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd="frontend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=(platform.system() == "Windows")
    )

    # Wait for frontend to start
    print("Waiting for frontend to start...", end=" ", flush=True)
    time.sleep(8)
    print_success("Frontend running!")

    # Open browser
    print("Opening browser...")
    webbrowser.open("http://localhost:3001")

    print()
    print_header("=" * 50)
    print_success("SlideRefactor is now running!")
    print_header("=" * 50)
    print()
    print_info("Backend:  http://localhost:8000")
    print_info("Frontend: http://localhost:3001")
    print()
    print_warning("Press Ctrl+C to stop both servers")
    print()

    # Keep servers running
    try:
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print()
        print_warning("Shutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print_success("Servers stopped!")

def main():
    """Main launcher function."""
    print()
    print_header("=" * 50)
    print_header("  SlideRefactor - One-Click Launcher")
    print_header("=" * 50)

    try:
        check_prerequisites()
        install_python_dependencies()
        install_node_dependencies()
        check_configuration()
        cleanup_old_instances()
        start_servers()
    except KeyboardInterrupt:
        print()
        print_warning("Launcher interrupted by user")
        sys.exit(0)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
