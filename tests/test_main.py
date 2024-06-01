import time
import pytest
import requests
from multiprocessing import Process
from app.main import app, active_request_count
import os


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client


def test_setup(client):
    assert active_request_count == 0


def test_folder_name_missing(client):
    response = client.post('/list_files', json={})
    assert response.status_code == 400
    assert response.get_json()['error'] == 'Folder name missing'


def test_folder_not_exist(client):
    response = client.post('/list_files', json={'folder': 'folder_name_does_not_exist'})
    assert response.status_code == 404
    assert response.get_json()['error'] == 'Requested folder does not exist'


def test_folder_no_permission(client, tmp_path):
    tmp_path_str = str(tmp_path)
    folder = os.path.join(tmp_path_str, 'no_permission_folder')
    os.mkdir(folder)
    os.chmod(folder, 0o000)
    response = client.post('/list_files', json={'folder': folder})
    assert response.status_code == 403
    assert response.get_json()['error'] == 'No permission to read the requested folder'


def test_list_files_success(client, tmp_path):
    folder = tmp_path / 'test_folder'
    folder.mkdir()
    (folder / 'file1.txt').write_text('This is a test')
    (folder / 'file2.log').write_text('This is a test log')
    response = client.post('/list_files', json={'folder': str(folder)})
    assert response.status_code == 200
    files = response.get_json()['files']
    assert 'file1.txt' in files
    assert 'file2.log' in files


def test_list_files_with_filter(client, tmp_path):
    folder = tmp_path / "test_folder"
    folder.mkdir()
    (folder / 'file1.txt').write_text('This is a test')
    (folder / 'file2.log').write_text('This is a test log')
    response = client.post('/list_files', json={'folder': str(folder), 'filter': '*.txt'})
    assert response.status_code == 200
    files = response.get_json()['files']
    assert 'file1.txt' in files
    assert 'file2.log' not in files


def run_server():
    app.run(port=8000)


def send_shutdown_request():
    try:
        requests.post('http://127.0.0.1:8000/shutdown')
    except requests.ConnectionError as e:
        print(f"Failed to send shutdown request: {e}")


def send_requests(num_requests):
    for _ in range(num_requests):
        try:
            response = requests.post('http://127.0.0.1:8000/list_files', json={'folder': '.'})
            print(f"Request status code: {response.status_code}")
            print(response.json())
        except requests.ConnectionError as e:
            print(f"Failed to send request: {e}")


def test_graceful_shutdown(client, num_requests=5):
    # Start the server process
    server_process = Process(target=run_server)
    server_process.start()
    time.sleep(5)  # Give the server more time to start

    # Start the request processes
    requests_process = Process(target=send_requests, args=(num_requests,))
    requests_process.start()
    time.sleep(10)  # Allow all requests to be sent before shutdown

    shutdown_process = Process(target=send_shutdown_request)
    shutdown_process.start()

    # Wait for the processes to finish
    requests_process.join()
    shutdown_process.join()

    # Stop the server process
    server_process.terminate()
    server_process.join()

    # Check that all requests were handled correctly
    assert requests_process.exitcode == 0
