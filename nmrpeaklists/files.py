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
from struct import unpack
from math import ceil, floor
from collections import Mapping
from .peaklist import Assignment, get_empty_peaklist
from .columns import PipeTemplate, XeasyTemplate, UplTemplate, SparkyTemplate
from .utils import FORMAT_STRING_PATTERN


__all__ = ['PipeFile', 'XeasyFile', 'UplFile', 'SparkyFile', 'CaraSpinsFile',
           'CaraAnchorFile', 'PipeSpectrumHeader']


class PeakListFile(object):
    def __init__(self, template):
        self.template = template

    def __repr__(self):
        name = type(self).__name__
        init_args, _, _, _ = getargspec(self.__init__)
        vrs = vars(self)
        attr = [arg + '=' + repr(vrs[arg]) for arg in init_args[1:]]
        rpr = name + '(' + ', '.join(attr) + ')'
        return rpr

    def __str__(self):
        name = type(self).__name__
        init_args, _, _, _ = getargspec(self.__init__)
        vrs = vars(self)
        attr = [arg + '=' + repr(vrs[arg]) + ', ' for arg in init_args[1:]
                if arg != 'template']
        template = str(vrs['template'])
        rpr = name + '(' + ''.join(attr) + 'template=' + template + ')'
        return rpr

    def read_data(self, lines):
        commented = []
        row_data = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            com = True if line.startswith('#') else False
            commented.append(com)
            row = line.lstrip(' #').split()
            row_data.append(row)
        num_peaks = len(commented)
        commented = tuple(commented)
        column_data = tuple(column for column in zip_longest(*row_data))
        return num_peaks, commented, column_data

    def read_header(self, lines):
        raise NotImplementedError

    def read_peaklist(self, filename, add_unknown=True):
        with open(filename, 'r') as plf:
            lines = plf.readlines()
        peaklist = self.read_peaklist_lines(lines, add_unknown)
        return peaklist

    def read_peaklist_lines(self, lines, add_unknown=True):
        num_dims, names, formats = self.read_header(lines)
        num_peaks, commented, column_data = self.read_data(lines)
        template = self.template
        resolved = template.resolve_from_header(names, formats, add_unknown)
        self.template[:] = [col for col in resolved if col is not None]
        peaklist = get_empty_peaklist(num_peaks, num_dims)
        for com, peak in zip(commented, peaklist):
            peak.commented = com
        for data, column in zip(column_data, resolved):
            if column is None:
                continue
            for peak, string in zip(peaklist, data):
                if string is None:
                    continue
                column.set_string(peak, string)
        return peaklist

    def write_data(self, lines, num_peaks, commented, column_data):
        comments = ['#' if c else ' ' for c in commented]
        data_rows = [' '.join(row) + '\n' for row in zip(*column_data)]
        rows = [com + row for com, row in zip(comments, data_rows)]
        lines += rows
        return lines

    def write_header(self, lines, num_dims, column_names, column_formats):
        raise NotImplementedError

    def write_peaklist(self, peaklist, filename):
        lines = self.write_peaklist_lines(peaklist)
        with open(filename, 'w') as plf:
            plf.writelines(lines)

    def write_peaklist_lines(self, peaklist):
        num_dims = peaklist.dims
        num_peaks = len(peaklist)
        self.template[:] = self.template.resolve_from_peaklist(peaklist)
        column_names = [column.name for column in self.template]
        column_formats = [column.fmt for column in self.template]
        try:
            commented = [peak.commented for peak in peaklist]
        except AttributeError:
            commented = [False] * len(peaklist)
        column_data = []
        for column in self.template:
            data = [column.get_string(peak) for peak in peaklist]
            column_data.append(data)
        lines = self.write_header([], num_dims, column_names, column_formats)
        lines = self.write_data(lines, num_peaks, commented, column_data)
        lines[-1].rstrip('\n')
        return lines


