"""
"""
from __future__ import division, absolute_import, print_function
import re
from ast import literal_eval
from collections import Iterable


__all__ = ['argsort', 'flatten', 'parse_list_literal']


FORMAT_STRING_PATTERN = r'^\%[-]?(\d+)?(?:\.(\d+))?([defs])$'

RES_TYPE_NAME_PATTERN = r'[A-Z+?]'
RES_NUM_NAME_PATTERN = r'(?:[?]|\d+)'
RES_NAME_PATTERN = ('^'
                    + '(' + RES_TYPE_NAME_PATTERN + ')'
                    + '(' + RES_NUM_NAME_PATTERN + ')'
                    + '$')
ATOM_NAME_PATTERN = r'(?:[?]|[A-Z]+[\d]*(?:[-+]\d)?)'
SPARKY_ATOM_NAME_PATTERN = r'(?:[?]|[A-Z]+[\d]*(?:[mp]\d)?)'
NAME_PATTERN = ('^'
                + '(' + RES_TYPE_NAME_PATTERN
                + RES_NUM_NAME_PATTERN + ')'
                + '-'
                + '(' + ATOM_NAME_PATTERN + ')'
                + '$')
SPARKY_NAME_PATTERN = ('^'
                       + '(' + RES_TYPE_NAME_PATTERN
                       + RES_NUM_NAME_PATTERN + ')'
                       + '(' + SPARKY_ATOM_NAME_PATTERN + ')'
                       + '$')

ANCHOR_NAME_PATTERN = ('^'
                       + '(' + RES_TYPE_NAME_PATTERN
                       + RES_NUM_NAME_PATTERN + ')'
                       + '-'
                       + '(' + ATOM_NAME_PATTERN + ')'
                       + '/'
                       + '(' + ATOM_NAME_PATTERN + ')'
                       + '$')

AA_1TO3 = {'A': 'ALA', 'C': 'CYS', 'D': 'ASP', 'E': 'GLU', 'F': 'PHE',
           'G': 'GLY', 'H': 'HIS', 'I': 'ILE', 'K': 'LYS', 'L': 'LEU',
           'M': 'MET', 'N': 'ASN', 'P': 'PRO', 'Q': 'GLN', 'R': 'ARG',
           'S': 'SER', 'T': 'THR', 'V': 'VAL', 'W': 'TRP', 'Y': 'TYR'}
AA_3TO1 = {v: k for k, v in AA_1TO3.items()}


def argsort(new_indices):
    """
    """
    order = [(new, old) for old, new in enumerate(new_indices)]
    old_indices = [old for new, old in sorted(order)]
    return old_indices


def flatten(item):
    """
    Flatten nested iterables while maintaining intact strings.

    Parameters
    ----------
    item : iterable object
        Nested iterable to flatten

    Returns
    -------
    out : generator
        A generator for the fully flattened iterable

    Examples
    --------
    >>> a = [1,[2,3],[['foo',5],'bar']]
    >>> list(flatten(a))
    [1, 2, 3, 'foo', 5, 'bar']
    """
    if isinstance(item, Iterable) and not isinstance(item, str):
        for element in item:
            for sub in flatten(element):
                yield sub
    else:
        yield item


def parse_list_literal(string):
    """
    """
    single_list = r'(\[.*\])'
    list_mult = r'(\*\d+)?'
    pattern = '^' + single_list + list_mult + '$'
    final_list = []
    lists_to_add = string.split('+')
    for lst in lists_to_add:
        match = re.match(pattern, lst)
        if match is None:
            raise ValueError('mis-formatted list literal')
        lst = literal_eval(match.group(1))
        if match.group(2) is not None:
            mult = int(match.group(2).lstrip('*'))
            lst = lst * mult
        final_list += lst
    return final_list
