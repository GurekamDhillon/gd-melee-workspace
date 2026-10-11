# Local TLS test fixture

`tls-localhost.pem` and `tls-localhost-key.pem` are a deliberately public,
self-signed certificate/key pair for `127.0.0.1` HTTPS tests. They are neither
release-signing keys nor production credentials. Never use them outside tests.

The Qt updater redirect tests and packaged runtime probe trust this certificate
only in their request/process configuration. They never modify Windows trust
stores or ignore TLS verification errors. The probe and fixture files are not
installed in release packages.
