"""IMAP4rev1 mailbox encoding used by imapsync's explicit folder options."""
import base64


def imap_utf7(name: str) -> str:
    parts, pending = [], []

    def flush():
        if pending:
            encoded = base64.b64encode("".join(pending).encode("utf-16-be")).decode()
            parts.append("&" + encoded.rstrip("=").replace("/", ",") + "-")
            pending.clear()

    for char in name:
        if " " <= char <= "~":
            flush()
            parts.append("&-" if char == "&" else char)
        else:
            pending.append(char)
    flush()
    return "".join(parts)
