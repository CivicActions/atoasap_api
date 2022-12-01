# Rapid ATO API

## Introduction

Rapid ATO is system designed to simplify the process of creating a System Security Plan. The system uses
[OSCAL](https://pages.nist.gov/OSCAL/) formatted
[Component Definitions](https://pages.nist.gov/OSCAL/reference/latest/component-definition/) to help
you create an [OSCAL formatted SSP](https://pages.nist.gov/OSCAL/reference/latest/system-security-plan/).

## Local configuration

The easiest way to get up and running is to copy the `docker-compose.yml.example` file in the project root up a
directory; `cp docker-compose.yml.example ../docker-compose.yml`. Then run `docker-compose up` to start the
containers. The docker-compose file expects there to be two directories; `atoasap_api`
and `atoasap_ui`  The [atoasap_ui](https://github.com/CivicActions/atoasap_ui) is a React frontend that is configured
to run with the Rapid ATO API.

Once your containers start, you will need to enter the API container and run the following commands:

### Create an admin user and using the admin site

When developing locally, it's useful to have an admin user.
To add a super-user to your local database, enter the API container and run:

```shell
python3 manage.py createsuperuser
```

And enter a username and password when prompted.
This will allow access to access the admin site, http://localhost:8000/admin/ where the database can be interacted with
directly.

### Migrations

When there are changes to the database models, migrations will need to be executed:

```shell
python3 manage.py migrate
````

For more information about database migrations, see [this](https://docs.djangoproject.com/en/4.1/topics/migrations/).

### Import [Control Catalogs](https://csrc.nist.gov/Projects/risk-management/sp800-53-controls/release-search#/!/800-53)

Rapid ATO comes with a couple control catalogs that can be imported and used with the system. Import them with
the following command:

```shell
python3 manage.py load_catalog --load-standard-catalogs
```

### Import [Components](https://github.com/CivicActions/oscal-component-definitions)

```shell
python3 manage.py load_components
```

### Testing

Run unit tests:

```shell
# To run all the tests
python3 manage.py test

# Or, to run a specific test(s), add the name of the directory path or the specific test within the directory path and
# file.
# Examples:
python3 manage.py test directory
python3 manage.py test directory.filename
python3 manage.py test directory.filename.TestClassName
```

To run the server (outside the docker container), first set the following environment variables:
- POSTGRES_DB_HOST=localhost
- POSTGRES_DB_NAME
- POSTGRES_PASSWORD
- POSTGRES_USER

Where `POSTGRES_DB_NAME`, `POSTGRES_PASSWORD`, and `POSTGRES_USER` will need to correspond to the database name and
postgres super-user created during database setup.

Then run the server:

```shell
python3 manage.py runserver
```

### SwaggerUI

Go to http://localhost:8000/doc/ to see the SwaggerUI
Go to http://localhost:8000/doc.json or http://localhost:8000/doc.yaml to see the unformatted spec

### Django REST Framework UI

Go to http://localhost:8000/ to see the index page of the REST framework UI.
Any request defined in for the API can be executed in a browser and viewed via this UI, but actions/data may be
restricted until a user logs in with appropriate permissions.

## Contributing

### Pre-commit

A pre-commit configuration is included in the repo to assist in the development workflow.
It's not required for development, but can be useful.

To use pre-commit, ensure that you have installed [pre-commit](https://pre-commit.com/#install) on your machine and that
you have instantiated pre-commit in the **rapid ato API** repository by running `pre-commit install` in the root of your
local copy of the repo.

Once you have ``pre-commit`` installed, _pre-commit hooks_ will run each time that you do a git commit. ``pre-commit``
will try to resolve many issues, but you will be required to resolve those that it cannot before pushing your code.
