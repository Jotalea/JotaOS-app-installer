from http.server import SimpleHTTPRequestHandler, HTTPServer
from PyQt5.QtCore import QUrl
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from pathlib import Path
import json
import os
import random
import requests
import shutil
import stat
import sys
import tarfile
import threading
import time

packageName = "com.pystardust.ani-cli.jpkg"

InstallerAssets = {
    "iconurl": "assets/application.svg",
    "appsurl": "assets/folder-applications.svg",
    "fonturl": "assets/font.ttf",
    "altopts": {
        "iconurl": [
            "application.svg",
            "https://github.com/Jotalea/JotaOS-app-installer/"
        ],
        "appsurl": [
            "folder-applications.svg",
            "https://github.com/Jotalea/JotaOS-app-installer/"
        ],
        "fonturl": [
            "font.ttf",
            "https://github.com/Jotalea/JotaOS-app-installer/"
        ],
    }
}

with tarfile.open(packageName, 'r:xz') as archive:
    print("Files in the archive:")

    for member in archive.getmembers():
        print(member.name)

    if "app/metadata.json" in archive.getnames():
        extracted_file = archive.extractfile("app/metadata.json")
        if extracted_file is not None:
            file_contents = extracted_file.read().decode('utf-8')
            print("\nContents of the file:")
            AppData = json.loads(file_contents)
            print(AppData)
        else:
            print(f"Could not extract the file: app/metadata.json")
    else:
        print("File app/metadata.json not found in the archive.")

Port = random.randint(49152, 65535) # Choose a port to temporarily use

def installApp():
    global AppData
    print("App installation request received!")

    target_directory = Path.home() / ".local/share/jotaos/apps"
    target_directory.mkdir(parents=True, exist_ok=True)

    temp_directory = Path.home() / ".local/share/jotaos/temp"
    temp_directory.mkdir(parents=True, exist_ok=True)

    for file_name in AppData["appbins"]:
        if not file_name:
            # Fetch package
            requests.get(AppData["gitrepo"])

        with tarfile.open(packageName, 'r:xz') as tar:
            tar.extractall(path=f'{temp_directory}/{AppData["pkgname"]}')
        source_path = Path(str(temp_directory) + "/" + AppData["pkgname"] + "/app/" + file_name)
        destination_path = target_directory / source_path.name

        if source_path.exists():
            shutil.copy(source_path, destination_path)
            print(f"Copied {source_path} to {destination_path}")
        else:
            print(f"Source file {source_path} does not exist.")

    for file_name in AppData["appbins"]:
        destination_path = target_directory / Path(file_name).name
        if destination_path.exists():
            st = os.stat(destination_path)
            os.chmod(destination_path, st.st_mode | stat.S_IEXEC)
            print(f"Set executable permissions for {destination_path}")

    path_to_add = str(target_directory)
    path_line = f'export PATH="{path_to_add}:$PATH"\n'

    user_shell = os.environ.get("SHELL", "")
    if "bash" in user_shell:
        shell_config_path = Path.home() / ".bashrc"
    elif "zsh" in user_shell:
        shell_config_path = Path.home() / ".zshrc"
    else:
        shell_config_path = None
        print("Unsupported or unknown shell. Please add the directory to the PATH manually.")

    if shell_config_path:
        try:
            with open(shell_config_path, 'r') as f:
                lines = f.readlines()
                if any(path_to_add in line for line in lines):
                    print(f"{path_to_add} is already in the PATH.")
                    return
            
            with open(shell_config_path, 'a') as f:
                f.write(path_line)
                print(f"Added {path_to_add} to {shell_config_path}")
            
        except FileNotFoundError:
            with open(shell_config_path, 'w') as f:
                f.write(path_line)
                print(f"Created {shell_config_path} and added {path_to_add} to it.")

    try:
        shutil.rmtree(temp_directory)
        print(f"Successfully removed directory: {temp_directory}")
    except FileNotFoundError:
        print(f"Directory not found: {temp_directory}")
    except PermissionError:
        print(f"Permission denied: Unable to delete directory: {temp_directory}")
    except Exception as e:
        print(f"An error occurred while trying to delete the directory: {e}")

