import sys
from mitmproxy import http

def request(flow: http.HTTPFlow):
    sys.stderr.write(f"[MINIMAL] request: {flow.request.method} {flow.request.pretty_host}{flow.request.path}\n")
    sys.stderr.flush()

def response(flow: http.HTTPFlow):
    sys.stderr.write(f"[MINIMAL] response: {flow.request.pretty_host} -> {flow.response.status_code}\n")
    sys.stderr.flush()
