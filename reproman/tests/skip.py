# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the reproman package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Define `skipif` and `mark` namespaces for custom pytest skippers.

There are two main ways to skip in pytest:

  * decorating a test function, such as

        @pytest.mark.skip(sys.platform.startswith("win"), reason="on windows")
        def test_func():
            [...]

  * skipping inline, such as

        def test_func():
            if sys.platform.startswith("win"):
                pytest.skip("on Windows")
            [...]

This module provides a mechanism to register a reason and condition as both a
decorator and an inline function:

  * Within this module, create a condition function that returns a tuple of the
    form (REASON, COND). REASON is a str that will be shown as the reason for
    the skip, and COND is a boolean indicating if the test should be skipped.

    For example

    def windows():
        return "on windows", sys.platform.startswith("win")

  * Then add the above function to CONDITION_FNS.

Doing that will make the skip condition available in two places:
`mark.skipif_NAME` and `skipif.NAME`. So, for the above example, there would
now be `mark.skipif_windows` and `skipif.windows`.
"""
import abc
import os

import pytest

from reproman.resource.docker_container import DockerContainer
from reproman.support.external_versions import external_versions
from reproman.utils import on_windows as _on_windows

# Condition functions
#
# To create a new condition, (1) add a condition function and (2) add that
# function to CONDITION_FNS.


def no_apt_cache():
    return ("apt-cache not available",
            not external_versions["cmd:apt-cache"])


def no_docker_engine():
    return ("No Docker",
            not DockerContainer.is_engine_running())


def no_network():
    return ("no network settings",
            os.environ.get('REPROMAN_TESTS_NONETWORK'))


def no_singularity():
    return ("singularity not available",
            not external_versions["cmd:singularity"])


def no_ssh():
    if _on_windows:
        reason = "no ssh on windows"
    else:
        reason = "no ssh (REPROMAN_TESTS_SSH unset)"
    return (reason,
            _on_windows or not os.environ.get('REPROMAN_TESTS_SSH'))


def no_svn():
    return ("subversion not available",
            not external_versions["cmd:svn"])


def on_windows():
    return "on windows", _on_windows


CONDITION_FNS = [
    no_apt_cache,
    no_docker_engine,
    no_network,
    no_singularity,
    no_ssh,
    no_svn,
    on_windows,
]

# Entry points: skipif and mark


class Namespace(object, metaclass=abc.ABCMeta):
    """Provide namespace skip conditions in CONDITION_FNS.
    """

    fns = {c.__name__: c for c in CONDITION_FNS}

    @abc.abstractmethod
    def attr_value(self, condition_func):
        """Given a condition function, return an attribute value.
        """

    def __getattr__(self, item):
        try:
            condfn = self.fns[item]
        except KeyError:
            raise AttributeError(item) from None
        return self.attr_value(condfn)


class SkipIf(Namespace):
    """Namespace for inline variants of the condition functions.

    Each condition is available under an attribute with the same name as the
    condition function name.
    """

    def attr_value(self, condition_func):
        def fn():
            reason, cond = condition_func()
            if cond:
                pytest.skip(reason, allow_module_level=True)
        return fn


skipif = SkipIf()


class Mark(Namespace):
    """Namespace for mark variants of the condition functions.

    Each condition is available under an attribute "skipif_NAME", where NAME is
    the condition function name.
    """

    def attr_value(self, condition_func):
        reason, cond = condition_func()
        return pytest.mark.skipif(cond, reason=reason)

    def __getattr__(self, item):
        if item.startswith("skipif_"):
            try:
                return super(Mark, self).__getattr__(item[len("skipif_"):])
            except AttributeError:
                # Fall back to the original item name so that the attribute
                # error message doesn't confusingly drop "skipif_".
                pass
        return super(Mark, self).__getattr__(item)


mark = Mark()