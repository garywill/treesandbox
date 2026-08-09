#!/usr/bin/env -S python3 -IBS

# Deploy Tool of Tree Sandbox
#
# Licensed under GPL.  https://github.com/garywill/treesandbox
# This project comes with no warranty. Use on your own risk.

import os,sys, ast, tomllib, argparse, subprocess, datetime, traceback, zipapp, zipfile, tempfile
from urllib.parse import quote
from pathlib import Path

user_sbxes_path = None
def main():
    global user_sbxes_path
    arg_parser = argparse.ArgumentParser( add_help=True,
        description="The Deploy Tool of Tree Sandbox"
    )
    arg_parser.add_argument("-s", default=None, metavar='<dir>',
                            help="The path of the dir that contains your list.toml and uc.<name>.py files. Defaultly use the same dir as this deploy tool script file.")

    (known_args, # 上面列出的参数
        user_cli_argv # 未知参数，即之后的参数，
    ) = arg_parser.parse_known_args()
    user_sbxes_path = known_args.s
    if not user_sbxes_path: user_sbxes_path = f'{scriptdirpath}/my-sandboxes'

    log(f"Using python interpreter << '{sys.executable}' >> . This interpreter will also be used in deployed specific-sandbox startup .pyz files.")
    log(f"Look for user custom list.toml and uc.<name>.py files in '{user_sbxes_path}'")
    log('')

    list_file = f'{user_sbxes_path}/list.toml'
    list_file_content = open(list_file).read()
    try:
        list_file_obj = tomllib.loads(list_file_content)
    except Exception as err:
        log_warn(f'Failed to parse {list_file}')
        log_warn(err)
        sys.exit(1)

    try:
        my_sandboxes = D(list_file_obj).my_sandboxes
    except Exception as err:
        log_warn(f'Failed to find my_sandboxes from file {list_file}')
        log_warn(err)
        sys.exit(1)

    if not isinstance(my_sandboxes, list):
        log_warn(f'Failed to find list object my_sandboxes from file {list_file}')
        sys.exit(1)

    for sbx in my_sandboxes:
        try:
            deploy_one_sandbox(d(sbx))
        except OneSbxError as err:
            log_warn(f'✘ A sandbox failed {sbx}: {err}')
        except OneSbxErrorSame as err:
            log_warn(f'A sandbox skipped {sbx}: {err}')
        except Exception as err:
            log_warn(f'✘ Error occured when deploying sandbox {sbx}: {err}')
            traceback.print_exc()
            sys.exit(1)



def deploy_one_sandbox(sbx):
    if sbx.destfile:
        destfile = sbx.destfile
        if not destfile.lower().endswith('.pyz'):
            raise OneSbxError("destfile should end with '.pyz'")
    elif sbx.destdir:
        destfile = f'{sbx.destdir}/tsbxrun_{sbx.name}.pyz'
    else:
        raise OneSbxError("No destdir nor destfile")

    uc_filename = f'uc.{sbx.name}.py'
    uc_file_path = f'{user_sbxes_path}/{uc_filename}'
    if not os.path.exists(uc_file_path):
        raise OneSbxError(f'✘ User config file not exist {uc_file_path}')
    check_syntax(filepath=uc_file_path)

    destdir = os.path.dirname(destfile)
    if not os.path.exists(destdir):
        raise OneSbxError(f'Dir {destdir} not exist. ')


    tsver = sbx.tsver
    if not tsver:
        verstring = 'file-as-is'
    else:
        verstring = tsver

    progcodeinfo = get_progcodeinfo_by_ver(verstring)
    if progcodeinfo == 'preholder':
        raise OneSbxErrorSame(f"Skip because version '{verstring}' met problem before")

    verdir = progcodeinfo.verdir
    userconfig_dst = f'{verdir}/userconfig.py'
    info_txt_path = f'{verdir}/info.txt'

    copy_file(uc_file_path, userconfig_dst)
    with open(info_txt_path, 'w') as f: f.write(progcodeinfo.tsver_tip)
    try:
        zipapp.create_archive( source=verdir, target=destfile, compressed=True,
            interpreter=f'/usr/bin/env -S {sys.executable} -IBS',
        )
        os.chmod(destfile, 0o755)
        log(f'Successfully write to {destfile}. √')
    except Exception as err:
        traceback.print_exc()
        raise OneSbxError(err)
    finally:
        if os.path.lexists(userconfig_dst):
            os.unlink(userconfig_dst)
        if os.path.lexists(info_txt_path) :
            os.unlink(info_txt_path)



