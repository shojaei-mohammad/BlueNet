
This template is used to develop Telegram bots using the Aiogram V3.0+ Library.

## SQLAlchemy + Alembic
The code includes examples of a User table using SQLAlchemy 2.0, and scripts for Alembic (Alembic initialization, creating and applying migrations).

### To start using:
1. Copy `.env.dist` to `.env` and fill in the necessary data.
2. Create new handlers.
3. **With Docker:**
   1. You can immediately start the project with Docker, and if you don't have it, [download and install it](https://docs.docker.com/get-docker/).
   2. Start the project with the command `docker-compose up`.
4. **Without Docker:**
   1. Create a [venv](https://docs.python.org/3/library/venv.html).
   2. Install dependencies from requirements.txt: `pip install -r requirements.txt --pre`.
   3. Start the project with the command `python3 bot.py`.

### How to create and register handlers:
Create a module `you_name.py` in the `handlers` folder.

Create a router in `you_name.py`.
```python
from aiogram import Router
user_router = Router()
```
Multiple routers can be made in one module, and handlers can be attached to each.
Handlers can be registered using decorators:

```python
@user_router.message(commands=["start"])
async def user_start(message):
    await message.reply("Welcome, regular user!")
```
Enter the file handlers/__init__.py and add all routers to it:

```python
from .admin import admin_router
from .echo import echo_router
from .user import user_router


routers_list = [
    admin_router,
    user_router,
    echo_router,  # echo_router must be last
]
```
How to add handlers to our bot:

Go to the file bot.py and unpack our handlers:

```python
from tgbot.handlers import routers_list

async def main():
   
   dp.include_routers(*routers_list)

```

### How to start the Database and conduct your first migration:

1. Go to the .env file and fill in the database details if you have not done so earlier.

2. Go to the file docker-compose.yml and uncomment sections: api, pg_database, and volumes to begin work.

3. Go to `config.py` and complete the `TODO` in the function `construct_sqlalchemy_url`. Also, find the section of the function `load_config` and uncomment the line that corresponds to the database configuration initialization `db=DbConfig.from_env(env)` to activate the database connection.

4. Now we can restart Docker with new containers using the command:

    `docker-compose up --build.`

5. All set! Now we can conduct the migration! Open the terminal and enter the following command:

    `docker-compose exec api alembic upgrade head`

## A Special Thanks to

- [Latand](https://github.com/Latand)