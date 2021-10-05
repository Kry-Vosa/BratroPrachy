import src.prachy, contextlib, sys
with open('last_run.log', 'w+') as f:
    with contextlib.redirect_stdout(f), contextlib.redirect_stderr(sys.stdout):
        src.prachy.run_app()
        print("Run done!")