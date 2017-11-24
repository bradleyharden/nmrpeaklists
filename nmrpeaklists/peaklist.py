"""
A Python library for handling NMR peak lists.

Read, write, process and convert between NMR peak list formats. Easily
add and remove columns for data processing and fitting with NMRPipe.
Sort and filter peak lists by the peak assignments. Currently supports
peak lists from NMRPipe (.tab files), XEASY (.peaks files), CARA
(modified .peaks files), and CYANA (.upl files).

Classes
-------

:class:`Spin` objects encapsulate all properties of a single NMR spin in
a peak list

:class:`Peak` objects represent a line in a peak list. They act as lists
of Spin objects and contain additional peak-specific attributes.

:class:`PeakList` objects represent a peak list. They act as lists of Peak
objects and contain attributes associated with the entire list.

Documentation
-------------

"""
from __future__ import division, absolute_import, print_function
try:
    from itertools import izip as zip
except ImportError:
    pass
import re
from itertools import combinations
from collections import MutableSequence, namedtuple
from .utils import (RES_NAME_PATTERN, ATOM_NAME_PATTERN, NAME_PATTERN,
                    SPARKY_NAME_PATTERN, SPARKY_ATOM_NAME_PATTERN, argsort)


__all__ = ['Assignment', 'Spin', 'Peak', 'PeakList', 'calibrate_peaklist',
           'get_empty_peaklist', 'get_spin_link_dict', 'renumber_peaklist',
           'reorder_dims', 'sort_by_assignments']


Assignment = namedtuple('Assignment', ('res_type', 'res_num', 'atom'))
"""
"""


class Spin(object):
    """
    Encapsulate all properties of an NMR spin.

    Record the chemical shift and assignment information for an NMR spin.
    Spins are hashable, and the hash is based on a tuple of the spin's
    residue type, residue number, and atom name. Two spins are considered
    equal if they share the same value for all three assignment attributes.
    Spins may also be compared to each other for sorting purposes. A spin is
    considered "less than" another spin, if the former is assigned and the
    latter is an unassigned spin system. Furthermore, assigned spins are
    compared to each other first by residue number, then by backbone or
    sidechain position, and finally by atom number.

    Parameters
    ----------
    res_type : string, optional
        Single letter code for residue type. Use ``'+'`` for unassigned
        spin systems.
    res_num : int or string, optional
        Residue number
    atom : string, optional
        Atom name

    Examples
    --------
    >>> spin = Spin(shift=3.41, spin_id=1012, res_type='D', res_num=54,
                    atom='HB3')
    >>> print(spin)
    Spin(shift=3.41, shfit_pts=None, id=1012, res_type='D', res_num=54,
    atom='HB3')

    See Also
    --------
    Peak, PeakList
    """
    SIDECHAIN_MAP = dict(zip('NABGDEZH', range(8)))

    def __init__(self, res_type=None, res_num=None, atom=None, **kwargs):
        self.res_type = None if res_type is None else str.upper(res_type)
        self.res_num = None if res_num is None else int(res_num)
        self.atom = None if atom is None else str.upper(atom)
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __repr__(self):
        rprs = [k + '=' + repr(v) for k, v in vars(self).items()]
        return 'Spin(' + ', '.join(rprs) + ')'

    def __str__(self):
        strs = [k + '=' + repr(v) for k, v in vars(self).items()
                if v is not None]
        return 'Spin(' + ', '.join(strs) + ')'

    def __nonzero__(self):
        vrs = vars(self).items()
        return True if any(v is not None for k, v in vrs) else False

    def __eq__(self, other):
        return self.assignment == other.assignment

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        # Shorthand
        srt = self.res_type
        srn = self.res_num
        sat = self.atom
        ort = other.res_type
        orn = other.res_num
        oat = other.atom
        # Replace letters with ' ' to sort before unassigned '+'
        srt = None if srt is None else re.sub(r'\w', ' ', self.res_type)
        ort = None if ort is None else re.sub(r'\w', ' ', other.res_type)
        # Map 2nd letter of atom to side chain position 1-7. 'N' to 0 for HN.
        # For single letter backbone atoms, use `get` default to map '' to 0
        ssc = None if sat is None else Spin.SIDECHAIN_MAP.get(sat[1:2], 0)
        osc = None if oat is None else Spin.SIDECHAIN_MAP.get(oat[1:2], 0)
        # Always sort None last. True sorts after False
        slf = ((srt is None, srt), (srn is None, srn),
               (ssc is None, ssc), (sat is None, sat))
        oth = ((ort is None, ort), (orn is None, orn),
               (osc is None, osc), (oat is None, oat))
        return slf < oth

    def __le__(self, other):
        return not other < self

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return not self < other

    @property
    def assignment(self):
        return Assignment(self.res_type, self.res_num, self.atom)

    @property
    def res_name(self):
        rest = self.res_type if self.res_type is not None else '?'
        resn = '{:d}'.format(self.res_num) if self.res_num is not None else '?'
        return rest + resn

    @res_name.setter
    def res_name(self, name):
        if name is None:
            self.res_type = None
            self.res_num = None
        else:
            match = re.match(RES_NAME_PATTERN, name.strip())
            if match is None:
                raise ValueError('invalid res_name: {!r}'.format(name))
            res_type = match.group(1)
            res_num = match.group(2)
            self.res_type = res_type if res_type != '?' else None
            self.res_num = int(res_num) if res_num != '?' else None

    @property
    def atom_name(self):
        return self.atom if self.atom is not None else '?'

    @atom_name.setter
    def atom_name(self, name):
        if name is None:
            self.atom = None
        else:
            match = re.match(ATOM_NAME_PATTERN, name.strip())
            if match is None:
                raise ValueError('invalid atom_name: {!r}'.format(name))
            self.atom = name if name != '?' else None

    @property
    def name(self):
        return '{}-{}'.format(self.res_name, self.atom_name)

    @name.setter
    def name(self, name):
        if name is None:
            self.res_name = None
            self.atom_name = None
        else:
            match = re.match(NAME_PATTERN, name.strip())
            if match is None:
                raise ValueError('invalid name: {!r}'.format(name))
            self.res_name = match.group(1)
            self.atom_name = match.group(2)


