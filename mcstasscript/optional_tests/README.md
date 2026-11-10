# Optional Tests

These tests exercise the optional `pythreejs` geometry-rendering dependency.
The regular test dependencies already include `ipympl`.

Install `pythreejs` and run them with:

```bash
python -m pytest mcstasscript/optional_tests/
```

They are kept separate from the base unit tests so installations that do not
provide `pythreejs` can still run the regular test suite.
