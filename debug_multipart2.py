# 1x1 PNG bytes
png = bytes([0x89, 0x50, 0x4e, 0x47])

boundary = "----TestBoundary"
body = (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="file"; filename="test.png"\r\n'
    "Content-Type: image/png\r\n\r\n"
    .encode() + png + f"\r\n--{boundary}--\r\n".encode()
)

import re
content_type = f"multipart/form-data; boundary={boundary}"
boundary_match = re.search(r"boundary=(.+?)(?:;|$)", content_type)
b = boundary_match.group(1).strip().strip('"')
delim = f"--{b}".encode()
parts = body.split(delim)

part = parts[1]
print("Part repr:", repr(part[:100]))
print()

# Check if it has \r\n\r\n
header_block, file_data = part.split(b"\r\n\r\n", 1)
print("Header block repr:", repr(header_block))
print()

# Now test _parse_headers
text = header_block.decode("utf-8", errors="replace")
print("Text:", repr(text))
print()

result = {}
for line in text.splitlines():
    print(f"Line: {repr(line)}")
    if ": " in line:
        key, val = line.split(": ", 1)
        result[key.lower()] = val.strip()

print("Result:", result)
print("name:", result.get("name"))
