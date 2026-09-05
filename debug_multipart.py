# 1x1 PNG bytes
png = bytes([
    0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a,
    0x00, 0x00, 0x00, 0x0d, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xde, 0x00, 0x00, 0x00, 0x0c, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xd7, 0x63, 0xf8, 0xcf, 0xc0, 0x00,
    0x00, 0x00, 0x02, 0x00, 0x01, 0xe2, 0x21, 0xbc,
    0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4e,
    0x44, 0xae, 0x42, 0x60, 0x82
])

boundary = "----TestBoundary"
body = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="test.png"\r\n'
    "Content-Type: image/png\r\n\r\n"
    .encode() + png + f"\r\n--{boundary}--\r\n".encode()
)

# 模拟服务器的解析逻辑
import re
content_type = f"multipart/form-data; boundary={boundary}"
boundary_match = re.search(r"boundary=(.+?)(?:;|$)", content_type)
b = boundary_match.group(1).strip().strip('"')
print("Extracted boundary:", repr(b))
delim = f"--{b}".encode()
print("Delimiter:", repr(delim))
parts = body.split(delim)
print("Num parts:", len(parts))
for i, p in enumerate(parts):
    has_crlf = b"\r\n\r\n" in p
    stripped = bool(p.strip())
    print(f"Part {i}: len={len(p)}, has_crlf={has_crlf}, stripped={stripped}")
    if has_crlf and stripped:
        header_block, file_data = p.split(b"\r\n\r\n", 1)
        print(f"  Header: {header_block[:80]}")
        print(f"  File data len: {len(file_data)}")
