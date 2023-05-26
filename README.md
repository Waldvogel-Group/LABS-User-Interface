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

Upon the first start, an administrativ account ist created, the credentials will be printed to the console.
The login page can be found at http://127.0.0.1:5000/login


The Project is still in the development phase, so there are some features that are not yet implemented. 

Since the API connection between the User-Interface and the Twisted Backend is not secured yet, we do not recommend use case open to the local or wide network under any circumstances yet. 
We tested the project, where the host for user interface and backend was the same computer. 
If an installation with several backends is to be realized at this time, we recommend putting the applications behind a reverse proxy and securing access with a firewall. 
We plan to secure the API communication for a later release. 

'WTF_CSRF_ENABLED' = False in config.py is used to disable CSRF protection. This is not recommended for production environments. 

## Authors
Maximilian Hielscher and Maurice Dörr.