class PipeFile(PeakListFile):
    """
    """
    def __init__(self, template=None):
        template = template if template is not None else PipeTemplate()
        super(PipeFile, self).__init__(template)

    def read_data(self, lines):
        ignore = set(['REMARK', 'DATA', 'NULL', '***', 'VARS', 'FORMAT'])
        row_data = []
        commented = []
        for line in lines:
            line = line.strip()
            if not line or any(line.startswith(s) for s in ignore):
                continue
            commented.append(True if line.startswith('#') else False)
            row = line.lstrip(' #').split()
            row_data.append(row)
        num_peaks = len(commented)
        commented = tuple(commented)
        column_data = tuple(column for column in zip_longest(*row_data))
        return num_peaks, commented, column_data

    def read_header(self, lines):
        column_names = column_formats = None
        for line in lines:
            line = line.strip()
            if line.startswith('VARS'):
                column_names = tuple(line.strip().split()[1:])
            elif line.startswith('FORMAT'):
                column_formats = tuple(line.strip().split()[1:])
            if column_names is not None and column_formats is not None:
                break
        else:
            raise ValueError("NMRPipe file missing VARS and/or FORMAT line")
        matches = [re.match('([XYZA]{1,2})_', name) for name in column_names]
        chars = ''.join(match.group(1) for match in matches if match)
        num_dims = len(set(chars))
        return num_dims, column_names, column_formats

    def write_header(self, lines, num_dims, column_names, column_formats):
        variables = 'VARS ' + ' '.join(n for n in column_names) + '\n'
        formats = 'FORMAT ' + ' '.join(f for f in column_formats) + '\n'
        lines += [variables, formats, '\n']
        return lines


class SparkyFile(PeakListFile):
    """
    """
    def __init__(self, template=None):
        template = template if template is not None else SparkyTemplate()
        super(SparkyFile, self).__init__(template)

    def read_header(self, lines):
        if lines[0].endswith('peaks\n'):
            column_names = lines[1]
        else:
            column_names = lines[0]
        column_names = tuple(column_names.strip().split())
        matches = [re.match('^w(\d)$', name) for name in column_names]
        dims = [int(match.group(1)) for match in matches if match]
        num_dims = max(dims)
        column_formats = tuple(self.template.get_formats(column_names))
        return num_dims, column_names, column_formats

    def read_data(self, lines):
        if lines[0].endswith('peaks\n'):
            lines = lines[2:]
        else:
            lines = lines[1:]
        spr = super(SparkyFile, self)
        num_peaks, commented, column_data = spr.read_data(lines)
        return num_peaks, commented, column_data

    def write_header(self, lines, num_dims, column_names, column_formats):
        pattern = FORMAT_STRING_PATTERN
        header = []
        for name, fmt in zip(column_names, column_formats):
            match = re.match(pattern, fmt)
            if not match:
                err = 'invalid format string {!r}'.format(fmt)
                raise ValueError(err)
            else:
                width = int(match.group(1))
                name_format = '%{:d}s'.format(width)
                header.append(name_format % name)
        lines += [' ' + ' '.join(header) + '\n']
        return lines


class UplFile(PeakListFile):
    """
    """
    def __init__(self):
        super(UplFile, self).__init__(UplTemplate())

    def read_header(self, lines):
        num_dims = 2
        column_names = [column.name for column in self.template]
        column_formats = [column.fmt for column in self.template]
        return num_dims, column_names, column_formats

    def write_header(self, lines, num_dims, column_names, column_formats):
        return lines


