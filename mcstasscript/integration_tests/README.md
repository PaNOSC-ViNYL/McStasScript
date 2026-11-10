# Integration Tests

These tests run complete McStas/McXtrace simulations and therefore require a
working McStas installation and its executables.

Run them with:

```bash
python -m unittest discover -s mcstasscript/integration_tests -v
```

They are separate from unit tests because they require external simulation
software and take longer to run.