class Peak(MutableSequence):
    """
    A list of Spin objects and an associated set of parameters.

    Peak objects encapsulate each line of an NMR peak list. Peak specific
    parameters should be added as attributes. Arbitrary attributes may be
    added to a Peak with the standard attribute syntax or as keyword
    arguments upon initialization.

    Peaks are hashable, and the hash is based on a frozen set of the peak's
    constituent spins. Two peaks are considered equal if their sets of
    spins are equal. Note that this only depends on the assignments of the
    spins, not on the spin's attributes nor the peak's attributes.

    .. warning:: Peak objects are hashable but still mutable.

    Parameters
    ----------
    spins : :obj:`list` of :obj:`Spin`, optional
        Spins comprising the peak
    index : int or string, optional
        Peak index
    commented : bool, default False
        Whether the peak should be commented in the peak list

    Examples
    --------
    >>> spin0 = Spin(shift=3.41, spin_id=1012, res_type='D', res_num=54,
                    atom='HB3')
    >>> spin1 = Spin(shift=40.24, spin_id=1013, res_type='D', res_num=54,
                    atom='CB')
    >>> spin2 = Spin(shift=4.632, spin_id=973, res_type='L', res_num=56,
                    atom='HA')
    >>> peak = Peak(spins=[spin0, spin1, spin2], index=134, volume=5.432e5)
    >>> print(peak)
    Peak(volume=543200.0, index=134, commented=False, spins=
    [Spin(shift=3.41, shfit_pts=None, id=1012, res_type='D', res_num=54,
    atom='HB3'),
    Spin(shift=40.24, shfit_pts=None, id=1013, res_type='D', res_num=54,
    atom='CB'),
    Spin(shift=4.63, shfit_pts=None, id=973, res_type='L', res_num=56,
    atom='HA')])
    >>> peak.height = 1.852e3
    >>> print(peak)
    Peak(volume=543200.0, index=134, commented=False, height=1852.0, spins=
    [Spin(shift=3.41, shfit_pts=None, id=1012, res_type='D', res_num=54,
    atom='HB3'),
    Spin(shift=40.24, shfit_pts=None, id=1013, res_type='D', res_num=54,
    atom='CB'),
    Spin(shift=4.63, shfit_pts=None, id=973, res_type='L', res_num=56,
    atom='HA')])

    See Also
    --------
    Spin, PeakList
    """
    def __init__(self, spins=None, **kwargs):
        self._spins = []
        self.extend(spins if spins is not None else [])
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __len__(self):
        return len(self._spins)

    def __getitem__(self, i):
        return self._spins[i]

    def __delitem__(self, i):
        del self._spins[i]

    def __setitem__(self, i, v):
        self._spins[i] = v

    def insert(self, i, v):
        self._spins.insert(i, v)

    def __repr__(self):
        attr = [k + '=' + repr(v) + ', ' for k, v in vars(self).items()
                if k != '_spins']
        attr = ''.join(attr)
        return 'Peak(' + attr + 'spins=' + repr(self._spins) + ')'

    def __str__(self):
        attr = [k + '=' + repr(v) + ', ' for k, v in vars(self).items()
                if k != '_spins' and v is not None]
        attr = ''.join(attr)
        spins = ',\n'.join('  ' + str(spin) for spin in self)
        return 'Peak(' + attr + 'spins=[\n' + spins + '])'

    def __nonzero__(self):
        empty = True
        for key, value in vars(self).items():
            if key == '_spins':
                continue
            if value is not None:
                empty = False
                break
        return True if len(self) > 0 or not empty else False

    def __eq__(self, other):
        return (set(spin.assignment for spin in self) ==
                set(spin.assignment for spin in other))

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        return tuple(spin for spin in self) < tuple(spin for spin in other)

    def __le__(self, other):
        return not other < self

    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        return not self < other

    def sort(self, **kwargs):
        self._spins.sort(**kwargs)

    @property
    def sparky_name(self):
        prev_res_name = None
        names = []
        for spin in self:
            name = ''
            if spin.res_name != prev_res_name:
                name += spin.res_name
            name += spin.atom_name.replace('-', 'm').replace('+', 'p')
            names.append(name)
            prev_res_name = spin.res_name
        sparky_name = '-'.join(names)
        return sparky_name

    @sparky_name.setter
    def sparky_name(self, value):
        prev_res_name = None
        names = value.strip().split('-')
        for name, spin in zip(names, self):
            match = re.match(SPARKY_NAME_PATTERN, name)
            if match is None:
                if prev_res_name is None:
                    raise ValueError('invalid sparky name: {!r}'.format(value))
                match = re.match(SPARKY_ATOM_NAME_PATTERN, name)
                if match is None:
                    raise ValueError('invalid sparky name: {!r}'.format(value))
                else:
                    spin.res_name = prev_res_name
                    atom_name = name.replace('m', '-').replace('p', '+')
                    spin.atom_name = atom_name
            else:
                spin.res_name = match.group(1)
                atom_name = match.group(2).replace('m', '-').replace('p', '+')
                spin.atom_name = atom_name
                prev_res_name = spin.res_name

    def name(self, columns=None):
        if columns is None:
            name = ' '.join(spin.name for spin in self)
        else:
            name = ' '.join(column.get_string(self) for column in columns)
        return name


