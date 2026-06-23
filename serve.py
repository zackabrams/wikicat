import functools, http.server, socketserver
D = "/Users/zackabrams/Downloads/wikicat"
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=D)
with socketserver.TCPServer(("127.0.0.1", 8754), H) as s:
    s.serve_forever()