Codes = None
def get_progcodeinfo_by_ver(verstring):
    global Codes

    if Codes is None:
        Codes = d()

    if Codes[verstring]:
        return Codes[verstring]

    Codes[verstring] = 'preholder'

    verdir = f'{DPL_TMPDIR}/{quote(verstring, safe="")}'
    os.makedirs(verdir)

    if verstring == 'file-as-is' :
        srcdir = f'{scriptdirpath}/src'

        timestamp_disp = datetime.datetime.fromtimestamp(os.stat(srcdir).st_mtime) \
            .strftime("%Y-%m-%d %H:%M:%S")
        tsver_tip = timestamp_disp

        srcfileS = [str(p) for p in Path(srcdir).glob('*.py') if p.is_file()]
        for srcfile in srcfileS :
            filename = srcfile.split('/')[-1]
            if filename == 'userconfig.py':
                continue
            copy_file(srcfile, f'{verdir}/{filename}')
    elif verstring.startswith('git:tag:'):
        tagname = verstring.removeprefix('git:tag:')
        tsver_tip = verstring
        export_git_src_to_verdir(f'refs/tags/{tagname}', verdir)
    elif verstring.startswith('git:commit:'):
        commit = verstring.removeprefix('git:commit:')
        tsver_tip = verstring
        export_git_src_to_verdir(commit, verdir)
    elif verstring.startswith('git:branch:') :
        branchname = verstring.removeprefix('git:branch:')
        commit = run_cmd_get_stdout(['git', 'rev-parse', f'refs/heads/{branchname}']).strip()
        tsver_tip = f'{verstring} {commit}'
        export_git_src_to_verdir(commit, verdir)
    elif verstring == 'git:head':
        commit = run_cmd_get_stdout(['git', 'rev-parse', 'HEAD']).strip()
        tsver_tip = f'{verstring} {commit}'
        export_git_src_to_verdir(commit, verdir)
    else:
        raise OneSbxError(f'Invalid version string {verstring}')

    py_files_in_verdir = [str(p) for p in Path(verdir).glob('*.py') if p.is_file()]
    for filepath in py_files_in_verdir:
        check_syntax(codecontent=open(filepath).read(),
                     name=f'{filepath.split("/")[-1]} (version: {verstring})'
                     )

    result = D(
        tsver_tip = tsver_tip,
        verdir = verdir,
    )
    Codes[verstring] = result
    return Codes[verstring]


