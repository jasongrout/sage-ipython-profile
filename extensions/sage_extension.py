"""
A Sage extension which adds sage-specific features:

* magics
  - %load: alias to IPython's %run
  - %attach
  - %mode (like %cython, %maxima, etc.)
* preparsing of input
  - also make load and attach magics so that the '%' is optional (should we just turn on that optino to IPython?)
* loading Sage library
* running init.sage
* changing prompt to Sage prompt (should we have input/output numbers too?)
* Crash handler

"""

from IPython.core.hooks import TryNext
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.plugin import Plugin

@magics_class
class SageMagics(Magics):
    def __init__(self, *a, **kw):
        super(SageMagics, self).__init__(*a, **kw)
        self.attach = []
        
    @line_magic
    def attach(self, filename=''):
        r"""%attach => run the code each time before starting up.
        """
        print 'Attaching %s'%(filename,)
        self.attach.append(filename)
        
    def pre_run_code_hook(self, ip):
        print 'TODO: load attached files: %s'%(self.attach,)
        raise TryNext

class SagePlugin(Plugin):
    def __init__(self, shell=None, config=None):
        super(SagePlugin, self).__init__(shell=shell, config=config)
        self.auto_magics = SageMagics(shell)
        shell.register_magics(self.auto_magics)
        shell.magics_manager.register_alias('load','run')
        shell.set_hook('pre_run_code_hook', self.auto_magics.pre_run_code_hook)

from IPython.core.inputsplitter import IPythonInputSplitter

try:
    import sage
    import sage.all
    from sage.misc.interpreter import SageInputSplitter
    class SageIPythonInputSplitter(SageInputSplitter, IPythonInputSplitter):
        """
        This class merely exists so that the IPKernelApp.kernel.shell class does not complain.  It requires
        a subclass of IPythonInputSplitter, but SageInputSplitter is a subclass of InputSplitter instead.
        """
        pass
except ImportError as e:
    print e
    SageIPythonInputSplitter = None


# from http://stackoverflow.com/questions/4103773/efficient-way-of-having-a-function-only-execute-once-in-a-loop
from functools import wraps
def run_once(f):
    """Runs a function (successfully) only once.

    The running can be reset by setting the `has_run` attribute to False
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            return f(*args, **kwargs)
            wrapper.has_run = True
    wrapper.has_run = False
    return wrapper

@run_once
def load_ipython_extension(ip):
    """Load the extension in IPython."""
    plugin = SagePlugin(shell=ip, config=ip.config)
    ip.plugin_manager.register_plugin('sage', plugin)
    ip.input_splitter = SageIPythonInputSplitter()
