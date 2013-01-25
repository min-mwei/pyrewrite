from functools import partial

from rewrite import matching
from rewrite.matching import free, freev
import rewrite.astnodes as ast

from parse import dslparse
import combinators as comb

def nameof(cls):
    return cls.__class__.__name__

combinators = {
    'fail'      : comb.fail,
    'id'        : comb.Id,
    'repeat'    : comb.Repeat,
    'all'       : comb.All,
    'some'      : comb.Some,
    '<+'        : comb.Choice,
    ';'         : comb.Seq,
    'try'       : comb.Try,
    'topdown'   : comb.Topdown,
    'bottomup'  : comb.Bottomup,
    'innermost' : comb.Innermost,
    'debug'     : comb.Debug,
}

#------------------------------------------------------------------------
# Exceptions
#------------------------------------------------------------------------

class NoMatch(Exception):
    pass

#------------------------------------------------------------------------
# Strategies
#------------------------------------------------------------------------

class Strategy(object):

    def __init__(self, combinator, expr):
        self.subrules = [a.rewrite for a in expr]
        self.names = [nameof(a) for a in expr]

        try:
            self.combinator = combinator(*self.subrules)
        except TypeError:
            raise TypeError, 'Wrong number of arguments to combinator: %s'\
                % str(combinator)

    def __call__(self, o):
        return self.combinator(o)

    rewrite = __call__

    def __repr__(self):
        return '%s(%s)' % (
            self.combinator.__class__.__name__,
            self.names
        )

class Rule(object):
    def __init__(self, symtab, lpat, rpat, matcher, builder):
        self.matcher = matcher
        self.symtab = symtab
        self.builder = builder
        self.lpat = lpat
        self.rpat = rpat

    def rewrite(self, pattern):
        # This is transliteration of some OCaml code
        b = {} # bindings

        matches, captured = self.matcher(pattern)
        if matches:

            # Short circuit for trivial rewrites
            if len(self.rpat) == 0 and len(self.lpat) == 0:
                return self.builder([])

            # Pattern match and ensure binding equality constraint
            for i,el in enumerate(captured):
                vi = self.lpat[i]
                if vi in b:
                    if b[vi] != el:
                        raise NoMatch()
                    else:
                        pass
                else:
                    b[self.lpat[i]] = el
            values = [b[j] for j in self.rpat]
            # TODO; prepend
            return self.builder(reversed(values))
        else:
            raise NoMatch()

    def __call__(self, pattern):
        return self.rewrite(pattern)

    def __repr__(self):
        return '%r -> %r' % (self.lpat, self.rpat)

class RuleBlock(object):
    def __init__(self, rules=None):
        self.rules = rules or []

    def add(self, rule):
        self.rules.append(rule)

    def rewrite(self, pattern):
        for rule in self.rules:
            try:
                return rule.rewrite(pattern)
            except NoMatch:
                continue
        raise NoMatch()

    def __call__(self, pattern):
        return self.rewrite(pattern)

    def __repr__(self):
        out = '[\n'
        for rule in self.rules:
            out += ' '*4 + repr(rule) + '\n'
        out += ']\n'
        return out

#------------------------------------------------------------------------
# Buld Automata
#------------------------------------------------------------------------

def build_strategy(label, env, comb, args):
    env = env.copy() # mutable state is evil
    self = object() # forward declaration since rules can be self-recursive
    comb = combinators[comb]

    sargs = []

    for arg in args:
        # composition of combinators
        if isinstance(arg, tuple):
            subcomb, subargs = arg
            sargs.append(build_strategy(None, env, subcomb, subargs))

        if isinstance(arg, list):
            for iarg in arg:
                # look up the corresponding rewrite rule or
                # rewrite block and pass the rewrite hook to the
                # strategy combinator
                rr = env[iarg.term]
                sargs.append(rr)

    return Strategy(comb, sargs)


def build_rule(l, r):
    i,j = 0, 0

    lpat = []
    rpat = []

    symtab = {}

    for v in free(l):
        if v in symtab:
            lpat.append(symtab[v])
        else:
            symtab[v] = i
            lpat.append(i)
            i += 1

    for v in free(r):
        if v in symtab:
            rpat.append(symtab[v])
        else:
            raise Exception('Unbound variable: %s' % v)

    matcher = partial(matching.match, freev(l))
    builder = partial(matching.build, freev(r))

    rr = Rule(symtab, lpat, rpat, matcher, builder)
    return rr

#------------------------------------------------------------------------
# Module Constructions
#------------------------------------------------------------------------

def module(s, _env=None):
    defs = dslparse(s)

    if _env:
        env = _env.copy()
    else:
        env = {}

    for df in defs:

        if isinstance(df, ast.RuleNode):

            label, l, r = df
            rr = build_rule(l, r)

            if label in env:
                env[label].add(rr)
            else:
                env[label] = RuleBlock([rr])

        elif isinstance(df, ast.StrategyNode):
            label, comb, args = df

            if label in env:
                raise Exception, "Strategy definition '%s' already defined" % label

            st = build_strategy(label, env, comb, args)
            env[label] = st

        else:
            raise NotImplementedError

    return env
