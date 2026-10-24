"""Bounded in-memory multipart parsing without UploadFile disk spooling."""
import anyio
from fastapi import HTTPException
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from security import MAX_BODY_BYTES

MAX_FILE_BYTES = 10 * 1024 * 1024

async def read_image_upload(request):
    content_type, options = parse_options_header(request.headers.get('content-type',''))
    boundary = options.get(b'boundary', b'')
    if content_type != b'multipart/form-data' or not 1 <= len(boundary) <= 70:
        raise HTTPException(400, 'Expected multipart image upload.')
    body = bytearray()
    try:
        with anyio.fail_after(20):
            async for chunk in request.stream():
                if len(body) + len(chunk) > MAX_BODY_BYTES:
                    raise HTTPException(413, 'Request exceeds upload limit.')
                body.extend(chunk)
    except TimeoutError:
        raise HTTPException(408, 'Upload timed out.') from None
    payload = bytearray()
    headers = {}
    field = bytearray()
    value = bytearray()
    state = {'parts':0,'headers':0,'header_bytes':0,'complete':False,'filename':None}
    def part_begin():
        state['parts'] += 1
        if state['parts'] != 1:
            raise ValueError('Only one file is accepted.')
    def header_field(data,start,end):
        state['header_bytes'] += end-start
        if state['header_bytes'] > 8192: raise ValueError('Headers too large.')
        field.extend(data[start:end])
    def header_value(data,start,end):
        state['header_bytes'] += end-start
        if state['header_bytes'] > 8192: raise ValueError('Headers too large.')
        value.extend(data[start:end])
    def header_end():
        state['headers'] += 1
        if state['headers'] > 8: raise ValueError('Too many headers.')
        key = bytes(field).lower()
        if key in headers: raise ValueError('Duplicate header.')
        headers[key] = bytes(value)
        field.clear(); value.clear()
    def headers_finished():
        kind, params = parse_options_header(headers.get(b'content-disposition',b''))
        if kind != b'form-data' or params.get(b'name') != b'file' or b'filename' not in params:
            raise ValueError('Expected a file field.')
        state['filename'] = params[b'filename'].decode('utf-8',errors='replace')
    def part_data(data,start,end):
        if len(payload) + end-start > MAX_FILE_BYTES:
            raise HTTPException(413, 'Image exceeds 10 MiB limit.')
        payload.extend(data[start:end])
    def finished(): state['complete'] = True
    callbacks={'on_part_begin':part_begin,'on_header_field':header_field,'on_header_value':header_value,'on_header_end':header_end,'on_headers_finished':headers_finished,'on_part_data':part_data,'on_end':finished}
    try:
        parser = MultipartParser(boundary, callbacks)
        parser.write(body)
        parser.finalize()
        if not state['complete'] or state['parts'] != 1 or state['filename'] is None:
            raise ValueError('Incomplete multipart file.')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, 'Invalid multipart image upload.') from None
    return state['filename'], payload
