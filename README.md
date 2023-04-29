## LABS: Laboratory Automation and Batch Scheduling 
Welcome to this repository, which is intended for the revision of the submitted manuscript "LABS: Laboratory Automation and Batch Scheduling". Here, you will find the state of the project as it currently stands. Our intention is to continue updating and improving this repository.

Setup virtual enviroment: 
 > py3 -m venv .venv

 > pip install -r requirements.txt

Initialize the database:
 > flask db init

 > flask db migrate

 > flask db upgrade

 Start Flask

 > flask run

The Project is still in the development phase, so there are some features that are not yet implemented. 

'WTF_CSRF_ENABLED' = False in config.py is used to disable CSRF protection. This is not recommended for production environments. 

## Authors
Maximilian Hielscher and Maurice Dörr.