#!/usr/bin/env python
# Copyright (C) 2010-2015 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

import argparse
import os
import platform
import subprocess
import sys
import tempfile
import traceback
import zipfile

try:
    from flask import Flask, request, jsonify
except ImportError:
    sys.exit("ERROR: Flask library is missing (`pip install flask`)")

app = Flask("agent")

def json_error(error_code, message):
    r = jsonify(message=message, error_code=error_code)
    r.status_code = error_code
    return r

def json_exception(message):
    r = jsonify(message=message, error_code=500,
                traceback=traceback.format_exc())
    r.status_code = 500
    return r

def json_success(message, **kwargs):
    return jsonify(message=message, **kwargs)

@app.route("/")
def get_index():
    return json_success("Cuckoo Agent!")

@app.route("/system")
def get_system():
    return json_success("System", system=platform.system())

@app.route("/environ")
def get_environ():
    return json_success("Environment variables", environ=dict(os.environ))

@app.route("/path")
def get_path():
    return json_success("Agent path", filepath=os.path.abspath(__file__))

@app.route("/mkdir", methods=["POST"])
def do_mkdir():
    if "dirpath" not in request.form:
        return json_error(400, "No dirpath has been provided")

    mode = int(request.form.get("mode", 0777))

    try:
        os.makedirs(request.form["dirpath"], mode=mode)
    except:
        return json_exception("Error creating directory")

    return json_success("Successfully created directory")

@app.route("/mktemp", methods=["GET", "POST"])
def do_mktemp():
    suffix = request.form.get("suffix", "")
    prefix = request.form.get("prefix", "tmp")
    dirpath = request.form.get("dirpath")

    fd, filepath = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=dirpath)
    os.close(fd)

    return json_success("Successfully created temporary file",
                        filepath=filepath)

@app.route("/mkdtemp", methods=["GET", "POST"])
def do_mkdtemp():
    suffix = request.form.get("suffix", "")
    prefix = request.form.get("prefix", "tmp")
    dirpath = request.form.get("dirpath")

    dirpath = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=dirpath)
    return json_success("Successfully created temporary directory",
                        dirpath=dirpath)

@app.route("/store", methods=["POST"])
def do_store():
    if "filepath" not in request.form:
        return json_error(400, "No filepath has been provided")

    if "file" not in request.files:
        return json_error(400, "No file has been provided")

    try:
        with open(request.form["filepath"], "wb") as f:
            f.write(request.files["file"].read())
    except:
        return json_exception("Error storing file")

    return json_success("Successfully stored file")

@app.route("/extract", methods=["POST"])
def do_extract():
    if "dirpath" not in request.form:
        return json_error(400, "No dirpath has been provided")

    if "zipfile" not in request.files:
        return json_error(400, "No zip file has been provided")

    try:
        with zipfile.ZipFile(request.files["zipfile"], "r") as archive:
            archive.extractall(request.form["dirpath"])
    except:
        return json_exception("Error extracting zip file")

    return json_success("Successfully extracted zip file")

@app.route("/execute", methods=["POST"])
def do_execute():
    if "command" not in request.form:
        return json_error(400, "No command has been provided")

    # Execute the command asynchronously?
    async = "async" in request.form
    stdout = stderr = None

    try:
        p = subprocess.Popen(request.form["command"], shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        if not async:
            stdout, stderr = p.communicate()
    except:
        return json_exception("Error executing command")

    return json_success("Successfully executed command",
                        stdout=stdout, stderr=stderr)

@app.route("/kill")
def do_kill():
    os.unlink(__file__)
    exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?", default="0.0.0.0")
    parser.add_argument("port", nargs="?", default="8000")
    args = parser.parse_args()

    app.run(host=args.host, port=int(args.port))
