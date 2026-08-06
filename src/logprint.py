from heads import *

def lines_add_prefix(text):
    prefix = f'[ {loghead} ]' if loghead else ''
    return ''.join( [prefix + l for l in text.splitlines(True)] )
def print_exc(*args): # 替代原 traceback.print_exc()
    sio = io.StringIO()
    traceback.print_exc(*args, file=sio)
    print( lines_add_prefix(sio.getvalue()) , file=sys.stderr)
def print_stack(*args): # 替代原 traceback.print_stack()
    sio = io.StringIO()
    traceback.print_stack(*args, file=sio)
    print( lines_add_prefix(sio.getvalue()) , file=sys.stderr)

def custom_excepthook(*args):
    tb_str = "".join(traceback.format_exception(*args))
    print( lines_add_prefix(tb_str) , file=sys.stderr)

_print = print
def print(*args, **kwargs):
    try:
        _print(*args, **kwargs)
        sys.stdout.flush() ; sys.stderr.flush()
    except: pass
loghead = ''
def set_loghead(new_loghead):
    global loghead
    loghead = new_loghead.rstrip(': ') + ': '
    sys.excepthook = custom_excepthook
def log(*args, **kwargs):
    new_args = args
    if loghead: new_args = ( loghead,  *args)
    print(*new_args, **kwargs)
def log_warn(*args, **kwargs):
    if 'file' not in kwargs: kwargs['file'] = sys.stderr
    log('WARNING: ',  *args, **kwargs)
