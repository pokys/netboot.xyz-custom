"""Exercise the real OSD downloader without curl, using a local HTTP fixture.

Only copies and edits the given function inside a fresh test directory; does not
install modules or touch an installed OSD module or any deployment disk.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import threading


def run(module_root, work):
    work.mkdir(parents=True, exist_ok=False)
    fixture = work / 'module' / 'Public' / 'Functions'
    fixture.mkdir(parents=True)
    shutil.copyfile(module_root / 'Public' / 'Functions' / 'Save-WebFile.ps1', fixture / 'Save-WebFile.ps1')

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != '/probe':
                self.send_error(404)
                return
            data = b'OSD-DOWNLOAD-REGRESSION-PASS'
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        subprocess.run([
            'powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(Path(__file__).resolve().parents[1] / 'scripts' / 'Test-OSDWebDownload.ps1'),
            '-ModuleRoot', str(work / 'module'),
            '-SourceUrl', f'http://127.0.0.1:{server.server_port}/probe',
            '-DestinationPath', str(work / 'downloads'),
        ], check=True, timeout=60)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('module_root', type=Path)
    parser.add_argument('--work-path', type=Path, default=Path('.build/osd-web-download-test'))
    args = parser.parse_args()
    run(args.module_root.resolve(), args.work_path.resolve())
