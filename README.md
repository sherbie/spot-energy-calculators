# Spot price simulation tools

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=sherbie_spot-risk-assessment&metric=coverage)](https://sonarcloud.io/summary/overall?id=sherbie_spot-risk-assessment)

This collection of scripts can help home owners estimate outcomes of switching from fixed rate energy prices to spot price. They are currently useful to nordic residents but additional contributers are welcome to add support for other regions.

# 1. How to set up the project


## 1.1 Install dependencies
It is recommended to use python3.12 or higher.

```
python3 -m virtualenv .env
source .env/bin/activate
pip install -r requirements.txt
```

If you want to contribute, you can also run `pre-commit install` to set up pre-commit hooks.

## 1.2. Create your entso-e account and api key

[Create your entso-e api key](https://transparency.entsoe.eu/usrm/user/myAccountSettings)

Once created put it into your local .env or export it before running
```bash
echo 'ENTSOE_API_KEY=myhoozawhatsit' >> .env
```

# Execution

```
python simulate.py
```

After deciding your input flags, you can also use `energy_model_test.json` as example input for reference.

# TODO

- Tests
- Enstoe api client integration
- cron-pattern-based consumption objects

[![SonarCloud](https://sonarcloud.io/images/project_badges/sonarcloud-white.svg)](https://sonarcloud.io/summary/overall?id=sherbie_spot-risk-assessment)
