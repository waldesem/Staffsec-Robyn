# StaffSec

Experimental desktop webapp for managing local database.

### The technology stack used in this project:

- Robyn;
- Sqlite;
- Vue;

### Installation

To use this project, you will need to have Python 3.14 or higher.

```
git clone https://github.com/waldesem/Staffsec-Desktop.git
cd Staffsec-Desktop
wget -qO- https://astral.sh/uv/install.sh | sh
uv sync
```

### Settings

You need creating settings.ini file run with:

```
[Destination]
path =
```

Where path is a destination for files share.

DEFAULT_PASSWORD for created user is `88888888`.


### Start backend server

To start desktop app run the command in terminal:

```
uv run app.py
```