class PeakList(MutableSequence):
    """
    A list of Peak objects and parameters associated with entire peak lists.

    PeakLists are hashable, and the hash is based on a frozen set of the
    constituent peaks. Two peak lists are considered equal if their sets of
    peaks are equal. Note that this only depends on the assignments of the
    spins in each peak, not on any other spin, peak or peak list attributes.

    .. warning:: PeakList objects are hashable but still mutable.

    Parameters
    ----------
    peaks : list of Peak objects, optional
        Each peak must have the same number of spins. The dimensionality
        of the peak list is given with self.dims

    Raises
    ------
    ValueError
        If attempting to insert a peak with a different number of spins than
        those currently populating the peak list.

    Examples
    --------
    >>> peaklist = PeakList(anchors=[(0,1)],
                            tab_fmt=[('height', 'HEIGHT', '%11.4e'),
                                     ('width', '%sW', '%5.2f'),
                                     ('CEST_profile', 'Z_A%d', '%6.4f')])
    >>> peak = peaklist[0]
    >>> peak.height
    53472000.0
    >>> peak.CEST_profile
    [0.3017, 0.3022, 0.3021, ...]
    >>> spin = peak[0]
    >>> spin.width
    2.07

    See Also
    --------
    Spin, Peak
    """
    def __init__(self, peaks=None):
        self._peaks = []
        self.extend(peaks if peaks is not None else [])

    def __len__(self):
        return len(self._peaks)

    def __getitem__(self, i):
        return self._peaks[i]

    def __setitem__(self, i, v):
        self._peaks[i] = v

    def __delitem__(self, i):
        del self._peaks[i]

    def insert(self, i, v):
        self._peaks.insert(i, v)

    def __repr__(self):
        return 'PeakList(' + repr(self._peaks) + ')'

    def __str__(self):
        peaks = []
        for peak in self:
            lines = str(peak).split('\n')
            lines = ['  ' + line for line in lines]
            peaks.append('\n'.join(lines))
        peaks = ',\n'.join(peaks)
        return 'PeakList([\n' + peaks + '])'

    def __nonzero__(self):
        empty = True
        for key, value in vars(self).items():
            if key == '_peaks':
                continue
            if value is not None:
                empty = False
                break
        return True if len(self) > 0 or not empty else False

    def __eq__(self, other):
        return (set(frozenset(spn.assignment for spn in pk) for pk in self) ==
                set(frozenset(spn.assignment for spn in pk) for pk in other))

    def __ne__(self, other):
        return not self == other

    def sort(self, **kwargs):
        self._peaks.sort(**kwargs)

    @property
    def dims(self):
        set_of_peak_lengths = set(len(peak) for peak in self)
        num_lens = len(set_of_peak_lengths)
        if num_lens == 1:
            return len(self[0])
        elif num_lens == 0:
            raise AttributeError('peaklist is empty')
        else:
            raise AttributeError('peaks in peaklist have different lengths')

    @property
    def anchors(self):
        """Detect which spins in each peak make up spin anchors."""
        dims = self.dims
        anchors = []
        for peak in self:
            possible_anchors = []
            for combination in combinations(range(dims), 2):
                spins = [peak[i] for i in combination]
                if any(s.res_num is None or s.atom is None for s in spins):
                    continue
                res_nums = [spin.res_num for spin in spins]
                atoms = [spin.atom for spin in spins]
                elements = [atom[0] for atom in atoms]
                positions = [atom[1:] for atom in atoms]
                same_res_num = res_nums[0] == res_nums[1]
                valid_pairs = [set(('H', 'N')), set(('H', 'C'))]
                is_proton_heavy_pair = set(elements) in valid_pairs
                same_position = all(c[0] == c[1] for c in zip(*positions))
                if same_res_num and is_proton_heavy_pair and same_position:
                    if '' in positions and set(elements) != set(('H', 'N')):
                        # One of the atom names must have been 'H', 'N' or 'C'
                        # Of these, only the amide proton anchor is valid
                        continue
                    if elements[0] == 'H':
                        possible_anchors.append(combination)
                    else:
                        possible_anchors.append(combination[::-1])
            if len(possible_anchors) > 1:
                pa_sets = [set(pa) for pa in possible_anchors]
                overlap = set.intersection(*pa_sets)
                if overlap:
                    # Ambiguous, overlapping anchors
                    continue
            for poss_anc in possible_anchors:
                if poss_anc not in anchors:
                    anchors.append(poss_anc)
        anchors = tuple(anchors)
        return anchors


