import hashlib


def junit_import_source_hash(test_run_id, content):
    value = f"{test_run_id}\0{content}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()
