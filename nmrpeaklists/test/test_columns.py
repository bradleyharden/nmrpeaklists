from __future__ import division, absolute_import, print_function
import unittest as ut
from ..columns import (
    Column, IgnoreColumn, PeakAttrColumn, PeakAttrListColumn, SpinAttrColumn,
    Res3LetterColumn, PipeNameColumn, PipeAnchorColumn, SparkyNameColumn,
    ColumnGroup, PeakAttrListGroup, SpinAttrGroup, PipeNameGroup,
    ColumnTemplate, PipeTemplate, SparkyTemplate, UplTemplate, XeasyTemplate)
from ..peaklist import PeakList, Peak, Spin


class ColumnTestCase(ut.TestCase):
    pass


class IgnoreTestCase(ut.TestCase):
    def setUp(self):
        self.column = IgnoreColumn('name', 'value')

    def test_fmt(self):
        self.assertEqual(self.column.fmt, '%5s')

    def test_get_value(self):
        self.assertEqual(self.column.get_value(None), 'value')

    def test_get_string(self):
        self.assertEqual(self.column.get_string(None), 'value')


class PeakAttrTestCase(ut.TestCase):
    def setUp(self):
        self.column = PeakAttrColumn('name', '%4d', 'attr')

    def test_get_value(self):
        peak = Peak(attr=12)
        value = self.column.get_value(peak)
        self.assertEqual(value, 12)

    def test_set_value(self):
        peak = Peak()
        self.column.set_value(peak, 10)
        self.assertEqual(peak.attr, 10)

    def test_set_value_overwrite(self):
        peak = Peak(attr=12)
        self.column.set_value(peak, 10)
        self.assertEqual(peak.attr, 10)

    def test_get_string(self):
        peak = Peak(attr=12)
        string = self.column.get_string(peak)
        self.assertEqual(string, '  12')

    def test_set_string(self):
        peak = Peak()
        self.column.set_string(peak, '10')
        self.assertEqual(peak.attr, 10)


class PeakAttrListTestCase(ut.TestCase):
    def setUp(self):
        self.column = PeakAttrListColumn('name', '%4d', 'attr', 7)

    def test_get_value(self):
        peak = Peak(attr=[12]*8)
        value = self.column.get_value(peak)
        self.assertEqual(value, 12)

    def test_get_value_default(self):
        peak = Peak()
        value = self.column.get_value(peak, None)
        self.assertEqual(value, None)

    def test_get_value_attr_err(self):
        peak = Peak()
        self.assertRaises(AttributeError, self.column.get_value, peak)

    def test_get_value_type_err(self):
        peak = Peak(attr=12)
        self.assertRaises(TypeError, self.column.get_value, peak)

    def test_get_value_index_err(self):
        peak = Peak(attr=[12]*6)
        self.assertRaises(IndexError, self.column.get_value, peak)

    def test_set_value(self):
        peak = Peak(attr=[10]*8)
        self.column.set_value(peak, 15)
        self.assertEqual(peak.attr, [10]*7 + [15])

    def test_set_value_extend(self):
        peak = Peak(attr=[10]*4)
        self.column.set_value(peak, 15)
        self.assertEqual(peak.attr, [10]*4 + [None]*3 + [15])

    def test_set_value_overwrite(self):
        peak = Peak()
        self.column.set_value(peak, 15)
        self.assertEqual(peak.attr, [None]*7 + [15])


class SpinAttrTestCase(ut.TestCase):
    def setUp(self):
        self.column = SpinAttrColumn('name', '%5.2f', 'attr', 2)

    def test_get_value(self):
        spins = [Spin(), Spin(), Spin(attr=8.751)]
        peak = Peak(spins=spins)
        value = self.column.get_value(peak)
        self.assertEqual(value, 8.751)

    def test_get_value_default(self):
        spins = [Spin(), Spin(), Spin()]
        peak = Peak(spins=spins)
        value = self.column.get_value(peak, None)
        self.assertEqual(value, None)

    def test_get_value_index_err(self):
        spins = [Spin(), Spin()]
        peak = Peak(spins=spins)
        self.assertRaises(IndexError, self.column.get_value, peak)

    def test_get_value_attr_err(self):
        spins = [Spin(), Spin(), Spin()]
        peak = Peak(spins=spins)
        self.assertRaises(AttributeError, self.column.get_value, peak)

    def test_set_value(self):
        spins = [Spin(), Spin(), Spin()]
        peak = Peak(spins=spins)
        self.column.set_value(peak, 8.75)
        self.assertEqual(peak[2].attr, 8.75)


