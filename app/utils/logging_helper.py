import logging
import time
import json
from flask import request, g

log = logging.getLogger("api.request")


def setup_request_logging(app):
    @app.before_request
    def before_request_func():
        # Only log API paths
        if not request.path.startswith('/api'):
            return

        g.request_start_time = time.monotonic()
        # Generate a unique request identifier
        g.request_id = f"REQ-{int(time.time() * 1000)}"

        # Gather details
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        method = request.method
        path = request.path

        log.info("+------------------------------------------------------------------------")
        log.info("| >>> INCOMING REQUEST %s %s from %s", method, path, ip)
        log.info("| ID: %s", g.request_id)

        # Headers (selected)
        important_headers = ['Content-Type', 'Content-Length', 'User-Agent', 'Authorization']
        headers_str = ", ".join(f"{h}: {request.headers.get(h)}" for h in important_headers if request.headers.get(h))
        if headers_str:
            log.info("| Headers: %s", headers_str)

        # Query Params
        if request.args:
            log.info("| Query Params: %s", json.dumps(request.args.to_dict(), ensure_ascii=True))

        # Form Data
        if request.form:
            log.info("| Form Data: %s", json.dumps(request.form.to_dict(), ensure_ascii=True))

        # Files
        if request.files:
            files_info = []
            for key, file_list in request.files.lists():
                for file in file_list:
                    filename = file.filename or "<empty>"
                    content_type = file.content_type or "unknown"
                    files_info.append(f"{key}='{filename}' ({content_type})")
            log.info("| Files: %s", ", ".join(files_info))

        # JSON Body
        if request.is_json:
            try:
                body = request.get_json(silent=True)
                if body:
                    truncated_body = _truncate_dict(body)
                    log.info("| JSON Body: %s", json.dumps(truncated_body, ensure_ascii=True, indent=2).replace('\n', '\n| '))
            except Exception as e:
                log.debug("| JSON parse error for logging: %s", str(e))

        log.info("+------------------------------------------------------------------------")

    @app.after_request
    def after_request_func(response):
        if not request.path.startswith('/api'):
            return response

        # Duration
        start_time = g.get('request_start_time')
        duration_ms = int((time.monotonic() - start_time) * 1000) if start_time else 0
        req_id = g.get('request_id', 'UNKNOWN')

        status = response.status_code
        status_text = response.status
        
        # Safe length computation
        try:
            content_length = response.content_length or len(response.get_data())
        except Exception:
            content_length = 0
            
        mimetype = response.mimetype

        log.info("+------------------------------------------------------------------------")
        log.info("| <<< OUTGOING RESPONSE [%s] -- %s", req_id, status_text)
        log.info("| Duration: %d ms | Size: %s bytes | Type: %s", duration_ms, content_length, mimetype)

        if mimetype == 'application/json':
            try:
                resp_data = response.get_data(as_text=True)
                resp_json = json.loads(resp_data)
                truncated_resp = _truncate_dict(resp_json)
                log.info("| Response JSON: %s", json.dumps(truncated_resp, ensure_ascii=True, indent=2).replace('\n', '\n| '))
            except Exception as e:
                log.debug("| Response JSON parse error for logging: %s", str(e))
        else:
            if mimetype and ('text' in mimetype or 'html' in mimetype):
                try:
                    resp_data = response.get_data(as_text=True)
                    preview = resp_data[:200] + ('...' if len(resp_data) > 200 else '')
                    log.info("| Response Text: %s", preview)
                except Exception:
                    pass

        log.info("+------------------------------------------------------------------------")
        return response


def _truncate_dict(d, max_len=150):
    """Recursively truncates long strings and lists in a dictionary/list for logging."""
    if isinstance(d, dict):
        return {k: _truncate_dict(v, max_len) for k, v in d.items()}
    elif isinstance(d, list):
        if len(d) > 5:
            return [_truncate_dict(x, max_len) for x in d[:5]] + [f"... <and {len(d) - 5} more items>"]
        return [_truncate_dict(x, max_len) for x in d]
    elif isinstance(d, str):
        if len(d) > max_len:
            return d[:max_len] + f"... <truncated; {len(d)} chars>"
        return d
    return d
