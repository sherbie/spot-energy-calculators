# Spot price simulation tools

This collection of scripts can help home owners estimate outcomes of switching from fixed rate energy prices to spot price. They are currently useful to nordic residents but additional contributers are welcome to add support for other regions.

# Installation

It is recommended to use python3.10 or higher.

```
python3 -m virtualenv .env
source .env/bin/activate
pip install -r requirements.txt
```

If you want to contribute, you can also run `pre-commit install` to set up pre-commit hooks.

# Execution

```
python simulate.py
```

After deciding your input flags, you can also use `energy_model_test.json` as example input for reference.

# TODO

- Tests
- Enstoe api client integration
- cron-pattern-based consumption objects
