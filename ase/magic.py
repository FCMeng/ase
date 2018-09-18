import warnings

import numpy as np

from ase.data import atomic_numbers, chemical_symbols
from ase.utils import basestring, formula_hill, formula_metal


class Symbols:
    def __init__(self, numbers):
        self.numbers = numbers

    def __getitem__(self, key):
        num = self.numbers[key]
        if np.isscalar(num):
            return chemical_symbols[num]
        return Symbols(num)

    def __setitem__(self, key, value):
        if isinstance(value, basestring):
            Z = atomic_numbers[value]
        else:
            Z = [atomic_numbers[v] for v in value]

        self.numbers[key] = Z

    def __len__(self):
        return len(self.numbers)

    def __repr__(self):
        return 'Symbols(\'{}\')'.format(self.get_chemical_formula())

    def get_chemical_formula(self, mode='hill', empirical=False):
        if mode in ('reduce', 'all') and empirical:
            warnings.warn("Empirical chemical formula not available "
                          "for mode '{}'".format(mode))

        if len(self) == 0:
            return ''
        numbers = self.numbers

        if mode == 'reduce':
            n = len(numbers)
            changes = np.concatenate(([0], np.arange(1, n)[numbers[1:] !=
                                                           numbers[:-1]]))
            symbols = [chemical_symbols[e] for e in numbers[changes]]
            counts = np.append(changes[1:], n) - changes

            formula = ''
            for s, c in zip(symbols, counts):
                formula += s
                if c > 1:
                    formula += str(c)
        elif mode == 'hill':
            formula = formula_hill(numbers,
                                   empirical=empirical)
        elif mode == 'all':
            symbols = [chemical_symbols[n] for n in numbers]

            formula = ''
            for s in symbols:
                formula += s
        elif mode == 'metal':
            formula = formula_metal(self.get_atomic_numbers(),
                                    empirical=empirical)
        else:
            raise ValueError("Use mode = 'all', 'reduce', 'hill' or 'metal'.")

        return formula
