"""
"""
from __future__ import division, absolute_import, print_function
try:
    from itertools import izip as zip
    from itertools import izip_longest as zip_longest
except ImportError:
    pass
import re
from sys import stderr
from inspect import getargspec
from copy import deepcopy
from itertools import permutations
from collections import Iterable, MutableSequence
from .utils import ANCHOR_NAME_PATTERN, AA_1TO3, AA_3TO1


__all__ = ['Column', 'IgnoreColumn', 'PeakAttrColumn', 'PeakAttrListColumn',
           'SpinAttrColumn', 'Res3LetterColumn', 'PipeNameColumn',
           'PipeAnchorColumn', 'SparkyNameColumn', 'ColumnGroup',
           'PeakAttrListGroup', 'SpinAttrGroup', 'PipeNameGroup',
           'ColumnTemplate', 'PipeTemplate', 'SparkyTemplate', 'UplTemplate',
           'XeasyTemplate']


class Column(object):
    """
    Represent a peak list column and map its data to Peak objects

    Provide a base class for representing peak list columns and define an
    interface for mapping column data to Peak objects.

    Parameters
    ----------
    name : str
        Name of the peak list column, should be unique within a peak list
    fmt : str
        printf-style format string specifying how the data should be printed
    """
    types = {'d': int, 'e': float, 'f': float, 's': str}
    _sentinel = object()

    def __init__(self, name, fmt):
        self.name = name
        self.fmt = fmt

    def __repr__(self):
        name = type(self).__name__
        init_args, _, _, _ = getargspec(self.__init__)
        vrs = vars(self)
        pairs = [repr(vrs[arg]) for arg in init_args[1:]]
        rpr = name + '(' + ', '.join(pairs) + ')'
        return rpr

    def get_value(self, peak, default=_sentinel):
        """
        get_value(peak[, default])

        Get the appropriate column data from a Peak object

        Return the value from the Peak object corresponding to the associated
        peak list column. Each subclass must provide its own definition of
        this interface.

        Parameters
        ----------
        peak : :class:`~.peaklist.Peak`
            Peak object containing the corresponding column data
        default : optional
            If the Peak does not contain the corresponding data, return
            ``default`` if provided, otherwise raise an Exception.

        Returns
        -------
        value
            The column value taken from the Peak object
        """
        raise NotImplementedError

    def set_value(self, peak, value):
        """
        Set the appropriate value in a Peak object from peak list column data

        Set the value in the Peak object corresponding to the associated peak
        list column. Each subclass must provide its own definition of this
        interface.

        Parameters
        ----------
        peak : :class:`~.peaklist.Peak`
            Peak object in which to set the column data
        value
            The column value to set in the Peak object
        """
        raise NotImplementedError

    def get_string(self, peak):
        """
        Get column data from a Peak object and return a formatted string

        Return a formatted string representing the value from the Peak object
        corresponding to the associated peak list column.

        Parameters
        ----------
        peak : :class:`~.peaklist.Peak`
            Peak object containing the corresponding column data

        Returns
        -------
        value : str
            A formatted string of the column data for the Peak object
        """
        return self.fmt % self.get_value(peak)

    def set_string(self, peak, string):
        """
        Set the appropriate value in a Peak object from a formatted string

        Set the value in the Peak object corresponding to the associated peak
        list column based on a formatted string.

        Parameters
        ----------
        peak : :class:`~.peaklist.Peak`
            Peak object in which to set the column data
        string : str
            Formatted string of the column data to set in the Peak object
        """
        if self.fmt is None:
            self.set_value(peak, string)
        else:
            try:
                typ = Column.types[self.fmt[-1]]
            except KeyError:
                err = 'invalid format string {!r}'.format(self.fmt)
                raise AttributeError(err)
            self.set_value(peak, typ(string))

    def update_from_peaklist(self, peaklist):
        return self