def calibrate_peaklist(peaklist, calibration, attr='shift'):
    """
    Calibrate the chemical shifts of each spin in the peak list.

    #TODO:

    For each spin in the peak list, subtract the corresponding calibration
    value from its spin.shift attribute.

    Parameters
    ----------
    calibration : list of floats
        List of calibrations for each dimension of the peak list, in PPM.
        The order of the calibration values should match the order of the
        spins in each peak.

    Raises
    ------
    ValueError
        When the calibration list length doesn't match the number of pins
        in the peak.

    Examples
    --------
    >>> peaklist = PeakList(peaks=peaks, dims=3)
    >>> peaklist.calibrate([0.053, 0.102, -0.018])
    """
    if len(calibration) != peaklist.dims:
        raise ValueError('incorrect calibration list length')
    for peak in peaklist:
        for spin, cal in zip(peak, calibration):
            shift = getattr(spin, attr)
            shift -= cal
            setattr(spin, attr, shift)
    return peaklist


def get_empty_peaklist(num_peaks, num_dims):
    peaklist = PeakList()
    peaklist[:] = [Peak() for _ in range(num_peaks)]
    for peak in peaklist:
        peak[:] = [Spin() for _ in range(num_dims)]
    return peaklist


def get_spin_link_dict(peaklist):
    """
    Map each unique spin link to all of its corresponding peaks.

    NOESY peak lists represent spin links between Hydrogen atoms. Whether
    2D, 3D or 4D, each peak in a NOESY peak list has exactly two Hydrogen
    spins. Here, a spin link is represented by a frozenset containing the
    spin.assignment tuples for each Hydrogen atom. This function returns a
    dictionary mapping each unique spin link to a list of the Peaks in the
    PeakList that contain those two Hydrogen atoms.

    Examples
    --------
    >>> spin_link_dict = peaklist.spin_link_dict()
    >>> spin_link, peaks = spin_link_dict.popitem()
    >>> spin_link
    frozenset([Assignment(res_type='Q', res_num=21, atom='HN'), Assignment(
    res_type='G', res_num=17, atom='HN')])
    >>> print(peaks[0])
        Peak(spins=[
        Spin(res_type=G, res_num=17, atom=HN),
        Spin(res_type=G, res_num=17, atom=N),
        Spin(res_type=Q, res_num=21, atom=HN)])
    >>> print(peaks[1])
        Peak(spins=[
        Spin(res_type=Q, res_num=21, atom=HN),
        Spin(res_type=Q, res_num=21, atom=N),
        Spin(res_type=G, res_num=17, atom=HN)])

    Returns
    -------
    out : dictionary
        Each key is a frozenset made from two Hydrogen spin.assignment
        tuples. Each value is a list of peaks containing those two Hydrogen
        spins.
    """
    spin_link_dict = {}
    for peak in peaklist:
        spins = [spin for spin in peak
                 if spin.atom is not None and spin.atom[0] == 'H']
        if len(spins) != 2:
            err = ('expected 2 Hydrogens in each peak, '
                   'found %d' % len(spins))
            raise ValueError(err)
        link = frozenset(spin.assignment for spin in spins)
        spin_link_dict.setdefault(link, []).append(peak)
    return spin_link_dict


