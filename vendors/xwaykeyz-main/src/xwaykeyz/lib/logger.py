VERBOSE = False
FLUSH = False

def debug(*args, ctx="DD"):
    if not VERBOSE:
        return

    # allow blank lines without context
    if len(args) == 0 or (len(args) == 1 and args[0] == ""):
        print("", flush=FLUSH)
        return
    print(f"({ctx})", *args, flush=FLUSH)


def warn(*args, ctx="WW"):
    print(f"({ctx})", *args, flush=FLUSH)


def error(*args, ctx="EE"):
    print(f"({ctx})", *args, flush=FLUSH)


def log(*args, ctx="--"):
    print(f"({ctx})", *args, flush=FLUSH)


def info(*args, ctx="--"):
    log(*args, ctx=ctx)