class IgnoreColumn(Column):
    """
    """
    def __init__(self, name, string):
        fmt = '%{:d}s'.format(len(string))
        super(IgnoreColumn, self).__init__(name, fmt)
        self.string = string

    def get_value(self, peak, default=Column._sentinel):
        return self.string

    def set_value(self, peak, value):
        pass

    def get_string(self, peak):
        return self.string

    def set_string(self, peak, string):
        pass


class PeakAttrColumn(Column):
    """
    """
    def __init__(self, name, fmt, attr):
        super(PeakAttrColumn, self).__init__(name, fmt)
        self.attr = attr

    def get_value(self, peak, default=Column._sentinel):
        try:
            value = getattr(peak, self.attr)
        except AttributeError as err:
            if default is Column._sentinel:
                raise err
            else:
                return default
        else:
            return value

    def set_value(self, peak, value):
        setattr(peak, self.attr, value)


class PeakAttrListColumn(Column):
    """
    """
    def __init__(self, name, fmt, attr, index, length=None):
        super(PeakAttrListColumn, self).__init__(name, fmt)
        self.attr = attr
        self.index = index
        self.length = length if length is not None else index + 1

    def get_value(self, peak, default=Column._sentinel):
        try:
            value = getattr(peak, self.attr)[self.index]
        except (AttributeError, TypeError, IndexError) as err:
            if default is Column._sentinel:
                raise err
            else:
                return default
        else:
            return value

    def set_value(self, peak, value):
        try:
            getattr(peak, self.attr)[self.index] = value
        except (AttributeError, TypeError):
            lst = [None] * self.length
            lst[self.index] = value
            setattr(peak, self.attr, lst)
        except IndexError:
            lst = getattr(peak, self.attr)
            pad = self.length - len(lst)
            lst += [None] * pad
            lst[self.index] = value


class SpinAttrColumn(Column):
    """
    """
    def __init__(self, name, fmt, attr, index):
        super(SpinAttrColumn, self).__init__(name, fmt)
        self.attr = attr
        self.index = index

    def get_value(self, peak, default=Column._sentinel):
        try:
            value = getattr(peak[self.index], self.attr)
        except (AttributeError, IndexError) as err:
            if default is Column._sentinel:
                raise err
            else:
                return default
        else:
            return value

    def set_value(self, peak, value):
        setattr(peak[self.index], self.attr, value)


class Res3LetterColumn(SpinAttrColumn):
    """
    """
    def __init__(self, name, index):
        fmt = '%3s'
        attr = 'res_type'
        super(Res3LetterColumn, self).__init__(name, fmt, attr, index)

    def get_string(self, peak):
        value = self.get_value(peak)
        try:
            string = AA_1TO3[value]
        except KeyError:
            err = ("can't get 3-letter amino acid string for unassigned "
                   "spin in peak: {!r}".format(peak))
            raise ValueError(err)
        return string

    def set_string(self, peak, string):
        try:
            value = AA_3TO1[string]
        except KeyError:
            err = ("can't get 1-letter amino acid string for unassigned "
                   "spin in peak: {!r}".format(peak))
            raise ValueError(err)
        self.set_value(peak, value)


class PipeNameColumn(SpinAttrColumn):
    """
    """
    def __init__(self, index, res_width=4, atom_width=4):
        letter = 'XYZA'[index]
        name = letter + '_NAME'
        fmt = None
        attr = 'name'
        super(PipeNameColumn, self).__init__(name, fmt, attr, index)
        self.res_width = res_width
        self.atom_width = atom_width

    @property
    def fmt(self):
        fmt = '%{:d}s'.format(self.res_width + self.atom_width + 1)
        return fmt

    @fmt.setter
    def fmt(self, value):
        pass

    def get_value(self, peak, default=Column._sentinel):
        try:
            spin = peak[self.index]
        except IndexError as err:
            if default is Column._sentinel:
                raise err
            else:
                return default
        else:
            value = spin.name
            return value

    def get_string(self, peak):
        value = self.get_value(peak)
        spin = peak[self.index]
        pad_left = self.res_width - len(spin.res_name)
        pad_right = self.atom_width - len(spin.atom_name)
        string = (' ' * pad_left) + value + (' ' * pad_right)
        return string

    def update_from_peaklist(self, peaklist):
        spins = [peak[self.index] for peak in peaklist]
        self.res_width = max(len(spin.res_name) for spin in spins)
        self.atom_width = max(len(spin.atom_name) for spin in spins)
        return self


