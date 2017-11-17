========
Tutorial
========

Read, write, edit and convert between various NMR peak list formats.

.. contents:: :local:

Reading a peak list
===================

Peak lists can be read in two different ways. The ``nmrpeaklists`` library provides top level functions for reading a peak list file and returning a new :class:`.PeakList` object. Alternatively, user may opt to initialize a blank :class:`.PeakList` object and read multiple peak lists into it using the vairous read methods.

XEASY format
------------

Standard format
~~~~~~~~~~~~~~~

The standard XEASY peak list format specifies a volume for each peak and a chemical shift and spin ID for each spin comprising the peak. Unfortunately, no direct assignment data is provided in the XEASY format. Assignment information is only available by referencing each spin ID to an atom list and sequence file. It is highly recommended that users provide both of these files when reading XEASY peak lists. Read an XEASY peak list with either method as follows:

.. code-block:: python

    peaklist = pl.read_peaks_file('protein.peaks', atom_list='protein.prot',
                                  seq_file='protein.seq')

.. code-block:: python

    peaklist = pl.PeakList(atom_list='protein.prot', seq_file='protein.seq')
    for filename in filenames:
        peaklist.read_peaks_file(filename)


.. note::
    The XEASY format creates a fundamental problem when dealing with a mixture of assigned and unassigned spins. An atom list can connect a spin ID to either its residue number or its spin system number, but not both simultaneously. As a result, atom lists that connect spin IDs to residue numbers must exclude unassigned spin systems. The ``peaklists`` library provides no way around this limitation at the current time.

CARA format
~~~~~~~~~~~

Although the standard XEASY format provides no way to directly access peak assignments, XEASY peak lists exported by CARA come with comments below each line indicating *some* of the spin assignment data. CARA 2D anchor peak lists fully identify both spins and do not require an atom list or sequence file. However, CARA 3D and 4D strip peak lists identify only some of the spins in each peak and must be treated as standard XEASY peak lists. Use the following functions to read CARA anchor peak lists.

.. code-block:: python

    peaklist = pl.read_cara_peaks_file('protein.peaks')

.. code-block:: python

    peaklist = pl.PeakList()
    for filename in filenames:
        peaklist.read_cara_peaks_file(filename)

NMRPipe format
--------------

The NMRPipe peak list format is the most versatile format supported by the ``peaklists`` library. NMRPipe peak lists may contain any combination of spin IDs, assignment data and arbitrary parameters for each peak and spin in the peak list.

Additionally, when an NMRPipe peak list is used in conjunction with nlinLS for fitting a spectrum, the chemical shift of each spin must be specified in points rather than in PPM. Because this value is specific to each spectrum, users must supply the spectrum or a plane from the spectrum when reading an NMRPipe peak list.

.. code-block:: python

    peaklist = pl.read_tab_file('protein.tab', spectrum='../ft3/test001.ft3')

.. code-block:: python

    peaklist = pl.PeakList(spectrum='../ft3/test001.ft3')
    for filename in filenames:
        peaklist.read_tab_file(filename)

UPL format
----------

UPL files are a very limited file format. They contain assignment data, but do not reference chemical shift or spin IDs. Support is provided to enable sorting and filtering of UPL files when performing structure calculations.

.. code-block:: python

    peaklist = pl.read_upl_file('protein.upl')

.. code-block:: python

    peaklist = pl.PeakList()
    for filename in filenames:
        peaklist.read_upl_file(filename)

Data structures
===============

The ``nmrpeaklists`` library provides three data structures that aim to mimic the structure of a peak list. A :class:`~.peaklist.PeakList` object represents an entire peak list and is composed of a sequence of :class:`~.peaklist.Peak` objects. Each Peak object represents a single line in a peak list and is composed of a sequence of :class:`~.peaklist.Spin` objects.

Spin
----

A Spin is a container object that holds attributes of a particular NMR spin resonance. A peak in an N-dimensional spectrum will be associated with N different spins. Typically, Spin objects will contain attributes of the spin like the chemical shift, assignments, line width, etc. The following three attributes are pre-defined for each Spin object:

+-----------+----------------------------------------------+
| Attribute | Meaning                                      |
+===========+==============================================+
| res_type  | Residue type                                 |
+-----------+----------------------------------------------+
| res_num   | Residue number or spin system number         |
+-----------+----------------------------------------------+
| atom      | Atom name                                    |
+-----------+----------------------------------------------+

Other attributes may be added to Spins as necessary. The following table provides a list of suggested attribute names for common spin parameters:

+-----------+--------------------------------------------------------+
| Attribute | Meaning                                                |
+===========+========================================================+
| shift     | Chemical shift                                         |
+-----------+--------------------------------------------------------+
| shift_pts | Chemical shift in number of points (spectrum specific) |
+-----------+--------------------------------------------------------+
| width     | Line width of the peak in the corresponding dimension  |
+-----------+--------------------------------------------------------+

Spin attributes can be set upon initializing a Spin object or added to a Spin object after creation

.. code-block:: python

    >>> spin = npl.Spin(atom='N')
    >>> print(spin)
    Spin(atom='N')
    >>> spin.res_num = 15
    >>> print(spin)
    Spin(res_num=15, atom='N')

Peak
----

A Peak object represents a single line in a peak list. It can be treated as a mutable sequence of Spin objects and can be used like any normal Python list. To initialize a Peak object, use the keyword argument ``spins`` to provide a list of Spin objects.

