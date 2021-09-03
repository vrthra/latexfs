#!/usr/bin/env python
# adapted from here: https://github.com/gehaxelt/Python-InMemoryFS/
import os
import sys
import errno
import string
import pudb
bp = pudb.set_trace

from fuse import FUSE, FuseOSError, Operations

import copy
import time

SECTION_BEGIN = '\\section{'
SECTIONS_END = '\\bibliographystyle{'
MAIN_TEX_FILE='_.tex'
ORIGINAL_TEX_FILE='.tex'

class SplitLatex:
    def split_sections(self, data):
        lines = data.split('\n')
        sections = [[]]
        while lines:
            line, *lines = lines
            if line.startswith(SECTION_BEGIN):
                sections.append([line])
            elif line.startswith(SECTIONS_END):
                sections.append([line])
            else:
                sections[-1].append(line)
        return sections


    def process_section(self, lines):
        if lines[0].startswith(SECTION_BEGIN):
            assert len(lines) >= 2
            sec_name = lines[0]
            sec_label = lines[1]
            # todo: if label does not exist, make up one from sec_name
            assert sec_label.startswith('\label{') and sec_label[-1] == '}'
            return (sec_name, sec_label[7:-1], '\n'.join(lines))
        elif lines[0].startswith(SECTIONS_END):
            return ('_end', '_end', '\n'.join(lines))
        else:
            return ('_start', '_start', '\n'.join(lines))

    def __init__(self, tex_file):
        with open(tex_file, encoding="utf-8") as f: data = f.read()
        my_items = self.split_sections(data)
        sections = []
        for section in my_items:
            name, label, src = self.process_section(section)
            print(name, label)
            sections.append((name, label, src))

        self.sections = sections