class PipeAnchorColumn(Column):
    """
    """
    def __init__(self, indices, res_width=4, atom_width=8):
        letters = ''.join('XYZA'[i] for i in indices)
        name = letters + '_NAME'
        fmt = None
        super(PipeAnchorColumn, self).__init__(name, fmt)
        self.indices = indices
        self.res_width = res_width
        self.atom_width = atom_width

    @property
    def fmt(self):
        fmt = '%{:d}s'.format(self.res_width + self.atom_width + 2)
        return fmt

    @fmt.setter
    def fmt(self, value):
        pass

    def get_value(self, peak, default=Column._sentinel):
        try:
            spn1, spn2 = (peak[i] for i in self.indices)
            if spn1.res_name != spn2.res_name:
                err = ('anchors spins not in same residue: '
                       '{!r} & {!r}'.format(spn1, spn2))
                raise ValueError(err)
        except (IndexError, ValueError) as err:
            if default is Column._sentinel:
                raise err
            else:
                return default
        else:
            value = spn1.res_name + '-' + spn1.atom_name + '/' + spn2.atom_name
            return value

    def set_value(self, peak, value):
        match = re.match(ANCHOR_NAME_PATTERN, value.strip())
        if match is None:
            raise ValueError('invalid anchor name: {!r}'.format(value))
        spin1, spin2 = (peak[i] for i in self.indices)
        spin1.res_name = match.group(1)
        spin2.res_name = match.group(1)
        spin1.atom_name = match.group(2)
        spin2.atom_name = match.group(3)

    def get_string(self, peak):
        value = self.get_value(peak)
        spin1, spin2 = (peak[i] for i in self.indices)
        pad_left = self.res_width - len(spin1.res_name)
        pad_right = self.atom_width - len(spin1.atom_name + spin2.atom_name)
        string = (' ' * pad_left) + value + (' ' * pad_right)
        return string

    def update_from_peaklist(self, peaklist):
        dims = [dim for dim in zip(*peaklist)]
        dims = [dims[i] for i in self.indices]
        res_widths = [max(len(spin.res_name) for spin in dim) for dim in dims]
        atom_widths = [max(len(spn.atom_name) for spn in dim) for dim in dims]
        self.res_width = max(res_widths)
        self.atom_width = sum(atom_widths)
        return self


class SparkyNameColumn(PeakAttrColumn):
    """
    """
    def __init__(self, fmt='%10s'):
        name = 'Assignment'
        attr = 'sparky_name'
        super(SparkyNameColumn, self).__init__(name, fmt, attr)

    def update_from_peaklist(self, peaklist):
        max_width = max(len(peak.sparky_name) for peak in peaklist)
        max_width = max_width if max_width > 10 else 10
        self.fmt = '%{:d}s'.format(max_width)
        return self


class ColumnGroup(object):
    """
    """
    def __init__(self):
        pass

    def __repr__(self):
        name = type(self).__name__
        init_args, _, _, _ = getargspec(self.__init__)
        vrs = vars(self)
        pairs = [repr(vrs[arg]) for arg in init_args[1:]]
        rpr = name + '(' + ', '.join(pairs) + ')'
        return rpr

    def generate_columns(self):
        raise NotImplementedError

    def resolve_from_names(self, names):
        raise NotImplementedError

    def resolve_from_peaklist(self, peaklist):
        raise NotImplementedError


