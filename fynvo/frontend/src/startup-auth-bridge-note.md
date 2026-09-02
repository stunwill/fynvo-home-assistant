# Startup authentication bridge

Fynvo's production shell authenticates before mounting the nested legacy-compatible application shell. v1.17.1 caches that authoritative authentication result so the nested shell's startup-only `/auth/state` read can complete immediately without a second Home Assistant ingress network dependency.

The outer shell still bypasses the cache when it refreshes authentication, so login, logout, session expiry and recovery-mode state continue to come from the backend.
