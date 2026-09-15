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


def imap_utf7_decode(name: str) -> str:
    """Inverse of imap_utf7, tolerant: an invalid shifted section is kept verbatim."""
    parts, index = [], 0
    while index < len(name):
        char = name[index]
        if char != "&":
            parts.append(char)
            index += 1
            continue
        end = name.find("-", index + 1)
        if end < 0:
            parts.append(name[index:])
            break
        section = name[index + 1:end]
        if section == "":
            parts.append("&")
        else:
            encoded = section.replace(",", "/")
            try:
                raw = base64.b64decode(encoded + "=" * (-len(encoded) % 4), validate=True)
                parts.append(raw.decode("utf-16-be"))
            except (ValueError, UnicodeDecodeError):
                parts.append(name[index:end + 1])
        index = end + 1
    return "".join(parts)