class PeakAttrListGroup(ColumnGroup):
    """
    """
    def __init__(self, possible_names, fmt, attr):
        super(PeakAttrListGroup, self).__init__()
        self.possible_names = tuple(possible_names)
        self.fmt = fmt
        self.attr = attr

    def generate_columns(self, rng=None):
        rng = rng if rng is not None else range(len(self.possible_names))
        length = max(rng) + 1 if rng else 0
        columns = []
        fmt = self.fmt
        attr = self.attr
        for index in rng:
            name = self.possible_names[index]
            column = PeakAttrListColumn(name, fmt, attr, index, length)
            columns.append(column)
        return columns

    def resolve_from_names(self, names):
        found = set(names) & set(self.possible_names)
        indices = sorted(self.possible_names.index(name) for name in found)
        columns = self.generate_columns(indices)
        return columns

    def resolve_from_peaklist(self, peaklist):
        indices = []
        data_rows = [getattr(peak, self.attr, []) for peak in peaklist]
        for index, col in enumerate(zip_longest(*data_rows)):
            if any(data is None for data in col):
                if not all(data is None for data in col):
                    name = self.possible_names[index]
                    warn = ('Warning: some values None in column {}, '
                            'excluding it'.format(name))
                    print(warn, file=stderr)
                continue
            else:
                indices.append(index)
        columns = self.generate_columns(indices)
        return columns


class SpinAttrGroup(ColumnGroup):
    """
    """
    def __init__(self, possible_names, fmt, attr):
        super(SpinAttrGroup, self).__init__()
        self.possible_names = tuple(possible_names)
        self.fmt = fmt
        self.attr = attr

    def generate_columns(self, rng=None):
        rng = rng if rng is not None else range(len(self.possible_names))
        columns = []
        for index in rng:
            name = self.possible_names[index]
            column = SpinAttrColumn(name, self.fmt, self.attr, index)
            columns.append(column)
        return columns

    def resolve_from_names(self, names):
        found = set(names) & set(self.possible_names)
        indices = sorted(self.possible_names.index(name) for name in found)
        columns = self.generate_columns(indices)
        return columns

    def resolve_from_peaklist(self, peaklist):
        indices = []
        for index, spins in enumerate(zip(*peaklist)):
            values = [getattr(spin, self.attr, None) for spin in spins]
            if any(value is None for value in values):
                if not all(value is None for value in values):
                    name = self.possible_names[index]
                    warn = ('Warning: some values None in column {}, '
                            'excluding it'.format(name))
                    print(warn, file=stderr)
                continue
            else:
                indices.append(index)
        columns = self.generate_columns(indices)
        return columns


class PipeNameGroup(ColumnGroup):
    """
    """
    name_perms = [''.join(perm) for perm in permutations('XYZA', 2)]
    prefixes = ['X', 'Y', 'Z', 'A'] + name_perms
    possible_names = tuple(prefix + '_NAME' for prefix in prefixes)
    index_perms = [perm for perm in permutations((0, 1, 2, 3), 2)]
    dim_permutations = tuple([0, 1, 2, 3] + index_perms)
    del name_perms, prefixes, index_perms

    def __init__(self):
        super(PipeNameGroup, self).__init__()

    def generate_columns(self, dim_perms):
        columns = []
        for elem in dim_perms:
            if isinstance(elem, Iterable):
                columns.append(PipeAnchorColumn(elem))
            else:
                columns.append(PipeNameColumn(elem))
        return columns

    def resolve_from_names(self, names):
        possible_names = PipeNameGroup.possible_names
        dim_permutations = PipeNameGroup.dim_permutations
        found = set(names) & set(possible_names)
        indices = sorted(possible_names.index(name) for name in found)
        dim_perms = [dim_permutations[index] for index in indices]
        columns = self.generate_columns(dim_perms)
        return columns

    def resolve_from_peaklist(self, peaklist):
        columns = []
        anchors = peaklist.anchors
        anchored_dims = set(i for tupl in anchors for i in tupl)
        unanchored_dims = set(range(peaklist.dims)) - anchored_dims
        dim_perms = anchors + tuple(sorted(unanchored_dims))
        columns = self.generate_columns(dim_perms)
        return columns


