

# When you are going to create a new specific sandbox:
# Copy the 'userconfig' part from treesandbox.py.
# Paste the code into your 'my-sandboxes/uc.<name>.py',
# and start to modify the userconfig code

# This is just a very simple example

def userconfig(si):
    uc = d() # dict-like object

    uc.sandbox_name='Example-Myapp0'

    uc.apps = [
        d(cmdvec=['bash'], appname='bash'),
    ]

    # Generally here should be many your options
    # uc.xxxx = .......

    return uc