class LatexFS(Operations):
    def __init__(self, latex_file):
        self.latex_file = latex_file
        self.parsed = SplitLatex(latex_file)
        self.fs = {"/": {}}
        main = []
        for sname, label, content in self.parsed.sections:
            if sname == '_start' or sname == '_end':
                main.append(content)
            else:
                main.append('\include{%s}' % label)
                self.fs["/"][label + '.tex'] = bytes(content, 'utf-8')

        self.fs["/"][MAIN_TEX_FILE] = bytes('\n'.join(main), 'utf-8')

        self.meta = {
            "/": {
                'st_atime': time.time(),
                'st_mtime': time.time(),
                'st_ctime': time.time(),
                'st_mode': 0o00040770,
                'st_nlink': 0,
                'st_size': 0,
                'st_gid': os.getuid(),
                'st_uid': os.getgid(),
                }
        }
        for k in self.fs['/']:
            self.meta['/' + k] = {
                'st_atime': time.time(),
                'st_mtime': time.time(),
                'st_ctime': time.time(),
                'st_mode': 0o0100770,
                'st_nlink': 0,
                'st_size': len(self.fs['/'][k]),
                'st_gid': os.getuid(),
                'st_uid': os.getgid(),
                }
        self.recreate_main('')

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join("/", partial)
        return path

    def _the_dir(self, f_path):
        d = "/".join(f_path.split("/")[:-1])
        return '/' if d == '' else d

    def _the_file(self, f_path):
        return f_path.split("/")[-1]


    def _debug(self):
        print('FS')
        print(self.fs)
        print('Meta')
        print(self.meta)

    # Filesystem methods
    # ==================

    def getattr(self, path, fh=None):
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)
        the_file = self._the_file(full_path)
        print("[*] getattr: ", full_path)

        if not full_path in self.meta.keys():
            raise FuseOSError(errno.ENOENT)

        if the_dir in self.fs and the_file in self.fs[the_dir]:
            # it's a file, update it's size
            self.meta[full_path]['st_size'] = len(self.fs[the_dir][the_file])

        if full_path in self.fs.keys():
            # it's a directory, update it's size
            self.meta[full_path]['st_size'] = sum([len(self.fs[full_path][k]) for k in self.fs[full_path].keys()])

        return self.meta[full_path]

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)

        print("[*] readdir: ", full_path, the_dir)

        dirents = ['.', '..']
        if the_dir in self.fs.keys():
            dirents.extend([f for f in self.fs[full_path]])

        lst = [x.lstrip(full_path) for x in self.fs.keys() if x.startswith(the_dir) and \
                "/" not in x.lstrip(full_path) and \
                x.lstrip(full_path) != '']
        dirents.extend(lst)

        for r in dirents: yield r

    def mknod(self, path, mode, dev):
        print('^')
        self._debug()
        print('_')
        print("[*] mknod")

    def statfs(self, path):
        print("[*] statfs")
        # Some numbers are chosen arbitrarily
        return {
            'f_bavail': 0,
            'f_bfree': 0,
            'f_blocks': len(self.meta),
            'f_bsize': 0,
            'f_favail': 0,
            'f_ffree': 0,
            'f_files': len(self.meta),
            'f_flag': 0,
            'f_frsize': 0,
            'f_namemax': 2**32
        }

    def utimens(self, path, times=None):
        full_path = self._full_path(path)

        print("[*] utimens: ", full_path)
        if not full_path in self.meta.keys():
            raise FuseOSError(errno.ENOENT)

        if times:
            self.meta[full_path]['st_atime'] = times[0]
            self.meta[full_path]['st_mtime'] = times[1]
        else:
            self.meta[full_path]['st_atime'] = time.time()
            self.meta[full_path]['st_mtime'] = time.time()

        return 0

    def regenerate_original(self):
        # first read main_tex.
        main_tex = self.fs["/"][MAIN_TEX_FILE].decode('utf-8')
        lines = []
        for line in main_tex.split('\n'):
            if line.startswith('\include{') and line.endswith('}'):
                inc_file = line[len('\include{'):-1] + '.tex'
                lines.append(self.fs['/'][inc_file].decode('utf-8'))
            else:
                lines.append(line)
        self.fs['/'][ORIGINAL_TEX_FILE] = bytes('\n'.join(lines), 'utf-8')
        self.meta['/' + ORIGINAL_TEX_FILE] = {
                'st_atime': time.time(),
                'st_mtime': time.time(),
                'st_ctime': time.time(),
                'st_mode': 0o0100770,
                'st_nlink': 0,
                'st_size': len(self.fs['/'][ORIGINAL_TEX_FILE]),
                'st_gid': os.getuid(),
                'st_uid': os.getgid(),
                }


    def interpret_main_tex(self):
        main_tex = self.fs["/"][MAIN_TEX_FILE].decode('utf-8')
        includes = []
        for line in main_tex.split('\n'):
            if line.startswith('\include{') and line.endswith('}'):
                inc_file = line[len('\include{'):-1] + '.tex'
                includes.append(inc_file)

        # for k in list(self.fs['/']):
        #     if k == ORIGINAL_TEX_FILE: continue
        #     if k == MAIN_TEX_FILE: continue
        #     if k not in includes:
        #         print('deleting:', k)
        #         del self.fs['/'][k]
        for k in includes:
            if k not in self.fs['/']:
                print('Creating %s'% k )
                my_buf = "\section{%s}\n\label{%s}\n" % (k, k)
                self.fs['/'][k] = bytes(my_buf, 'utf-8')
                self.meta['/' + k] = {
                        'st_atime': time.time(),
                        'st_mtime': time.time(),
                        'st_ctime': time.time(),
                        'st_mode': 0o0100770,
                        'st_nlink': 0,
                        'st_size': len(self.fs['/'][k]),
                        'st_gid': os.getuid(),
                        'st_uid': os.getgid(),
                        }

    def recreate_main(self, path):
        if path == '/%s' % MAIN_TEX_FILE:
            self.interpret_main_tex()
            self.regenerate_original()
        else:
            self.regenerate_original()

    # File methods
    # ============

    def open(self, path, flags):
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)
        the_file = self._the_file(full_path)

        print("[*] open: ", full_path, the_dir, the_file)
        if not the_dir in self.fs.keys():
            raise FuseOSError(38)
        if not the_file in self.fs[the_dir].keys():
            raise FuseOSError(38)

        return 1337

    def read(self, path, length, offset, fh):
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)
        the_file = self._the_file(full_path)

        print("[*] read: ", full_path, the_dir, the_file, offset, length)
        if not the_dir in self.fs.keys():
            raise FuseOSError(38)

        if not the_file in self.fs[the_dir].keys():
            raise FuseOSError(38)

        return self.fs[the_dir][the_file][offset:offset+length]


    def write(self, path, buf, offset, fh):
        # if the write is to MAIN_TEX_FILE then handle it differently.
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)
        the_file = self._the_file(full_path)

        print("[*] write: ", full_path, the_dir, the_file, offset)
        if not the_dir in self.fs.keys():
            raise FuseOSError(38)
        if not the_file in self.fs[the_dir].keys():
            raise FuseOSError(38)

        cur_bytes = self.fs[the_dir][the_file][offset:] + bytes(buf)
        self.fs[the_dir][the_file] = cur_bytes
        self.recreate_main(path)
        return len(bytes(buf))

    def truncate(self, path, length, fh=None):
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)
        the_file = self._the_file(full_path)

        print("[*] truncate: ", full_path, the_dir, the_file)
        if not the_dir in self.fs.keys():
            raise FuseOSError(38)
        if not the_file in self.fs[the_dir].keys():
            raise FuseOSError(38)

        self.fs[the_dir][the_file] = bytes('', 'utf-8')
        #self.meta[the_dir + the_file] = 
        self.recreate_main(path)

    def unlink(self, path):
        # if path is _.tex it is error, else recreate _ also.
        full_path = self._full_path(path)
        the_dir = self._the_dir(full_path)
        the_file = self._the_file(full_path)

        print("[*] unlink: ", full_path, the_dir, the_file)

        if not the_dir in self.fs.keys():
            raise FuseOSError(38)

        if not the_file in self.fs[the_dir].keys():
            raise FuseOSError(38)

        del self.fs[the_dir][the_file]
        del self.meta[full_path]
        main_tex = self.fs["/"][MAIN_TEX_FILE].decode('utf-8')
        my_lines = []
        for line in main_tex.split('\n'):
            if line[len('\\include{'):-1] == the_file[:-4]:
                print("removing: ", the_file)
                continue
            else:
                print(repr(line))
                my_lines.append(line)
        self.fs["/"][MAIN_TEX_FILE] = bytes("\n".join(my_lines), 'utf-8')
        self.recreate_main(path)

        return 0

def init_fs(latex_file, mount):
    FUSE(LatexFS(latex_file), mount, nothreads=True, foreground=True)

