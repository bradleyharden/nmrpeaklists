from distutils.core import setup

setup(
    name='nmrpeaklists',
    version='0.9.0',
    author='Bradley J. Harden',
    author_email='bradleyharden@gmail.com',
    packages=['nmrpeaklists'],
    scripts=['bin/cara2tab', 'bin/cluster_tab',
             'bin/comment_peaklist', 'bin/filter_NOESY_fits',
             'bin/filter_spin_links', 'bin/find_eliminated_spin_links',
             'bin/print_tab_clusters'],
    url='',
    license='LICENSE',
    description='',
    long_description=open('README.md').read(),
    install_requires=[],
)
