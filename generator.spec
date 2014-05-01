# -*- mode: python -*-
a = Analysis(['bin/generator.py'],
             pathex=['/apasvo'],
             hiddenimports=['scipy.special._ufuncs_cxx'])

# Added data
data = Tree('./bfirls', prefix='bfirls')
data += Tree('./docs', prefix='docs')
data += [('COPYING.txt', 'COPYING.txt', 'DATA'),
                ('README', 'README', 'DATA'),
                ('README.md', 'README.md', 'DATA')]

# Removed data 
a.datas = [x for x in a.datas if not
           os.path.dirname(x[1]).startswith("C:\\Python27\\lib\site-packages\\matplotlib\\mpl-data\\sample_data")]
a.datas = [x for x in a.datas if not
           os.path.dirname(x[1]).startswith("C:\\Python27\\lib\\site-packages\\matplotlib\\mpl-data\\fonts")]


pyz = PYZ(a.pure)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='generator.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True,
          icon='res/images/app.ico')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               data,
               strip=None,
               upx=True,
               name='generator')

