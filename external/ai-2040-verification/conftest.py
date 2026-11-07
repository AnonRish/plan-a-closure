# test_server.py needs a live server and PostgreSQL; test_suite.py is the experiment
# runner (`make quickstart`), not a pytest module. Both are scripts, so keep pytest
# from importing them. The assertions live in tests/.
collect_ignore = ["test_server.py", "test_suite.py"]