class ColumnTemplate(MutableSequence):
    def __init__(self, columns=None):
        self._columns = []
        self._columns.extend(columns if columns is not None else [])

    def __len__(self):
        return len(self._columns)

    def __getitem__(self, i):
        return self._columns[i]

    def __setitem__(self, i, v):
        self._columns[i] = v

    def __delitem__(self, i):
        del self._columns[i]

    def insert(self, i, v):
        self._columns.insert(i, v)

    def __repr__(self):
        rpr = type(self).__name__ + '(' + repr(self._columns) + ')'
        return rpr

    def __str__(self):
        columns = ['  ' + str(column) for column in self._columns]
        string = type(self).__name__ + '([\n' + ',\n'.join(columns) + '])'
        return string

    def sort(self, **kwargs):
        self._columns.sort(**kwargs)

    def resolve_from_header(self, names, formats, add_unknown=True):
        column_map = {}
        for column in self:
            if isinstance(column, Column):
                column_map[column.name] = deepcopy(column)
            elif isinstance(column, ColumnGroup):
                columns = column.resolve_from_names(names)
                column_map.update({column.name: column for column in columns})
        resolved = []
        for name, fmt in zip(names, formats):
            if name in column_map:
                column = column_map[name]
                column.fmt = fmt
                resolved.append(column)
            elif add_unknown:
                column = PeakAttrColumn(name, fmt, name)
                resolved.append(column)
            else:
                resolved.append(None)
        return resolved

    def resolve_from_peaklist(self, peaklist):
        resolved = []
        for column in self:
            if isinstance(column, Column):
                try:
                    values = [column.get_value(pk, None) for pk in peaklist]
                except AttributeError:
                    continue
                if any(value is None for value in values):
                    if not all(value is None for value in values):
                        warn = ('Warning: some values None in column {}, '
                                'excluding it'.format(column.name))
                        print(warn, file=stderr)
                    continue
                else:
                    resolved.append(deepcopy(column))
            elif isinstance(column, ColumnGroup):
                columns = column.resolve_from_peaklist(peaklist)
                resolved.extend(columns)
        resolved = [col.update_from_peaklist(peaklist) for col in resolved]
        return resolved


class PipeTemplate(ColumnTemplate):
    """
    """
    def __init__(self, columns=None):
        if columns is None:
            ppm_names = ['%s_PPM' % d for d in 'XYZA']
            id_names = ['%s_ID' % d for d in 'XYZA']
            hz_names = ['%s_Hz' % d for d in 'XYZA']
            axis_names = ['%s_AXIS' % d for d in 'XYZA']
            one_names = ['%s1' % d for d in 'XYZA']
            three_names = ['%s3' % d for d in 'XYZA']
            columns = (
                PeakAttrColumn('INDEX', '%4d', 'number'),
                PipeNameGroup(),
                PeakAttrColumn('CLUSTID', '%4d', 'cluster_id'),
                PeakAttrColumn('MEMCNT', '%2d', 'cluster_size'),
                SpinAttrGroup(ppm_names, '%7.3f', 'shift'),
                SpinAttrGroup(id_names, '%4d', 'spin_id'),
                SpinAttrGroup(hz_names, '%7.1f', 'shift_hz'),
                SpinAttrGroup(axis_names, '%6.1f', 'shift_pts'),
                SpinAttrGroup(one_names, '%4d', '_1'),
                SpinAttrGroup(three_names, '%4d', '_3'))
        super(PipeTemplate, self).__init__(columns)

    def insert_default(self, columns):
        pipe_name_idx = [i for i, col in enumerate(self)
                         if isinstance(col, PipeNameColumn)]
        pipe_anchor_idx = [i for i, col in enumerate(self)
                           if isinstance(col, PipeAnchorColumn)]
        pipe_group_idx = [i for i, col in enumerate(self)
                          if isinstance(col, PipeNameGroup)]
        peak_number_idx = [i for i, col in enumerate(self)
                           if isinstance(col, PeakAttrColumn)
                           and col.name == 'INDEX']
        name_indices = pipe_name_idx + pipe_anchor_idx + pipe_group_idx
        if name_indices:
            index = max(name_indices) + 1
        elif peak_number_idx:
            index = max(peak_number_idx) + 1
        else:
            index = 0
        self[index:index] = columns


