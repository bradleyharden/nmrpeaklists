========
Tutorial
========

The ``nmrpeaklists`` library can be used to read, write and edit NMR peak list files. It can also be used to convert between different peak list file formats. Currently, the library supports peak lists from NMRPipe and Sparky, and it can read peak lists in the XEASY and UPL formats.

The library was originally written to support data work flows involving CARA, CYANA and nlinLS. The :ref:`scripts <scripts>` provided with the library reflect this fact. However, it can be used equally well to support any data flow involving the supported peak list formats.

In the following tutorial, the code blocks assume that the ``nmrpeaklists`` library has been imported with the following command.

.. code-block:: python

    >>> import nmrpeaklists as npl

.. contents:: :local:

Data structures
===============

The ``nmrpeaklists`` library provides three data structures that aim to mimic the structure of a peak list. A :class:`~.peaklist.PeakList` object represents an entire peak list and is composed of a sequence of :class:`~.peaklist.Peak` objects. Each :class:`~.peaklist.Peak` object represents a single line in a peak list and is composed of a sequence of :class:`~.peaklist.Spin` objects.

Spin
----

A :class:`~.peaklist.Spin` object is a container that holds attributes of a particular NMR spin resonance. A peak in an N-dimensional NMR spectrum is associated with N different spin resonances. :class:`~.peaklist.Spin` objects aggregate attributes of the associated spin resonances, like chemical shift, assignment, line width, etc. The following three attributes are pre-defined for each :class:`~.peaklist.Spin` object:

+-----------+----------------------------------------------+
| Attribute | Meaning                                      |
+===========+==============================================+
| res_type  | Residue type                                 |
+-----------+----------------------------------------------+
| res_num   | Residue number or spin system number         |
+-----------+----------------------------------------------+
| atom      | Atom name                                    |
+-----------+----------------------------------------------+

Other attributes may be added to :class:`~.peaklist.Spin` objects as necessary. The following table provides a list of suggested attribute names for some common spin parameters:

+-----------+--------------------------------------------------------+
| Attribute | Meaning                                                |
+===========+========================================================+
| shift     | Chemical shift                                         |
+-----------+--------------------------------------------------------+
| shift_pts | Chemical shift in number of points (spectrum specific) |
+-----------+--------------------------------------------------------+
| width     | Line width of the peak in the corresponding dimension  |
+-----------+--------------------------------------------------------+

:class:`~.peaklist.Spin` attributes can be set upon initializing the :class:`~.peaklist.Spin` or added to the :class:`~.peaklist.Spin` after creation.

.. code-block:: python

    >>> spin = npl.Spin(atom='N')
    >>> print(spin)
    Spin(atom='N')
    >>> spin.res_num = 15
    >>> print(spin)
    Spin(res_num=15, atom='N')

Peak
----

A :class:`~.peaklist.Peak` object represents a single line in a peak list. It can be treated as a mutable sequence of :class:`~.peaklist.Spin` objects and can be used like any normal Python list. To initialize a :class:`~.peaklist.Peak` object, use the keyword argument ``spins`` to provide a list of :class:`~.peaklist.Spin` objects.

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

Each :class:`~.peaklist.Peak` object may have additional attributes that relate to the peak as a whole. For example, :class:`~.peaklist.Peak` objects created from XEASY files usually have a ``volume`` attribute, whereas :class:`~.peaklist.Peak` objects created from UPL files have a ``distance`` attribute. Furthermore, arbitrary attributes may be added to each :class:`~.peaklist.Peak` as needed. For example, when processing CEST data, users may want to add a ``CEST_profile`` attribute to each peak. Additional attributes can be added as keyword arguments at initialization or as attributes after the :class:`~.peaklist.Peak` has been created.

.. code-block:: python

    >>> peak = npl.Peak(volume=50000)
    >>> peak.CEST_profile = [0.4]*10
    >>> peak.volume
    50000
    >>> peak.CEST_profile
    [0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4]

.. note::
    Only the NMRPipe and Sparky formats are flexible enough to write any arbitrary Peak attribute to a file. See `Column Templates`_ for more information.

PeakList
--------

:class:`~.peaklist.PeakList` objects are mutable sequences of :class:`~.peaklist.Peak` objects and can be used as if they were Python lists.

.. code-block:: python

    >>> len(peaklist)
    12
    >>> for peak in peaklist:
    ...    peak.volume = 50000
    ...
    >>> peak = peaklist[8]
    >>> peak.volume
    50000

Just like :class:`~.peaklist.Peak` objects, :class:`~.peaklist.PeakList` objects also have attributes representing properties belonging to the peak list as a whole. The following attributes are pre-defined and are calculated by each :class:`~.peaklist.PeakList` object:

dims
~~~~

The ``dims`` attribute is an integer specifying the number of dimensions in the peak list. It corresponds to the number of :class:`~.peaklist.Spin` objects in each :class:`~.peaklist.Peak` object of the :class:`~.peaklist.PeakList`. An ``AttributeError`` is raised if the :class:`~.peaklist.PeakList` is empty or if any two :class:`~.peaklist.Peak` objects in the :class:`~.peaklist.PeakList` contain a different number of :class:`~.peaklist.Spin` objects. The following should always be true for a non-empty :class:`~.peaklist.PeakList`:

.. code-block:: python

    >>> peak = peaklist[0]
    >>> peaklist.dims == len(peak)
    True

anchors
~~~~~~~