class XeasyFile(PeakListFile):
    """
    """
    INAME_DICT = {'H': 'H1', 'N': 'N15', 'C': 'C13'}

    def __init__(self, inames=None, cyana_format=None):
        super(XeasyFile, self).__init__(XeasyTemplate())
        self.inames = inames
        self.cyana_format = cyana_format

    @staticmethod
    def inames_cyfmt_from_lines(lines):
        inames = []
        cyana_format = None
        for line in lines:
            clean = line.strip().lstrip('# ')
            if clean.startswith('INAME'):
                inames.append(line)
            if clean.startswith('CYANAFORMAT'):
                cyana_format = line
        inames = inames if inames else None
        return inames, cyana_format

    @staticmethod
    def inames_cyfmt_from_peaklist(peaklist):
        inames = None
        cyana_format = None
        atom_types = []
        for spins in zip(*peaklist):
            atom_type = set(s.atom[0] for s in spins if s.atom is not None)
            atom_type = atom_type.pop() if len(atom_type) == 1 else None
            atom_types.append(atom_type)
        if all(at is not None for at in atom_types):
            inames = []
            for i, atom_type in enumerate(atom_types, 1):
                nuc = XeasyFile.INAME_DICT[atom_type]
                inames.append('#INAME {:d} {}\n'.format(i, nuc))
        anchors = peaklist.anchors
        if anchors:
            cy_fmt = ''.join(at.upper() if i in anchors[0] else at.lower()
                             for i, at in enumerate(atom_types))
            cyana_format = '#CYANAFORMAT {}\n'.format(cy_fmt)
        return inames, cyana_format

    def read_data(self, lines):
        commented = []
        row_data = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            com = True if line.startswith('#') else False
            row = line.lstrip(' #').split()
            # Data rows start with integer index and have at least 10 fields
            if len(row) > 9:
                try:
                    int(row[0])
                except ValueError:
                    continue
                else:
                    commented.append(com)
                    row_data.append(row)
        num_peaks = len(commented)
        commented = tuple(commented)
        column_data = tuple(column for column in zip_longest(*row_data))
        return num_peaks, commented, column_data

    def read_header(self, lines):
        self.inames, self.cyana_format = self.inames_cyfmt_from_lines(lines)
        first_line = lines[0].strip().lstrip('# ')
        if first_line.startswith('Number of dimenstions'):
            num_dims = int(first_line.split()[-1])
        elif self.inames:
            num_dims = len(self.inames)
        else:
            raise ValueError("Can't detect number of dimensions in XEASY file")
        template = self.template
        column_names, column_formats = template.get_names_formats(num_dims)
        return num_dims, column_names, column_formats

    def write_header(self, lines, num_dims, column_names, column_formats):
        header = []
        header.append('# Number of dimensions {:d}\n'.format(num_dims))
        if self.cyana_format is not None:
            header.append(self.cyana_format)
        if self.inames is not None:
            header.extend(self.inames)
        header.append('\n')
        lines += header
        return lines

    def write_peaklist_lines(self, peaklist):
        inames, cy_fmt = self.inames_cyfmt_from_peaklist(peaklist)
        self.inames = inames if inames is not None else self.inames
        self.cyana_format = cy_fmt if cy_fmt is not None else self.cyana_format
        lines = super(XeasyFile, self).write_peaklist_lines(peaklist)
        return lines


class AssignmentFile(Mapping):
    """
    """
    def __init__(self, mapping=None):
        self._map = mapping if mapping is not None else {}

    def __getitem__(self, key):
        try:
            return self._map[key]
        except KeyError:
            raise KeyError('{!r}'.format(key))

    def __iter__(self):
        return iter(self._map)

    def __len__(self):
        return len(self._map)

    def __repr__(self):
        rpr = type(self).__name__ + '(' + repr(self._map) + ')'
        return rpr

    def __str__(self):
        _map = ['  ' + repr(k) + ': ' + repr(v) for k, v in self._map.items()]
        string = type(self).__name__ + '({\n' + ',\n'.join(_map) + '})'
        return string

    def read_file(self):
        raise NotImplementedError

    def assign_peaklist(self, peaklist, warn=True):
        for peak in peaklist:
            for spin in peak:
                spin_id = getattr(spin, 'spin_id')
                try:
                    spin.res_type, spin.res_num, spin.atom = self[spin_id]
                except KeyError:
                    if warn:
                        err = ('Warning: No assignment found for spin ID '
                               '{!r}'.format(spin_id))
                        print(err, file=stderr)
        return peaklist


class CaraSpinsFile(AssignmentFile):
    """
    """
    def __init__(self, mapping=None):
        super(CaraSpinsFile, self).__init__(mapping)  

    def read_file(self, filename):
        dct = {}
        with open(filename, 'r') as inp:
            for line in inp:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                line = line.split()
                spin_id, res_type, res_num, atom = line
                dct[int(spin_id)] = Assignment(res_type, int(res_num), atom)
        self._map = dct
        return self


