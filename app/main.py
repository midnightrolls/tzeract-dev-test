from flask import Flask, request, jsonify
import time
import signal
import os
import fnmatch
import threading

app = Flask(__name__)
active_request_count = 0
shutdown_event = threading.Event()
shutdown_requested = False


# Before each request, check if shutdown event is set
@app.before_request
def before_request():
    global active_request_count
    # If shutdown event is set, return 503 error
    if shutdown_event.is_set():
        return jsonify({'error': 'Server shutting down...'}), 503
    active_request_count += 1


def shutdown_server():
    global active_request_count
    # Wait until all active requests are handled
    while active_request_count > 0:
        time.sleep(1)
    os._exit(0)


# Set shutdown function to be called on SIGINT
signal.signal(signal.SIGINT, lambda signum, frame: shutdown_server())


@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Set shutdown event and start a new thread to shutdown the server
    response = jsonify({'message': 'Server shutting down...'}), 200
    shutdown_event.set()
    threading.Thread(target=shutdown_server).start()
    return response


# After each request, decrement active request count
@app.after_request
def after_request(response):
    global active_request_count
    active_request_count -= 1
    # If shutdown event is set and there are no more active requests, clear the shutdown event
    if shutdown_event.is_set() and active_request_count == 0:
        shutdown_event.clear()
    return response


@app.route('/list_files', methods=['POST'])
def list_files():
    # Extract JSON payload, then get the folder name and the filter
    data = request.json
    folder = data.get('folder')
    filter_param = data.get('filter', '')

    if not folder:
        return jsonify({'error': 'Folder name missing'}), 400

    if not os.path.exists(folder):
        return jsonify({'error': 'Requested folder does not exist'}), 404

    if not os.path.isdir(folder) or not os.access(folder, os.R_OK):
        return jsonify({'error': 'No permission to read the requested folder'}), 403

    try:
        # Simulate a blocking call
        time.sleep(5)
        files = os.listdir(folder)
        if filter_param:
            files = fnmatch.filter(files, filter_param)
        return jsonify({'files': files}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad Request'}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not Found'}), 404


@app.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal Server Error'}), 500


@app.errorhandler(501)
def not_implemented(error):
    return jsonify({'error': 'Not Implemented'}), 501


if __name__ == '__main__':
    app.run(port=8000, debug=True)