class SparkyTemplate(ColumnTemplate):
    """
    """
    DEFAULT_FMTS = {
        'Assignment': '%10s',
        'w1': '%7.3f',
        'w2': '%7.3f',
        'w3': '%7.3f',
        'w4': '%7.3f'}

    def __init__(self, columns=None):
        if columns is None:
            ppm_names = ['w%d' % i for i in range(1, 5)]
            columns = (
                SparkyNameColumn(),
                SpinAttrGroup(ppm_names, '%7.3f', 'shift'))
        super(SparkyTemplate, self).__init__(columns)

    def get_formats(self, column_names):
        formats = SparkyTemplate.DEFAULT_FMTS
        column_formats = tuple(formats[name] for name in column_names)
        return column_formats


class UplTemplate(ColumnTemplate):
    """
    """
    def __init__(self, columns=None):
        if columns is None:
            columns = (
                SpinAttrColumn('X_res_num', '%4d', 'res_num', 0),
                Res3LetterColumn('X_res_type', 0),
                SpinAttrColumn('X_atom', '%-4s', 'atom', 0),
                SpinAttrColumn('Y_res_num', '%4d', 'res_num', 1),
                Res3LetterColumn('Y_res_type', 1),
                SpinAttrColumn('Y_atom', '%-4s', 'atom', 1),
                PeakAttrColumn('Distance', '%5.2f', 'distance'),
                IgnoreColumn('#peak', '     #peak'),
                PeakAttrColumn('Index', '%5d', 'number'))
        super(UplTemplate, self).__init__(columns)


class XeasyTemplate(ColumnTemplate):
    """
    """
    _ppm_names = ['%s_PPM' % d for d in 'XYZA']
    _id_names = ['%s_ID' % d for d in 'XYZA']

    def __init__(self, columns=None):
        if columns is None:
            columns = (
                PeakAttrColumn('Index', '%4d', 'number'),
                SpinAttrGroup(XeasyTemplate._ppm_names, '%7.3f', 'shift'),
                IgnoreColumn('Ignore0', '0'),
                IgnoreColumn('Ignore1', 'U        '),
                PeakAttrColumn('Volume', '%10.3e', 'volume'),
                IgnoreColumn('Ignore2', ' 0.00e+00'),
                IgnoreColumn('Ignore3', '-'),
                IgnoreColumn('Ignore4', '  0'),
                SpinAttrGroup(XeasyTemplate._id_names, '%4d', 'spin_id'),
                IgnoreColumn('Ignore5', '0'))
        super(XeasyTemplate, self).__init__(columns)

    def get_names_formats(self, num_dims):
        column_names = (
            ['Index'] + XeasyTemplate._ppm_names[:num_dims] +
            ['Ignore0', 'Ignore1', 'Volume', 'Ignore2', 'Ignore3', 'Ignore4'] +
            XeasyTemplate._id_names[:num_dims] + ['Ignore5'])
        column_formats = (
            ['%4d'] + ['%7.3f']*num_dims +
            ['%1s', '%9s', '%10.3e', '%9s', '%1s', '%3s'] +
            ['%4d']*num_dims + ['%1s'])
        column_names = tuple(column_names)
        column_formats = tuple(column_formats)
        return column_names, column_formats

    def resolve_from_peaklist(self, peaklist):
        resolved = super(XeasyTemplate, self).resolve_from_peaklist(peaklist)
        col_names = [column.name for column in resolved]
        ppm_cols = set(XeasyTemplate._ppm_names) & set(col_names)
        if not ppm_cols:
            warn = ('XeasyTemplate: Peak list missing chemical shifts. '
                    'Beware of invalid files')
            print(warn, file=stderr)
        id_cols = set(XeasyTemplate._id_names) & set(col_names)
        if not id_cols:
            warn = ('XeasyTemplate: Peak list missing spin IDs. '
                    'Beware of invalid files')
            print(warn, file=stderr)
        if 'Volume' not in col_names:
            warn = ('XeasyTemplate: Peak list missing volumes. '
                    'Beware of invalid files')
            print(warn, file=stderr)
        return resolved