class Res3LetterTestCase(ut.TestCase):
    def setUp(self):
        self.column = Res3LetterColumn('name', 1)

    def test_get_string(self):
        spins = [Spin(), Spin(res_type='G'), Spin()]
        peak = Peak(spins=spins)
        string = self.column.get_string(peak)
        self.assertEqual(string, 'GLY')

    def test_set_string(self):
        spins = [Spin(), Spin(), Spin()]
        peak = Peak(spins=spins)
        self.column.set_string(peak, 'GLY')
        self.assertEqual(peak[1].res_type, 'G')


class PipeNameTestCase(ut.TestCase):
    def setUp(self):
        self.column = PipeNameColumn(1, 5, 5)

    def test_get_fmt(self):
        self.assertEqual(self.column.fmt, '%11s')

    def test_set_fmt(self):
        self.column.fmt = '%7s'
        self.assertEqual(self.column.fmt, '%11s')

    def test_get_value(self):
        spins = [Spin(),
                 Spin(res_type='I', res_num=15, atom='HG'),
                 Spin()]
        peak = Peak(spins=spins)
        value = self.column.get_value(peak)
        self.assertEqual(value, 'I15-HG')

    def test_get_string(self):
        spins = [Spin(), Spin(res_type='I', res_num=15, atom='HG'), Spin()]
        peak = Peak(spins=spins)
        string = self.column.get_string(peak)
        self.assertEqual(string, '  I15-HG   ')

    def test_set_value(self):
        spins = [Spin(), Spin(), Spin()]
        peak = Peak(spins=spins)
        self.column.set_value(peak, 'L7-HD1')
        tupl = (peak[1].res_type, peak[1].res_num, peak[1].atom)
        self.assertEqual(tupl, ('L', 7, 'HD1'))
        self.assertEqual(peak[1].name, 'L7-HD1')

    def test_update_from_peaklist(self):
        spins = [Spin(), Spin(res_type='I', res_num=15, atom='HG'), Spin()]
        peaklist = PeakList()
        peaklist.append(Peak(spins=spins))
        spins = [Spin(), Spin(res_type='L', res_num=103, atom='HD22'), Spin()]
        peaklist.append(Peak(spins=spins))
        self.column.update_from_peaklist(peaklist)
        self.assertEqual(self.column.res_width, 4)
        self.assertEqual(self.column.atom_width, 4)


class PipeAnchorTestCase(ut.TestCase):
    def setUp(self):
        self.column = PipeAnchorColumn((1, 0), 5, 10)

    def test_get_fmt(self):
        self.assertEqual(self.column.fmt, '%17s')

    def test_set_fmt(self):
        self.column.fmt = '%7s'
        self.assertEqual(self.column.fmt, '%17s')

    def test_get_value(self):
        peak = Peak(spins=[Spin(res_type='I', res_num=15, atom='N'),
                           Spin(res_type='I', res_num=15, atom='HN')])
        value = self.column.get_value(peak)
        self.assertEqual(value, 'I15-HN/N')

    def test_get_string(self):
        peak = Peak(spins=[Spin(res_type='I', res_num=15, atom='N'),
                           Spin(res_type='I', res_num=15, atom='HN')])
        string = self.column.get_string(peak)
        self.assertEqual(string, '  I15-HN/N       ')

    def test_set_value(self):
        peak = Peak(spins=[Spin(), Spin()])
        self.column.set_string(peak, 'L7-HN/N')
        tupl = (peak[0].res_type, peak[0].res_num, peak[0].atom)
        self.assertEqual(tupl, ('L', 7, 'N'))
        tupl = (peak[1].res_type, peak[1].res_num, peak[1].atom)
        self.assertEqual(tupl, ('L', 7, 'HN'))
        self.assertEqual(peak[0].name, 'L7-N')
        self.assertEqual(peak[1].name, 'L7-HN')

    def test_update_from_peaklist(self):
        peaklist = PeakList()
        spins = [Spin(res_type='I', res_num=15, atom='N'),
                 Spin(res_type='I', res_num=15, atom='HN')]
        peaklist.append(Peak(spins=spins))
        spins = [Spin(res_type='I', res_num=150, atom='CA'),
                 Spin(res_type='I', res_num=150, atom='HA')]
        peaklist.append(Peak(spins=spins))
        self.column.update_from_peaklist(peaklist)
        self.assertEqual(self.column.res_width, 4)
        self.assertEqual(self.column.atom_width, 4)


