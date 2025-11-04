# instagram_hmac.py
import hmac, hashlib

def verify_meta_hmac(app_secret: str, raw: bytes, hdr256: str|None, hdr1: str|None) -> bool:
    import hmac, hashlib
    def strip(v,p): 
        return v[len(p):] if v and v.lower().startswith(p) else v
    h256 = strip(hdr256, "sha256=")
    h1   = strip(hdr1,   "sha1=")

    calc256 = hmac.new(app_secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
    if h256 and hmac.compare_digest(calc256.lower(), h256.lower()):
        return True
    calc1 = hmac.new(app_secret.encode("utf-8"), raw, hashlib.sha1).hexdigest()
    if h1 and hmac.compare_digest(calc1.lower(), h1.lower()):
        return True
    return False
