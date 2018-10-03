# Mix-Mind

Dynamic menu generator and order manager for your home bar.

## Features

There exist some features

## Data Model

A relational database is used to manage Users to support the login system. A logged in user can place orders without entering their email every time. Other users may be assigned as bartenders or owners and can manage those settings when logged in.

Ingredients come from a spreadsheet, but are loaded into a bar's database on the site.

Recipes are stored as a json file, with a base file providing a common set of recipes, and each bar being able to add custom recipes.

### Entities
![Entity model](erd.svg "Entity Relational Model")
- User
  - User is uniquely identified by email
  - Some basic stats are kept on each user
  - The user model has the required bookkeeping for authentication
  - User may supply a nickname
  - If user supplies they Venmo ID, confirmations sent to customers when they are a bartender will include a link to their venmo profile, for tips
- Role
  - Customer - all users are customers
  - Bartender - this user has been assigned as bartender at at least one bar
  - Owner - this user has at least one bar
  - Admin - admin user may modify any user, assign bars to users, modify the main recipe library, modify any bar
- Bar
  - A bar represents a collection of ingredients
  - May have up to one bartender on duty (this will be the email address orders are sent to)
  - Has one owner
  - Has a number of configuration values for how to display recipes and set optional prices
- Order
  - An order is placed at a bar, by a user, served by a bartender once confirmed
- Ingredient
  - An ingredient is defined with a Type and Bottle, where Type is something like "dry gin" or "bourbon whiskey", and Bottle is the specific brand and bottling, "Bombay Sapphire" or "Old Grand-Dad Bonded"
  - An ingredient may only belong to one bar

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

A [virtualenv](https://docs.python-guide.org/dev/virtualenvs/) is recommended for setting up this project.

### Installing

```
pip install -r requirements.txt
```

### Configuration

Configuration for the flask app is contained in a `config.py` and `instance/config.py`. See the [flask config docs](http://flask.pocoo.org/docs/1.0/config/)

This repo includes an example [instance/config_example.py](instance/config_example.py), to be used for all the secret configuration.

For email notifications with the user system and order notifications, an email account with api access will be required. This is easy to do with gmail, and the base configuration assumes as much.


## Deployment

The original version of this site is running on [PythonAnywhere](pythonanywhere.com), which is the author's recommended deployment solution.

## Built With

* [Flask](http://flask.pocoo.org/docs/1.0/patterns/) - Web framework
* [Flask-Security](https://pythonhosted.org/Flask-Security/) - For user login management
* [Flask-SQLAlchemy](http://flask-sqlalchemy.pocoo.org/2.3/) - Manages SQL backend
* [Flask-WTF](https://flask-wtf.readthedocs.io/en/stable/) - Better WTForms
* [PyLaTeX](https://jeltef.github.io/PyLaTeX/current/) - Generate TeX menu downloads from python
* [Pendulum](https://pendulum.eustace.io/) - Better time and date for python
* [Datatables](https://datatables.net/) - For the ingredient tables and displaying users, orders
* [CellEdit](https://github.com/ejbeaty/CellEdit) - Basis for inline-editable ingredient datatable

## Contributing

Please feel free to check out the open issues and submit a PR!

## Versioning

This project uses [Semantic Versioning](http://semver.org/) for versioning. For the versions available, see the [tags on this repository](https://github.com/twschum/mix-mind/tags).

## Authors

* **Tim Schumacher** - *Core Author* - [twschum](https://github.com/twschum)

See also the list of [contributors](https://github.com/twschum/mix-mind/contributors) who participated in this project.

## License

This project is licensed under the Apache-2.0 License - see the [LICENSE](LICENSE) file for details.

