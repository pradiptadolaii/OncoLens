"""Load only the authorized, integrity-checked research artifact."""
import hashlib
import os
import shutil
import time
from pathlib import Path
from urllib.parse import urlsplit, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

EXPECTED_SHA256 = '4ba78eaa0302a8cf35f846316888b720fbc4ce7c5ed86946b1d8fb657e0dd3a4'
EXPECTED_SIZE = 44792971

def verify_model(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size != EXPECTED_SIZE:
        raise RuntimeError('Authorized checkpoint missing or size mismatch.')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            digest.update(chunk)
    if digest.hexdigest() != EXPECTED_SHA256:
        raise RuntimeError('Checkpoint SHA-256 mismatch; startup refused.')
    return path

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def prepare_model(destination):
    destination = Path(destination)
    if destination.exists(): return verify_model(destination)
    parts = [destination.with_name(destination.name+'.part01'), destination.with_name(destination.name+'.part02')]
    if all(part.is_file() for part in parts):
        temporary = destination.with_suffix('.download')
        try:
            total = 0
            with temporary.open('wb') as output:
                for part in parts:
                    with part.open('rb') as stream:
                        while chunk := stream.read(1024*1024):
                            total += len(chunk)
                            if total > EXPECTED_SIZE: raise RuntimeError('Private model parts exceed expected size.')
                            output.write(chunk)
            verify_model(temporary)
            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return destination
    source = os.environ.get('ONCOLENS_MODEL_PATH')
    url = os.environ.get('ONCOLENS_MODEL_URL')
    if not source and not url:
        raise RuntimeError('Supply ONCOLENS_MODEL_PATH or a private HTTPS ONCOLENS_MODEL_URL.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary = destination.with_suffix('.download')
    try:
        if source:
            verify_model(source)
            shutil.copyfile(source,temporary)
        else:
            original_host = urlsplit(url).hostname
            token = os.environ.get('ONCOLENS_MODEL_TOKEN','')
            opener = build_opener(NoRedirect())
            deadline = time.monotonic()+180
            for hop in range(6):
                parsed = urlsplit(url)
                if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                    raise RuntimeError('Model source must use HTTPS without URL credentials.')
                headers = {'Accept':'application/octet-stream','User-Agent':'OncoLens-artifact-loader'}
                if token and parsed.hostname == original_host:
                    headers['Authorization']='Bearer '+token
                try:
                    response = opener.open(Request(url,headers=headers),timeout=20)
                    break
                except HTTPError as error:
                    if error.code not in (301,302,303,307,308) or not error.headers.get('Location'):
                        raise RuntimeError('Private model download failed; check artifact access.') from None
                    url = urljoin(url,error.headers['Location'])
                    error.close()
            else: raise RuntimeError('Model source has too many redirects.')
            with response, temporary.open('wb') as output:
                total=0
                while True:
                    if time.monotonic() > deadline: raise RuntimeError('Model download timed out.')
                    chunk=response.read(1024*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>EXPECTED_SIZE: raise RuntimeError('Model download exceeds expected size.')
                    output.write(chunk)
        verify_model(temporary)
        temporary.replace(destination)
    except Exception as error:
        temporary.unlink(missing_ok=True)
        if isinstance(error,RuntimeError): raise
        raise RuntimeError('Unable to acquire verified private checkpoint.') from None
    return destination