class SparkyNameTestCase(ut.TestCase):
    pass


class PeakAttrListGroupTestCase(ut.TestCase):
    def setUp(self):
        names = ['Z_A%d' % i for i in range(12)]
        self.group = PeakAttrListGroup(names, '%7.3f', 'profile')
        self.column_names = ['Z_A0', 'Z_A2', 'Z_A3', 'Z_A6']
        self.peaklist = PeakList(peaks=[
            Peak(profile=[8, None, 3, 4, None, None, 12, None]),
            Peak(profile=[8, None, 3, 4, None, None, 12, None]),
            Peak(profile=[8, None, 3, 4, None, None, 12, None]),
            Peak(profile=[8, None, 3, 4, None, None, 12, None])
        ])
        self.columns = [PeakAttrListColumn('Z_A0', '%7.3f', 'profile', 0, 7),
                        PeakAttrListColumn('Z_A2', '%7.3f', 'profile', 2, 7),
                        PeakAttrListColumn('Z_A3', '%7.3f', 'profile', 3, 7),
                        PeakAttrListColumn('Z_A6', '%7.3f', 'profile', 6, 7)]

    def test_generate_columns(self):
        columns = self.group.generate_columns([0, 2, 3, 6])
        for col1, col2 in zip(columns, self.columns):
            self.assertEqual(vars(col1), vars(col2))

    def test_resolve_from_names(self):
        columns = self.group.resolve_from_names(self.column_names)
        for col1, col2 in zip(columns, self.columns):
            self.assertEqual(vars(col1), vars(col2))

    def test_resolve_from_peaklist(self):
        columns = self.group.resolve_from_peaklist(self.peaklist)
        for col1, col2 in zip(columns, self.columns):
            self.assertEqual(vars(col1), vars(col2))


class SpinAttrGroupTestCase(ut.TestCase):
    def setUp(self):
        names = ['%s_PPM' % d for d in 'XYZA']
        self.group = SpinAttrGroup(names, '%7.3f', 'ppm')
        self.column_names = ['Y_PPM', 'X_PPM']
        self.peaklist = PeakList(peaks=[
            Peak(spins=[Spin(ppm=8.124), Spin(ppm=121.934), Spin(ppm=None)]),
            Peak(spins=[Spin(ppm=7.589), Spin(ppm=117.348), Spin(ppm=None)]),
            Peak(spins=[Spin(ppm=6.923), Spin(ppm=128.257), Spin(ppm=None)]),
            Peak(spins=[Spin(ppm=9.235), Spin(ppm=125.695), Spin(ppm=None)]),
        ])
        self.columns = [SpinAttrColumn('X_PPM', '%7.3f', 'ppm', 0),
                        SpinAttrColumn('Y_PPM', '%7.3f', 'ppm', 1)]

    def test_generate_columns(self):
        columns = self.group.generate_columns([0, 1])
        for col1, col2 in zip(columns, self.columns):
            self.assertEqual(vars(col1), vars(col2))

    def test_resolve_from_names(self):
        columns = self.group.resolve_from_names(self.column_names)
        for col1, col2 in zip(columns, self.columns):
            self.assertEqual(vars(col1), vars(col2))

    def test_resolve_from_peaklist(self):
        columns = self.group.resolve_from_peaklist(self.peaklist)
        for col1, col2 in zip(columns, self.columns):
            self.assertEqual(vars(col1), vars(col2))