class CaraAnchorFile(AssignmentFile):
    """
    """
    def __init__(self, mapping=None):
        super(CaraAnchorFile, self).__init__(mapping)

    @staticmethod
    def _get_first_data_row(lines):
        first_data_row = None
        for index, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            row = line.lstrip(' #').split()
            # Data rows start with integer index and have at least 10 fields
            if len(row) > 9:
                try:
                    int(row[0])
                except ValueError:
                    continue
                else:
                    first_data_row = index
                    break
        return first_data_row

    def read_file(self, filename):
        with open(filename, 'r') as inp:
            lines = inp.readlines()
        first_data_row = self._get_first_data_row(lines)
        itr = iter(lines)
        [next(itr) for _ in range(first_data_row)]  # Skip header
        assignments = {}
        for data_line, assignment_line in zip(itr, itr):
            data_line = data_line.strip().split()
            assignment_line = assignment_line.lstrip('# ').rstrip().split()
            spin_id1 = int(data_line[9])
            spin_id2 = int(data_line[10])
            anchor, res_name = assignment_line
            if res_name[0].isalpha():
                res_type = res_name[0]
                res_num = int(res_name[1:])
            else:
                res_type = '+'
                res_num = int(res_name)
            atom1, atom2 = anchor.split('/')
            assignments[spin_id1] = Assignment(res_type, res_num, atom1)
            assignments[spin_id2] = Assignment(res_type, res_num, atom2)
        self._map = assignments
        return self


class SpectrumHeader(Mapping):
    """
    TODO:
    Standard header format.
    'XYZA' for dims, 'SIZE', 'SW', 'OBS', 'ORIG' for parameters
    """
    def __init__(self, header=None):
        self._header = header if header is not None else {}

    def __getitem__(self, key):
        try:
            return self._header[key]
        except KeyError:
            raise KeyError('{!r}'.format(key))

    def __iter__(self):
        return iter(self._header)

    def __len__(self):
        return len(self._header)

    def read_file(self):
        raise NotImplementedError

    def __repr__(self):
        rpr = type(self).__name__ + '(' + repr(self._header) + ')'
        return rpr

    def __str__(self):
        header = self._header
        hdr = ['  ' + repr(k) + ': ' + repr(v) for k, v in header.items()]
        string = type(self).__name__ + '({\n' + ',\n'.join(hdr) + '})'
        return string


class PipeSpectrumHeader(SpectrumHeader):
    """
    """
    def __init__(self, header=None):
        super(PipeSpectrumHeader, self).__init__(header)

    def read_file(self, filename):
        """
        """
        size_locations = {'X': 99, 'Y': 219, 'Z': 15, 'A': 32}
        parm_locations = {2: {'OBS': 119, 'SW': 100, 'ORIG': 101},
                          1: {'OBS': 218, 'SW': 229, 'ORIG': 249},
                          3: {'OBS':  10, 'SW':  11, 'ORIG':  12},
                          4: {'OBS':  28, 'SW':  29, 'ORIG':  30}}
        parameters = list(parm_locations[1].keys())
        header = {}
        with open(filename, 'rb') as ftf:
            raw = unpack('512f', ftf.read(2048))
        for dim_char, dim_int in zip('XYZA', raw[24:28]):  # FDDIMORD in 24:28
            header[dim_char] = {}
            loc = size_locations[dim_char]
            header[dim_char]['SIZE'] = raw[loc]
            for par in parameters:
                loc = parm_locations[dim_int][par]
                header[dim_char][par] = raw[loc]
        self._header = header
        return self

    def calc_shift_pts(self, peaklist):
        """
        TODO:
        Calculate and set the chemical shift of each spin in points

        Parameters
        ----------

        Examples
        --------
        >>> 
        """
        for peak in peaklist:
            for spin, dim in zip(peak, 'XYZA'):
                shift = getattr(spin, 'shift')
                obs = self[dim]['OBS']
                orig = self[dim]['ORIG']
                size = self[dim]['SIZE']
                sw = self[dim]['SW']
                hz = obs * shift
                hz = hz - sw * ((hz - orig) // sw)  # Correct for aliasing
                pts = size - (hz - orig) / (sw / size)
                setattr(spin, 'shift_pts', pts)
                setattr(spin, '_1', floor(pts))
                setattr(spin, '_3', ceil(pts))
        return peaklist