The ``anchors`` attribute specifies which dimensions of the peak list correspond to spin anchors. A spin anchor is a directly attached proton/heavy atom pair. Each spin anchor is represented by a tuple of two integers, where the integers are indices into :class:`~.peaklist.Peak` objects to extract the two corresponding :class:`~.peaklist.Spin` objects that form the spin anchor. The index of the proton spin always comes first. The ``anchors`` attribute of a :class:`~.peaklist.PeakList` is a list of tuples indicating the spin anchors. Only one anchor is possible in 2D and 3D peak lists, but two anchors are possible in 4D peak lists.

.. code-block:: python

    >>> peaklist.anchors
    [(2, 0)]
    >>> anchor = peaklist.anchors[0]
    >>> peak = peaklist[0]
    >>> anchored_spins = [peak[i] for i in anchor]
    >>> [(spin.res_num, spin.atom) for spin in anchored_spins]
    [(41, 'HD1'), (41, 'CD1')]

Reading peak lists
==================

For each supported peak list file format, there exists a corresponding subclass of the :class:`~.files.PeakListFile` class.

+-------------+-----------------------------+
| File format | Subclass                    |
+=============+=============================+
| NMRPipe     | :class:`~.files.PipeFile`   |
+-------------+-----------------------------+
| Sparky      | :class:`~.files.SparkyFile` |
+-------------+-----------------------------+
| XEASY       | :class:`~.files.XeasyFile`  |
+-------------+-----------------------------+
| UPL         | :class:`~.files.UplFile`    |
+-------------+-----------------------------+

To read a peak list file, create an object of the appropriate subclass and run its :class:`~.files.PeakListFile.read_peaklist` method. These two steps can be performed in one line.

.. code-block:: python

    >>> peaklist = npl.XeasyFile().read_peaklist(filename)

Alternatively, if you need to modify the object before reading the peak list, you can perform the two actions separately.

.. code-block:: python

    >>> peaklistfile = npl.XeasyFile()
    >>> peaklist = peaklistfile.read_peaklist(filename)

Objects of :class:`~.files.PeakListFile` subclasses are usually only edited when the corresponding file type is customizable, i.e. columns in the peak list can be added, removed and rearranged. This is accomplished by modifying the object's :class:`~.columns.ColumnTemplate`. For more information, see `Column Templates`_.

XEASY format
------------

The XEASY peak list format provides a set of spin IDs for each peak, but it does not include any assignment data directly. Assignment data can only be obtained by referencing each spin ID against a mapping of spin IDs to their respective assignments. Consequently, users must perform an extra step when reading XEASY peak lists in order to incorporate assignment data.

The mapping between spin IDs and spin assignments can be provided in several different forms. The standard approach uses a sequence file and atom list to create the mapping. Alternatively, if the spin IDs relate to a CARA repository, then users can create the mapping as a single file using the :ref:`Lua script <lua_script>` provided with this library. Finally, if the XEASY peak list is an anchor peak list from CARA, then the peak list itself contains the assignment data as comments interleaved within the data.

The :class:`~.files.AssignmentFile` class defines an interface for this mapping. Subclasses of :class:`~.files.AssignmentFile` are specific to each file or set of files used to create the mapping. The data is read from the file(s) using the :class:`~.files.AssignmentFile` method :class:`~.files.AssignmentFile.read_file`.

+-----------------------+----------------------------------+
| File(s)               | Subclass                         |
+=======================+==================================+
| Atom list & Seq file  | :class:`~.files.AtomListSeqFile` |
+-----------------------+----------------------------------+
| CARA spin ID file     | :class:`~.files.CaraSpinsFile`   |
+-----------------------+----------------------------------+
| CARA anchor peak list | :class:`~.files.CaraAnchorFile`  |
+-----------------------+----------------------------------+

Objects of :class:`~.files.AssignmentFile` subclasses can be used directly, as if they were a dictionary mapping spin ID values to :class:`~.peaklist.Assignment` tuples. When the XEASY peak list is read, each :class:`~.peaklist.Spin` in the :class:`~.peaklist.PeakList` is given a ``spin_id`` attribute. The :class:`~.files.AssignmentFile` method :class:`~.files.AssignmentFile.assign_peaklist` takes a :class:`~.peaklist.PeakList` and sets the ``res_type``, ``res_num`` and ``atom`` attributes for each :class:`~.peaklist.Spin` based on its ``spin_id`` attribute.

.. code-block:: python

    >>> peaklist = npl.XeasyFile().read_peaklist(peaklist_filename)
    >>> spin = peaklist[0][0]
    >>> (spin.res_type, spin.res_num, spin.atom)
    (None, None, None)
    >>> spin.spin_id
    194
    >>> assignments = npl.CaraSpinsFile().read_file(spins_filename)
    >>> assignments[194]
    Assignment(res_type='H', res_num=43, atom='HA')
    >>> peaklist = assignments.assign_peaklist(peaklist)
    >>> (spin.res_type, spin.res_num, spin.atom)
    ('H', 43, 'HA')

Writing peak lists
==================



Modifying a peak list
=====================

Sorting
-------

To facilitate sorting a :class:`~peaklist.PeakList` by its :class:`~.peaklist.Peak` assignments, :class:`~.peaklist.Spin` objects may be compared to each other with the comparison operators (<, <=, > and >=). These comparisons are only influenced by the assignment data, not by any other attributes of the spins. The default sorting order is by residue number, then sidechain position and finally atom name. Unassigned spins are always sorted last.

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

Use the ``sort_by_assignment`` :class:`.PeakList` method to change the default sort order. By default, ``sort_by_assignment`` takes into account the spin anchors, but it still gives the highest sorting priority to the lowest-index Spins. Alternatively, you can manually specify the sort order using the ``order`` keyword argument.

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
