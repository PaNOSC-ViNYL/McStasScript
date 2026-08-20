# Optional Tests

These tests exercise the optional `anythreejs` geometry-rendering dependency.
The regular test dependencies already include `ipympl`.

Install `anythreejs` and run them with:

```bash
python -m pytest mcstasscript/optional_tests/
```

They are kept separate from the base unit tests so installations that do not
provide `anythreejs` can still run the regular test suite.
