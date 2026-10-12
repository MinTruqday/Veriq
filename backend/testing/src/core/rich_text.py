def text_document(value):
    text = str(value)
    return {
        "type": "doc",
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}] if text else [],
    }
