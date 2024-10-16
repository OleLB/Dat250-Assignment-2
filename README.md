# Dat250-Assignment-2
DAT250 Assignment 2: Information and Software Security - Vulnerability Remediation 




### Starting the application

To start the application, open a terminal in the root directory of the project, and run the command:

```shell
poetry run flask --debug run
```

> [!TIP]
> The `--debug` flag starts the application in debug mode. This mode enables the debugger, reloader, and other nice-to-have development features.

An alternative way to start the application is by executing the `social_insecurity.py` file using Python:

```shell
poetry run python social_insecurity.py
```

Access the application by entering `http://localhost:5000/` in the address bar of a web browser while the application is running.

> [!NOTE]
> Prepending `poetry run` to any command ensures that the command is run inside the virtual environment created by Poetry, and not in the global Python environment. As an example, the command `poetry run python -c "print('Hello World')"` prints `Hello World` to the terminal using the Python interpreter installed inside the project‘s virtual environment.

To stop the application, press <kbd>Ctrl</kbd>+<kbd>C</kbd> in the terminal where the application is running.

To reset the application back to its initial state, use:

```shell
poetry run flask reset
```

This deletes the `instance/` directory which contains the database file and user uploaded files.