.. code-block:: python

    >>> spins = [npl.Spin(atom=atom) for atom in ('H', 'N', 'HA', 'CA')]
    >>> peak = npl.Peak(spins=spins)
    >>> [spin.atom for spin in peak]
    ['H', 'N', 'HA', 'CA']
    >>> del peak[1:3]
    >>> [spin.atom for spin in peak]
    ['H', 'CA']
    >>> peak.append(npl.Spin(atom='HB'))
    >>> [spin.atom for spin in peak]
    ['H', 'CA', 'HB']

Each Peak object may have additional attributes that relate to the peak as a whole. For example, Peak objects created from XEASY files usually have a ``volume`` attribute whereas Peak objects created from UPL files have a ``distance`` attribute. Furthermore, arbitrary attributes may be added to each Peak as needed. For example, when processing CEST data, users may want to add a ``CEST_profile`` attribute to each peak. Additional attributes can be added as keyword arguments at initialization or as attributes after the fact.

.. code-block:: python

    >>> peak = npl.Peak(volume=50000)
    >>> peak.CEST_profile = [0.4]*10
    >>> peak.volume
    50000
    >>> peak.CEST_profile
    [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4]

.. note::
    Only the NMRPipe and Sparky formats are flexible enough to write arbitrary Peak attributes to a file. See <add-reference-here> for more information.

PeakList
--------

PeakList objects are mutable sequences Peak objects and can be used as if they were Python lists.

.. code-block:: python

    for peak in peaklist[:5]:
        for spin in peak:
            print spin.atom
    atoms = [tuple(spin.atom for spin in peak) for peak in peaklist]
    del peaklist[18]
    peaklist[35:] = []

Just like Peak objects, PeakList objects also have attributes representing properties belonging to the peak list as a whole. The following attributes are pre-defined and are calculated by each PeakList object:

dims
~~~~

The ``dims`` attribute is an integer specifying the number of dimensions in the peak list. It corresponds to the number of Spin objects in each Peak object of the peak list. An ``AttributeError`` is raised if the PeakList is empty or if any two Peaks in the PeakList contain a different number of Spin objects. The following should always be true for non-empty PeakLists:

.. code-block:: python

    >>> peak = peaklist[0]
    >>> peaklist.dims == len(peak)
    True

anchors
~~~~~~~

The ``anchors`` attribute specifies which columns of the peak list correspond to spin anchors. A spin anchor is a directly attached proton/heavy atom pair. Each spin anchor is represented by a tuple of two integers, where each integer indexes Peak objects to extract the two spins forming the anchor. The index of the proton spin always comes first. The ``anchors`` attribute is a list of tuples indicating the spin anchors. Only one anchor is possible in 2D and 3D peak lists, but two anchors are possible in 4D peak lists.

.. code-block:: python

    >>> peaklist.anchors
    [(2, 0)]
    >>> peak = peaklist[0]
    >>> anchored_spins = [peak[i] for i in peaklist.anchors]
    >>> [(spin.res_num, spin.atom) for spin in anchored_spins]
    [(41, 'HD1'), (41, 'CD1')]

Modifying a peak list
=====================

Sorting
-------

To facilitate sorting the peaks by their assignments, Spin objects may be compared to each other with the comparison operators (<, <=, > and >=). These comparisons are only influenced by the assignment data, not by any other attributes of the spins. The default sorting order is by residue number, then sidechain position and finally atom name. Unassigned spins are always sorted last.

.. code-block:: python

    >>> spin1 = pl.Spin(res_num=24, atom='HB')
    >>> spin2 = pl.Spin(res_num=24, atom='HD1')
    >>> spin1 < spin2
    True

:class:`.Peak` objects may also be compared using the comparison operators, and once again, only the assignment data influences sorting. The default behavior for peaks sorts them as tuples of their respective spins. As a result, the order of the peak list dimensions (i.e. the order of spins in each peak) matters greatly when sorting peaks. This is especially evident in NOESY peak lists.

.. code-block:: python

    >>> spin1 = pl.Spin(res_num=28, atom='HG')
    >>> spin2 = pl.Spin(res_num=17, atom='HA')
    >>> peak1 = pl.Peak([spin1, spin2])
    >>> spin3 = pl.Spin(res_num=14, atom='HG2')
    >>> spin4 = pl.Spin(res_num=63, atom='H')
    >>> peak2 = pl.Peak([spin3, spin4])
    >>> peak1 < peak2
    False
    >>> print sorted([peak1, peak2])
    [Peak(spins=
    [Spin(res_num=14, atom='HG2'),
     Spin(res_num=63, atom='H')]), Peak(spins=
    [Spin(res_num=28, atom='HG'),
     Spin(res_num=17, atom='HA')])]

Use the ``sort_by_assignment`` :class:`.PeakList` method to change the default sort order. On its own, the only change made by ``sort_by_assignment`` is to include the influence of spin anchors when sorting. Alternatively, you can manually specify the sort order of dimensions using the ``order`` keyword argument.

.. code-block:: python

    >>> peaklist.sort_by_assignments(order=[1,0])
    >>> print peaklist
    PeakList(peaks=
    [Peak(spins=
    [Spin(res_num=28, atom='HG'),
     Spin(res_num=17, atom='HA')]),
     Peak(spins=
    [Spin(res_num=14, atom='HG2'),
     Spin(res_num=63, atom='H')])])

Filtering
---------

Peak attributes
===============
