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
* exit hook (call quit_sage())
* Display hook


TODO:
* Crash handler -- change the crash text.  This may need a new app, based on TerminalApp, rather than something we change here!

* interactivity -- all???  I thought we had `last_expr`
"""

from IPython.core.hooks import TryNext
from IPython.core.magic import Magics, magics_class, line_magic
from IPython.core.plugin import Plugin
import os
import sys
import sage
import sage.all
from sage.all import quit_sage

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
        import traceback
        #print traceback.print_stack()
        raise TryNext

from IPython.core.formatters import PlainTextFormatter
class SagePlainTextFormatter(PlainTextFormatter):
    """
    A replacement for ``sys.displayhook`` which correctly print lists
    of matrices.

    EXAMPLES::

        sage: from sage.misc.interpreter import SageDisplayHook, get_test_shell
        sage: shell = get_test_shell()
        sage: shell.displayhook
        <sage.misc.interpreter.SageDisplayHook object at 0x...>
        sage: shell.run_cell('a = identity_matrix(ZZ, 2); [a,a]')
        [
        [1 0]  [1 0]
        [0 1], [0 1]
        ]
    """
    def __call__(self, obj):
        r"""
        Computes the format data of ``result``.  If the
        :func:`sage.misc.displayhook.print_obj` writes a string, then
        we override IPython's :class:`DisplayHook` formatting.

        EXAMPLES::

            sage: from sage.misc.interpreter import get_test_shell
            sage: shell = get_test_shell()
            sage: shell.displayhook
            <sage.misc.interpreter.SageDisplayHook object at 0x...>
            sage: shell.displayhook.compute_format_data(2)
            {u'text/plain': '2'}
            sage: a = identity_matrix(ZZ, 2)
            sage: shell.displayhook.compute_format_data([a,a])
            {u'text/plain': '[\n[1 0]  [1 0]\n[0 1], [0 1]\n]'}
        """
        from cStringIO import StringIO
        s = StringIO()
        import sage
        from sage.misc.displayhook import print_obj
        print_obj(s, obj)
        if s:
            return s.getvalue().strip()
        else:
            return super(SagePlainTextFormatter, self).__call__(obj)



class SagePlugin(Plugin):
    startup_code = """from sage.all import *
