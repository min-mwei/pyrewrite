from parse import _init, parse
from terms import *

placeholders = {
    'appl': aappl,
    'str': astr,
    'int': aint,
    'real': areal,
    'term': (aterm, aappl, astr, aint, areal),
    'placeholder': aplaceholder,
    #'list' : alist
}

def init(xs):
    for x in xs:
        return x

def tail(xs):
    for x in reversed(xs):
        return x

def aterm_zip(a, b):
    if isinstance(a, (aint, areal, astr)) and isinstance(b, (aint, areal, astr)):
        yield a.val == b.val, None

    elif isinstance(a, aappl) and isinstance(b, aappl):
        if len(a.args) == len(b.args):
            yield a.spine == b.spine, None
            for ai, bi in zip(a.args, b.args):
                for aj in aterm_zip(ai,bi):
                    yield aj
        else:
            yield False, None

    elif isinstance(a, aterm) and isinstance(b, aterm):
        yield a.term == b.term, None
        yield a.annotation == b.annotation, None

    elif isinstance(a, aplaceholder):
        # <appl(...)>
        if a.args:
            if isinstance(b, aappl):
                yield True, b.spine
                for ai, bi in zip(a.args, b.args):
                    for a in aterm_zip(ai,bi):
                        yield a
            else:
                yield False, None
        # <term>
        else:
            yield isinstance(b, placeholders[a.type]), b
    else:
        yield False, None


def aterm_splice(a, elts):
    elts = elts[:]

    if isinstance(a, (aint, areal, astr)):
        yield a

    elif isinstance(a, aappl):
        # ugly
        yield aappl(a.spine, [init(aterm_splice(ai,elts)) for ai in a.args])

    elif isinstance(a, aterm):
        yield a

    elif isinstance(a, aplaceholder):
        # <appl(...)>
        if a.args:
            # ugly
            yield aappl(elts.pop(), [init(aterm_splice(ai,elts)) for ai in a.args])
        # <term>
        else:
            yield elts.pop()
    else:
        raise NotImplementedError

def free(a):
    if isinstance(a, (aint, areal, astr)):
        pass

    elif isinstance(a, aappl):
        for ai in a.args:
            for aj in free(ai):
                yield aj

    elif isinstance(a, aterm):
        yield a.term

    elif isinstance(a, (alist,atupl)):
        for ai in a.args:
            for aj in free(ai):
                yield aj

    else:
        raise NotImplementedError


def freev(a):
    if isinstance(a, (aint, areal, astr)):
        return a

    elif isinstance(a, aappl):
        # ugly
        return aappl(a.spine, [freev(ai) for ai in a.args])

    elif isinstance(a, aterm):
        return aplaceholder('term', None)

    else:
        raise NotImplementedError


def match(pattern, subject, *captures):
    parser = _init()

    captures = []

    p = parser.parse(pattern)
    s = parser.parse(subject)

    for matches, capture in aterm_zip(p,s):
        if not matches:
            return False, []
        elif matches and capture:
            captures += [capture]
    return True, captures

def matches(pattern, subject):
    parser = _init()

    p = parser.parse(pattern)
    s = parser.parse(subject)

    for matches, capture in aterm_zip(p,s):
        if not matches:
            return False
    return True

def build(pattern, values):
    parser = _init()
    vals = list(values)

    p = parser.parse(pattern)
    return list(aterm_splice(p,vals))