html_index = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Drag and Drop to Install</title>
    <style>
        @font-face {
            font-family: 'San Francisco Pro';
            src: url('[FONTURL]') format('truetype');
            font-weight: normal;
            font-style: normal;
        }

        body {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            background-color: #f0f0f5;
            margin: 0;
            font-family: 'San Francisco Pro', bold;
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
        }

        .container {
            display: none;
            justify-content: space-between;
            align-items: center;
            width: 75%;
        }

        .icon, .drop-zone {
            text-align: center;
            width: 100px;
            height: 140px;
            padding: 10px;
            border-radius: 10px;
            transition: background-color 0.3s;
        }

        .icon img, .drop-zone img {
            width: 100px;
            height: 100px;
        }

        .drop-zone {
            background-color: transparent;
        }

        .icon.dragging {
            opacity: 0.5;
        }

        .drop-zone.over {
            background-color: #e0e0e5;
        }

        .throbber {
            display: flex;
            justify-content: center;
            align-items: center;
            width: 50px;
            height: 50px;
            border: 4px solid #ccc;
            border-top: 4px solid #333;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div id="throbber" class="throbber"></div>

    <div class="container" id="main-content">
        <div id="app-icon" class="icon" draggable="true">
            <img src="[APPEXEC]" alt="App Icon">
            <p>[APPNAME]</p>
        </div>

        <div id="drop-zone" class="drop-zone">
            <img src="[APPSFOLDER]" alt="Applications Folder">
            <p>Applications</p>
        </div>
    </div>

    <script>
        window.addEventListener('load', () => {
            document.getElementById('throbber').style.display = 'none';
            document.getElementById('main-content').style.display = 'flex';
        });

        const appIcon = document.getElementById('app-icon');
        const dropZone = document.getElementById('drop-zone');
        
        appIcon.addEventListener('dragstart', (e) => {
            appIcon.classList.add('dragging');
            e.dataTransfer.setData('text/plain', 'app-icon');
        });

        appIcon.addEventListener('dragend', () => {
            appIcon.classList.remove('dragging');
        });

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('over');
        });

        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('over');
        });

        dropZone.addEventListener("drop", function(event) {
            event.preventDefault();
            dropZone.classList.remove("dragging");

            document.body.style.cursor = "wait";

            fetch("http://localhost:[PORT]/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"app": "install"})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    alert(data.message);
                } else {
                    alert("Error: " + data.message);
                }
            })
            .catch(error => {
                alert("An error occurred: " + error);
            })
            .finally(() => {
                document.body.style.cursor = "default";
            });

            fetch("http://localhost:[PORT]/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({"app": "exit"})
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === "success") {
                    alert(data.message);
                } else {
                    alert("Error: " + data.message);
                }
            })
            .catch(error => {
                alert("An error occurred: " + error);
            })
            .finally(() => {
                document.body.style.cursor = "default";
            });
        });
    </script>
</body>
</html>
"""
html_index = html_index.replace("[APPNAME]", AppData["appname"]).replace("[PORT]", str(Port)).replace("[APPSFOLDER]", InstallerAssets["appsurl"]).replace("[APPEXEC]", InstallerAssets["iconurl"]).replace("[FONTURL]", InstallerAssets["fonturl"])

class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/index.html" or self.path == "/":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html_index.encode('utf-8'))
        else:
            super().do_GET()

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data)
        except json.JSONDecodeError:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid JSON"}).encode())
            return

        if data.get("app") == "install":
            time.sleep(5)
            installApp()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "App Installed. Closing installer in 10 seconds."}).encode())
        elif data.get("app") == "exit":
            print("exit")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Exit"}).encode())
            time.sleep(10)
            os._exit(0)
        else:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": "Invalid request"}).encode())

def run_server():
    server_address = ('', Port)
    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    print(f"Starting server on port {Port}...")
    httpd.serve_forever()

class JotaleaWebView(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(JotaleaWebView, self).__init__(*args, **kwargs)
        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl(f"http://localhost:{Port}/"))
        self.setWindowTitle("App Installer")
        self.setCentralWidget(self.browser)
        self.resize(640, 360)

server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

app = QApplication([])
window = JotaleaWebView()
window.show()

sys.exit(app.exec_())