from sage.calculus.predefined import x
from sage.misc.html import html
from sage.server.support import help
from sagenb.misc.support import automatic_names
"""

    def __init__(self, shell=None, config=None):
        super(SagePlugin, self).__init__(shell=shell, config=config)
        self.shell = shell
        os.chdir(os.environ["CUR"])

        self.auto_magics = SageMagics(shell)
        shell.register_magics(self.auto_magics)
        shell.magics_manager.register_alias('load','run')
        shell.set_hook('pre_run_code_hook', self.auto_magics.pre_run_code_hook)
        shell.display_formatter.formatters['text/plain'] = SagePlainTextFormatter(config=config)
        from sage.misc.edit_module import edit_devel
        self.shell.set_hook('editor', edit_devel)
        self.init_inspector()
        self.init_line_transforms()
        self.set_quit_hook()
        self.register_interface_magics()

        self.print_branch()

        # These are things I'm not sure that we need to do anymore
        #self.deprecated()


        if os.environ.get('SAGE_IMPORTALL', 'yes') != 'yes':
            return

        self.init_environment()

    def register_interface_magics(self):
        """Register magics for each of the Sage interfaces"""
        interfaces = sorted([ obj.name()
                              for obj in sage.interfaces.all.__dict__.values() 
                              if isinstance(obj, sage.interfaces.interface.Interface) ])
        for name in interfaces:
            def tmp(line,name=name):
                self.shell.run_cell('%s.interact()'%name)
            tmp.__doc__="Interact with %s"%name
            self.shell.register_magic_function(tmp, magic_name=name)

    def set_quit_hook(self):
        def quit(shell):
            quit_sage()
        self.shell.set_hook('shutdown_hook', quit)

    def print_branch(self):
        from sage.misc.misc import branch_current_hg_notice, branch_current_hg
        branch = branch_current_hg_notice(branch_current_hg())
        if branch and self.test_shell is False:
            print branch

    def init_environment(self):
        """
        Set up Sage command-line environment
        """
        try:
            self.shell.run_cell('from sage.all import Integer, RealNumber')
        except Exception:
            import traceback
            print "Error importing the Sage library"
            traceback.print_exc()
            print
            print "To debug this, you can run:"
            print 'sage -ipython -i -c "import sage.all"'
            print 'and then type "%debug" to enter the interactive debugger'
            sys.exit(1)

        self.shell.run_cell('from sage.all_cmdline import *')
        self.run_init()

        
    def run_init(self):
        startup_file = os.environ.get('SAGE_STARTUP_FILE', '')
        if os.path.exists(startup_file):
            self.shell.run_cell('%%run "%s"'%startup_file)

    def init_inspector(self):
        # Ideally, these would just be methods of the Inspector class
        # that we could override; however, IPython looks them up in
        # the global :class:`IPython.core.oinspect` module namespace.
        # Thus, we have to monkey-patch.
        from sage.misc import sagedoc, sageinspect
        import IPython.core.oinspect
        IPython.core.oinspect.getdoc = sageinspect.sage_getdoc #sagedoc.my_getdoc
        IPython.core.oinspect.getsource = sagedoc.my_getsource
        IPython.core.oinspect.getargspec = sageinspect.sage_getargspec

    def init_line_transforms(self):
        import sage
        import sage.all
        from sage.misc.interpreter import (SagePromptDedenter, SagePromptTransformer,  InterfaceMagicTransformer,
                                           LoadAttachTransformer, SagePreparseTransformer)
        self.shell.input_splitter.transforms.extend([SagePromptDedenter(),
                                                     SagePromptTransformer(), 
                                                     #InterfaceMagicTransformer(),
                                                     LoadAttachTransformer(), 
                                                     SagePreparseTransformer() ])
        #preparser(True)


    def deprecated(self):
        """
        These are things I don't think we need to do anymore; are they used?
        """
        self.shell.push(dict(sage_prompt=sage_prompt))

        # I'm not sure this is ever needed; when would this not be ''?
        if sys.path[0]!='':
            sys.path.insert(0, '')

# from http://stackoverflow.com/questions/4103773/efficient-way-of-having-a-function-only-execute-once-in-a-loop
from functools import wraps
def run_once(f):
    """Runs a function (successfully) only once.

    The running can be reset by setting the `has_run` attribute to False
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            result = f(*args, **kwargs)
            wrapper.has_run = True
            return result
    wrapper.has_run = False
    return wrapper

@run_once
def load_ipython_extension(ip):
    """Load the extension in IPython."""
    plugin = SagePlugin(shell=ip, config=ip.config)
    ip.plugin_manager.register_plugin('sage', plugin)
    

r'''
        This method loads all modified attached files before executing
        any code.  Any arguments and keyword arguments are passed to
        :meth:`TerminalInteractiveShell.run_cell`.

        EXAMPLES::

            sage: import os
            sage: from sage.misc.interpreter import get_test_shell
            sage: from sage.misc.misc import tmp_dir
            sage: shell = get_test_shell()
            sage: tmp = os.path.join(tmp_dir(), 'run_cell.py')
            sage: f = open(tmp, 'w'); f.write('a = 2\n'); f.close()
            sage: shell.run_cell('%attach ' + tmp)
            sage: shell.run_cell('a')
            2
            sage: import time; time.sleep(1)
            sage: f = open(tmp, 'w'); f.write('a = 3\n'); f.close()
            sage: shell.run_cell('a')
            3
            sage: os.remove(tmp)
        """
        """
        We need to run the :func:`sage.all.quit_sage` function when we
        exit the shell.

        EXAMPLES:

        We install a fake :func:`sage.all.quit_sage`::
        
            sage: import sage.all
            sage: old_quit = sage.all.quit_sage
            sage: def new_quit(): print "Quitter!!!"
            sage: sage.all.quit_sage = new_quit

        Now, we can check to see that this method works::
        
            sage: from sage.misc.interpreter import get_test_shell
            sage: shell = get_test_shell()
            sage: shell.ask_exit()
            Quitter!!!
            sage: shell.exit_now
            True

        Clean up after ourselves::

            sage: shell.exit_now = False
            sage: sage.all.quit_sage = old_quit
        """
'''