class PipeNameGroupTestCase(ut.TestCase):
    def setUp(self):
        self.group = PipeNameGroup()
        self.column_names = ['ZY_NAME', 'X_NAME']
        self.peaklist = PeakList(peaks=[
            Peak(spins=[
                Spin(res_type='H', res_num=45, atom='H'),
                Spin(res_type='I', res_num=15, atom='N'),
                Spin(res_type='I', res_num=15, atom='H')]),
            Peak(spins=[
                Spin(res_type='Q', res_num=46, atom='H'),
                Spin(res_type='L', res_num=16, atom='N'),
                Spin(res_type='L', res_num=16, atom='H')]),
            Peak(spins=[
                Spin(res_type='N', res_num=30, atom='H'),
                Spin(res_type='Q', res_num=17, atom='N'),
                Spin(res_type='Q', res_num=17, atom='H')])])
        self.columns_from_names = [PipeNameColumn(0, 4, 4),
                                   PipeAnchorColumn((2, 1), 4, 8)]
        self.columns_from_peaks = [PipeAnchorColumn((2, 1), 4, 8),
                                   PipeNameColumn(0, 4, 4)]
        self.columns_updated = [PipeAnchorColumn((2, 1), 3, 2),
                                PipeNameColumn(0, 3, 1)]

    def test_generate_columns(self):
        columns = self.group.generate_columns([(2, 1), 0])
        for col1, col2 in zip(columns, self.columns_from_peaks):
            self.assertEqual(vars(col1), vars(col2))

    def test_resolve_from_names(self):
        columns = self.group.resolve_from_names(self.column_names)
        for col1, col2 in zip(columns, self.columns_from_names):
            self.assertEqual(vars(col1), vars(col2))

    def test_resolve_from_peaklist(self):
        columns = self.group.resolve_from_peaklist(self.peaklist)
        for col1, col2 in zip(columns, self.columns_from_peaks):
            self.assertEqual(vars(col1), vars(col2))

    def test_update_from_peaklist(self):
        columns = self.group.resolve_from_peaklist(self.peaklist)
        for column in columns:
            column.update_from_peaklist(self.peaklist)
        for col1, col2 in zip(columns, self.columns_updated):
            self.assertEqual(vars(col1), vars(col2))


#loadTestsFromTestCase = ut.TestLoader().loadTestsFromTestCase
#column_suite = loadTestsFromTestCase(ColumnTestCase)
#ignore_suite = loadTestsFromTestCase(IgnoreTestCase)
#peak_attr_suite = loadTestsFromTestCase(PeakAttrTestCase)
#peak_attr_list_suite = loadTestsFromTestCase(PeakAttrListTestCase)
#spin_attr_suite = loadTestsFromTestCase(SpinAttrTestCase)
#pipe_name_suite = loadTestsFromTestCase(PipeNameTestCase)
#pipe_anchor_suite = loadTestsFromTestCase(PipeAnchorTestCase)
#spin_attr_group_suite = loadTestsFromTestCase(SpinAttrGroupTestCase)
#peak_attr_list_group_suite = loadTestsFromTestCase(PeakAttrListGroupTestCase)
#pipe_name_group_suite = loadTestsFromTestCase(PipeNameGroupTestCase)
#
#all_suites = ut.TestSuite([
#    column_suite, ignore_suite, peak_attr_suite, peak_attr_list_suite,
#    spin_attr_suite, pipe_name_suite, pipe_anchor_suite, spin_attr_group_suite,
#    peak_attr_list_group_suite, pipe_name_group_suite])
#ut.TextTestRunner(verbosity=2).run(all_suites)
