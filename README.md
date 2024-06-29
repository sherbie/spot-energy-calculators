# Spot price simulation tools

[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=sherbie_spot-risk-assessment&metric=coverage)](https://sonarcloud.io/summary/overall?id=sherbie_spot-risk-assessment)

This collection of scripts can help home owners estimate outcomes of switching from fixed rate energy prices to spot price. They are currently useful to nordic residents but additional contributers are welcome to add support for other regions.

# 1. How to set up the project


## 1.1 Install dependencies
It is recommended to use python3.12 or higher.

```
python3 -m virtualenv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name=.venv --display-name "Spot Energy Calculators"
```

If you want to contribute, you can also run `pre-commit install` to set up pre-commit hooks.

## 1.2. Create your entso-e account and api key

1. Go to https://transparency.entsoe.eu and click *Login*.
1. Click *Register* at the bottom of the dialog and complete the registration process.
1. Go to [account settings](https://transparency.entsoe.eu/usrm/user/myAccountSettings).
1. Create your entso-e API key by clicking the *Generate a new Token* button under **Web Api Security Token**.
1. If you do not see the *Generate a new Token* button, you will need to contact support at `transparency@entsoe.eu` to request API access. Once the support request is resolved, try again to create an API token.
1. Once created put it into your local .env or export it before running
```bash
 echo 'ENTSOE_API_KEY=myhoozawhatsit' >> .env
```

# Execution

```
python simulate.py
```

After deciding your input flags, you can also use `energy_model_test.json` as example input for reference.

[![SonarCloud](https://sonarcloud.io/images/project_badges/sonarcloud-white.svg)](https://sonarcloud.io/summary/overall?id=sherbie_spot-risk-assessment)
