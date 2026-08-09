

# This is just a very simple example

def userconfig(si):
    uc = d() # dict-like object

    uc.sandbox_name='Example-Myapp0'

    uc.apps = [
        d(cmdvec=['bash', '--norc'], appname='bash'),
    ]

    # Generally here should be many your options
    # uc.xxxx = .......

    return uc