def run_cmd_get_stdout(cmdvec):
    proc = subprocess.Popen( cmdvec,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        raise OneSbxError(f'Error when executing command {cmdvec} . Stderr: {stderr.decode()}')
    return stdout.decode()

def copy_file(src, dst):
    with open(src, 'rb') as fsrc:  data = fsrc.read()
    with open(dst, 'wb') as fdst:  fdst.write(data)

def export_git_src_to_verdir(gitref, verdir):
    files_text = run_cmd_get_stdout(['git', 'ls-tree', '--name-only', gitref, 'src/'])
    # print(gitref, files_text)
    files = [x.strip() for x in files_text.splitlines() if x.strip()]
    files = [x.removeprefix('src/') for x in files if x.startswith('src/') and x.endswith('.py') ]

    for filename in files:
        if '/' in filename: # 如果是 src/xxx/xxx.py
            continue
        if filename == 'userconfig.py':
            continue
        content = run_cmd_get_stdout(['git', 'show', f'{gitref}:src/{filename}'])
        with open(f'{verdir}/{filename}', 'w') as f:
            f.write(content)





def check_syntax(filepath=None, codecontent=None , name=None, lineofs=0):
    try:
        if filepath:
            ast.parse(open(filepath).read())
        elif codecontent:
            ast.parse(codecontent)
        else: raise Exception('This function is not used with proper parameter')
        return True
    except SyntaxError as err:
        errmsg = '\n'
        errmsg +=  "✘ Syntax Error in " + (filepath if filepath else name) + " :\n"
        errmsg += f"   Line {err.lineno + lineofs}, Col {err.offset}:\n"
        errmsg +=   err.text + '\n'
        errmsg += f"   Err msg: {err.msg}\n"
        errmsg += '\n'
        log_warn(errmsg)
        raise OneSbxError(f'Syntax error found in {filepath if filepath else name}')






# ================================================

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
    log('Warn: ',  *args, **kwargs)

class OneSbxError(Exception):
    pass
class OneSbxErrorSame(Exception):
    pass


class EnhancedFalse:
    def __init__(self, dictObj, keyName):
        self.dictObj = dictObj
        self.keyName = keyName
    def _error(self):
        raise Exception(f"✘ Program tries to stringlize or compare a non-defined member '{self.keyName}' of a dict-like obj: {str(self.dictObj)[:200]} ...")
    def __str__(self):
        self._error()
    def __repr__(self):
        self._error()
    def __bool__(self):
        return False
    def __eq__(self, other):
        return False
    def __ne__(self, other):
        return True
    def __lt__(self, other):
        self._error()
    def __le__(self, other):
        self._error()
    def __gt__(self, other):
        self._error()
    def __ge__(self, other):
        self._error()
    __hash__ = None


class EnhancedDictTempl(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for key, value in self.items():
            if isinstance(value, dict) and not isinstance(value, type(self)):
                self[key] = type(self)(value)
            elif isinstance(value, list):
                self[key] = self._convert_list(value)
    def _convert_list(self, lst):
        new_list = []
        for item in lst:
            if isinstance(item, dict) and not isinstance(item, type(self)):
                new_list.append(type(self)(item))
            elif isinstance(item, list):
                new_list.append(self._convert_list(item))
            else: new_list.append(item)
        return new_list
    def __setattr__(self, name, value):
        self[name] = value
    def __delattr__(self, name):
        try: del self[name]
        except KeyError: pass
    def __setitem__(self, key, value):
        processed_value = value
        if isinstance(value, dict) and not isinstance(value, type(self)):
            processed_value = type(self)(value)
        elif isinstance(value, list):
             processed_value = self._convert_list(value)
        super().__setitem__(key, processed_value)
class Dict(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try: return self[name]
        except :
            raise
class DictFALSE(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"): raise AttributeError(name)
        try: return self[name]
        except KeyError:
            return EnhancedFalse(self, name)
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            return EnhancedFalse(self, key)
class DictNone(EnhancedDictTempl):
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        try: return self[name]
        except :
            return None
    def __getitem__(self, key):
        try: return super().__getitem__(key)
        except KeyError:
            return None
D = Dict  # Raises an error when trying to access a non-existent key.
d = DictFALSE  # Returns EnhancedFalse when trying to access a non-existent key.
dn = DictNone  # Returns None when trying to access a non-existent key.


# ================================================

scriptfilepath = os.path.abspath(__file__)
scriptdirpath = os.path.dirname(scriptfilepath)
scriptpadirpath = os.path.dirname(scriptdirpath)

os.chdir(scriptdirpath)
os.environ.update(d(GIT_WORK_TREE=scriptdirpath))

DPL_TMPDIR = None
with tempfile.TemporaryDirectory(
        prefix='dply_tsbx_' + datetime.datetime.now().strftime("%m%d_%H%M%S%f") + '__' ,
        dir="/tmp", delete=True
    ) as temp_dir:
    DPL_TMPDIR = temp_dir
    main()