def renumber_peaklist(peaklist):
    for i, peak in enumerate(peaklist, 1):
        peak.number = i
    return peaklist


def reorder_dims(peaklist, old_indices=None, new_indices=None):
    """
    TODO:
    """
    if old_indices is None:
        if new_indices is None:
            raise ValueError('must provide indices')
        else:
            old_indices = argsort(new_indices)
    for peak in peaklist:
        peak[:] = [peak[i] for i in old_indices]
    return peaklist


def sort_by_assignments(peaklist, order=None, commented_at_end=False):
    """
    Sort peaks by the assignments of their constituent spins.

    Sort the peaks by the assignments of spins in particular dimensions.
    The default order sorts the peaks by the dimensions associated with
    spin anchors first then by the remaining dimensions in the order they
    appear in each peak. Optionally place all commented peaks at the end of
    the peak list.

    Parameters
    ----------
    order : list containing ints or tuples of ints
        A list of spin indices and anchor tuples indicating the order in
        which the dimensions should be sorted. The default order sorts
        anchored spins before unanchored spins, then sorts the remaining
        spins by their order in the peaks.
    commented_at_end : boolean, default False
        Indicate whether commented peaks should be sorted in their normal
        order or at the end of the peak list

    Examples
    --------
    >>> peaklist.dims
    3
    >>> peaklist[0][0]
    Spin(res_type='I', res_num=34, atom='H')
    >>> peaklist[0][2]
    Spin(res_type='I', res_num=34, atom='N')
    >>> peaklist.sort_by_assignments([(0, 2), 1], commented_at_end=True)
    >>> peaklist[0][0]
    Spin(res_type='E', res_num=1, atom='H')
    >>> peaklist[0][2]
    Spin(res_type='E', res_num=1, atom='N')
    """
    anchors = peaklist.anchors
    anchored = tuple(i for anchor in anchors for i in anchor)
    unanchored = set(range(peaklist.dims)) - set(anchored)
    default_order = anchored + tuple(sorted(unanchored))
    order = order if order is not None else default_order
    peaklist.sort(key=lambda peak: tuple(peak[i] for i in order))
    if commented_at_end:
        peaklist.sort(key=lambda peak: peak.commented)
    return peaklist
