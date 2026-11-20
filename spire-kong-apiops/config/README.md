# CI tool configuration

`deck.yaml` is the configuration file used by our decK commands. It disables CLI analytics and prevents an operator's personal `~/.deck.yaml` from silently supplying deployment defaults. Credentials and the expected target are supplied by the protected CI job.

This folder contains CI tool settings only. It does not define company governance, provision Konnect, manage global plugins or create IAM policy. API policy choices must come from the designated Kong/security owners; the pipeline validates the agreed baseline before delivery.
