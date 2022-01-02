#!/usr/bin/env python3

from collections import defaultdict
import itertools
import json

class Morpheme:
    def __init__(self):
        self.fields = []
        self.prefix = ''
        self.suffix = ''

MORPHEME_SEPARATORS = '<>/-='

def split_morph(s):
    ls = []
    cur = ''
    for c in s:
        if c in MORPHEME_SEPARATORS:
            if cur:
                ls.append(cur)
            ls.append(c)
            cur = ''
        else:
            cur += c
    if cur:
        ls.append(cur)
    return ls

class Word:
    def __init__(self):
        self.fields = []
        self.footnotes = []
    def json(self):
        lines = []
        for l, v in self.fields:
            if isinstance(l, int):
                lines.append(v)
            else:
                ls = []
                w = l[1] - l[0] + 1
                for i in range(w):
                    cur = ['']
                    for m in v:
                        cur[-1] += m.prefix
                        cur.append(m.fields[i])
                        cur.append(m.suffix)
                    ls.append(cur)
                lines.append(ls)
        return {'lines': lines, 'footnotes': self.footnotes}
    def process_morphs(self, ln, i, j, morphs):
        if all(x == None for x in morphs):
            self.fields.append(((i,j), []))
        else:
            err_loc = 'Columns %s through %s' % (i, j)
            ls1 = [split_morph(x or '') for x in morphs]
            m = max(len(x) for x in ls1)
            ls2 = [x if x else [None]*m for x in ls1]
            if min(len(x) for x in ls2) != m:
                ln.error('%s do not all have the same number of morphemes' % err_loc)
            morphs = []
            sep = ''
            for col in zip(*ls2):
                s = set(x for x in col if x)
                if len(s) == 1 and list(s)[0] in MORPHEME_SEPARATORS:
                    sep += list(s)[0]
                elif len(s) > 1 and any(c in MORPHEME_SEPARATORS for c in s):
                    ln.error('%s do not have the same morpheme separators' % err_loc)
                else:
                    m = Morpheme()
                    # TODO: is there a more intelligent way to split this?
                    # or a way to store it so it doesn't matter?
                    m.prefix = sep
                    sep = ''
                    m.fields = [s or '' for s in col]
                    morphs.append(m)
            if sep:
                if morphs:
                    morphs[-1].suffix = sep
                else:
                    ln.error('%s have morpheme separators but no morphemes' % err_loc)
            self.fields.append(((i,j), morphs))
    def from_tsv(self, ln, lang):
        pat = [('SPECIFIER', str)]
        pat += [(l.label, str) for l in lang.lines]
        pat.append(('FOOTNOTES', str))
        tup = ln.parse(pat[:2], pat[2:], True)
        ls = list(tup)[1:]
        m_start = 0
        m_ls = []
        for i, (l, v) in enumerate(zip(lang.lines, ls), 1):
            if l.ltype == 'morph':
                if not m_ls:
                    m_start = i
                m_ls.append(v)
            else:
                if m_ls:
                    self.process_morphs(ln, m_start, i-1, m_ls)
                self.fields.append((i, v or ''))

class Line:
    def __init__(self):
        self.words = []
        self.trans = {}
    def json(self):
        return {'words': [w.json() for w in self.words],
                'trans': self.trans}

class Sentence:
    def __init__(self):
        self.lines = {}
    def json(self):
        dct = {}
        for l, f in self.lines:
            if l not in dct:
                dct[l] = {'words': [], 'trans': {}, 'footnotes': {}}
            j = self.lines[(l, f)].json()
            if f == 0:
                dct[l]['words'] = j['words']
                dct[l]['trans'] = j['trans']
            else:
                dct[l]['footnotes'][f] = j
        return dct
    def from_tsv(self, blk, langs):
        def parse_loc(s, p):
            if s == p:
                return 1
            if s.startswith(p) and s[len(p):].isnumeric():
                return int(s[len(p):])
            return 0
        def pop_loc(lg, p):
            if len(lg) > 1:
                n = parse_loc(lg[-1], p)
                if n > 0:
                    return lg[:-1], n
            return lg, 0
        for ln in blk.lines:
            lg = ln.cols[0].split('-')
            if lg[0] not in langs:
                ln.error("Unknown language '%s'" % lg[0])
            lg, trans = pop_loc(lg, 'T')
            lg, footnote = pop_loc(lg, 'F')
            if len(lg) != 1:
                ln.error("Unable to interpret specifier '%s'" % ln.cols[0])
            loc = (lg[0], footnote)
            if loc not in self.lines:
                self.lines[loc] = Line()
            if trans != 0:
                self.lines[loc].trans[trans] = ln.cols[1]
            else:
                w = Word()
                w.from_tsv(ln, langs[lg[0]])
                self.lines[loc].words.append(w)

class LineType:
    def __init__(self):
        self.ltype = 'text'
        self.label = ''
    def json(self):
        return {'type': self.ltype, 'label': self.label}
    def from_tsv(self, ln):
        self.ltype, self.label = ln.parse([('TYPE', str), ('LABEL', str)], [], True)
        if self.ltype not in ['text', 'morph', 'trans']:
            ln.error("Line type must be one of 'text', 'morph', 'trans'")

class Language:
    def __init__(self):
        self.langid = ''
        self.name = ''
        self.lines = []
        self.translangs = []
    def json(self):
        lns = []
        for l in self.lines:
            if lns and lns[-1]['type'] == l.ltype:
                lns[-1]['labels'].append(l.label)
            else:
                lns.append({'type': l.ltype, 'labels': [l.label]})
        return {
            'id': self.langid,
            'name': self.name,
            'lines': lns,
            'trans': self.translangs
        }
    def from_tsv(self, blk):
        _, self.langid = blk.head.parse([('%LANG', str), ('ID', str)], [], True)
        data = blk.parse_dict(str, str)
        self.name = data['name']
        for b in blk.blocks:
            if b.head.head == 'TRANS':
                for l in b.lines:
                    self.translangs.append(l.cols[0])
            elif b.head.head == 'LINES':
                for l in b.lines:
                    lt = LineType()
                    lt.from_tsv(l)
                    self.lines.append(lt)
    def word_index(self, lineno):
        l = -1
        m = -1
        for n, ln in enumerate(self.lines, 1):
            if ln.ltype == 'morph':
                if m == -1:
                    l += 1
                m += 1
            else:
                m = -1
                l += 1
            if n == lineno:
                return (l, m)

class AutoDict:
    def __init__(self):
        self.lang = None
        self.src = 0
        self.trg = 0
        self.data = {}
    def from_tsv(self, blk, langs):
        _, self.lang, self.src, self.trg = blk.head.parse(
            [('%DICT', str), ('LANG', str), ('SOURCE', int), ('TARGET', int)],
            [], True)
        if self.lang not in langs:
            blk.head.error("Unknown language '%s'" % self.lang)
        l = langs[self.lang]
        for c in [self.src, self.trg]:
            if c > len(l.lines):
                blk.head.error('Language %s (%s) has no column %s' % (l.name, self.lang, c))
        self.data = blk.parse_dict(str, str)
    def apply(self, doc):
        lg = doc.langs[self.lang]
        sl, sm = lg.word_index(self.src)
        tl, tm = lg.word_index(self.trg)
        if sl != tl or sm == -1 or tm == -1:
            return # don't know what to do with this yet
        for w in doc.iter_words(lang=self.lang):
            if len(w.fields) <= sl:
                continue
            for m in w.fields[sl][1]:
                if m.fields[sm] and not m.fields[tm]:
                    m.fields[tm] = self.data.get(m.fields[sm], '')

class TSVLine:
    def __init__(self, text, lineno):
        self.text = text
        self.cols = text.strip().split('\t')
        self.lineno = lineno
        self.head = None
        if self.cols[0][0] == '%':
            self.head = self.cols[0][1:]
    def parse(self, req, opt, named=False):
        if len(req) > len(self.cols) or len(self.cols) > len(req) + len(opt):
            s = str(len(req))
            t = ''
            if opt:
                s = 'between %s and %d' % (s, len(opt))
            if named:
                t = '\nColumns: '
                t += ' '.join(x[0] for x in req)
                t += ' '
                t += ' '.join('['+x[0]+']' for x in opt)
            self.error('Expected %s columns but found %d%s' % (s, len(self.cols), t))
        ret = []
        ls = req + opt
        for i, (c, (r, t)) in enumerate(zip(self.cols, ls), 1):
            try:
                ret.append(t(c))
            except:
                l = '%s (%s)' % (r, i) if named else str(i)
                self.error("Expected %s but got '%s' in column %s" % (t, c, l))
        while len(ls) < len(ret):
            ret.append(None)
        return tuple(ret)
    def error(self, msg):
        raise SyntaxError('Error on line %s:\n%s\n%s' % (self.lineno, self.text.rstrip(), msg))
    def debug(self):
        print(self.cols)

class TSVBlock:
    def __init__(self, head, lines, blocks):
        self.head = head
        self.lines = lines
        self.blocks = blocks
    def parse_dict(self, ktype, vtype):
        ret = {}
        for l in self.lines:
            k, v = l.parse([('KEY', ktype), ('VAL', ktype)], [], True)
            if k in ret:
                l.error("Key '%s' specified multiple times" % k)
            ret[k] = v
        return ret
    def debug(self):
        print(self.head.head)
        self.head.debug()
        for l in self.lines:
            l.debug()
        print('')
        for b in self.blocks:
            b.debug()

def group_tsv_lines(lns):
    NEST = {
        '__ALL__': ['META', 'TEXT', 'DICT'],
        'DICT': [],
        'LANG': ['TRANS', 'LINES'],
        'LINE': [],
        'LINES': [],
        'META': ['LANG'],
        'TEXT': ['LINE'],
        'TRANS': []
    }
    head = lns[0]
    lines = list(itertools.takewhile(lambda l: l.head == None, lns[1:]))
    blocks = []
    rem = lns[len(lines)+1:]
    while rem and rem[0].head in NEST[head.head]:
        b, rem = group_tsv_lines(rem)
        blocks.append(b)
    return TSVBlock(head, lines, blocks), rem
        
def tsv_blocks(stream):
    lns = [TSVLine('%__ALL__', 0)]
    for n, line in enumerate(stream, 1):
        if not line:
            break
        if not line.isspace() and line[0] != '#':
            lns.append(TSVLine(line, n))
    blk, rem = group_tsv_lines(lns)
    if rem:
        raise SyntaxError('Unexpected header %s!' % rem[0].head)
    return blk

class Document:
    def __init__(self):
        self.title = ''
        self.lang_order = []
        self.langs = {}
        self.sents = []
        self.dicts = []
    def json(self):
        return {
            'title': self.title,
            'langs': {k:v.json() for k,v in self.langs.items()},
            'order': self.lang_order,
            'sents': [s.json() for s in self.sents]
        }
    def from_tsv(self, stream):
        blk = tsv_blocks(stream)
        for b in blk.blocks:
            if b.head.head == 'META':
                for l in b.lines:
                    if len(l.cols) == 2 and l.cols[0] == 'title':
                        self.title = l.cols[1]
                for b2 in b.blocks:
                    l = Language()
                    l.from_tsv(b2)
                    self.lang_order.append(l.langid)
                    self.langs[l.langid] = l
        for b in blk.blocks:
            if b.head.head == 'TEXT':
                for b2 in b.blocks:
                    if b2.head.head == 'LINE':
                        s = Sentence()
                        s.from_tsv(b2, self.langs)
                        self.sents.append(s)
            elif b.head.head == 'DICT':
                d = AutoDict()
                d.from_tsv(b, self.langs)
                self.dicts.append(d)
    def apply_dicts(self):
        for d in self.dicts:
            d.apply(self)
    def iter_words(self, lang=None, footnotes=None):
        for s in self.sents:
            for (lg, fn), ws in s.lines.items():
                if lang and lg != lang:
                    continue
                if footnotes and fn not in footnotes:
                    continue
                for w in ws.words:
                    yield w
    def find_unglossed_morphs(self):
        for lang in self.langs:
            miss = defaultdict(lambda: defaultdict(set))
            for w in self.iter_words(lang=lang):
                for loc, mls in w.fields:
                    if isinstance(mls, str):
                        continue
                    mn = loc[0]
                    for morph in mls:
                        if all(morph.fields):
                            continue
                        for i in range(len(morph.fields)):
                            if not morph.fields[i]:
                                continue
                            for j in range(len(morph.fields)):
                                if i == j or morph.fields[j]:
                                    continue
                                miss[i+mn][j+mn].add(morph.fields[i])
            if len(miss) > 0:
                print('Unglossed morphemes in %s:' % self.langs[lang].name)
                for l1 in sorted(miss.keys()):
                    for l2 in sorted(miss[l1].keys()):
                        print('  Entries on line %s without corresponding entry on line %s: %s' % (l1, l2, ' '.join(sorted(miss[l1][l2]))))

HTML_TEMPLATE = '''<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>{title}</title>
    <style>{css}</style>
  </head>
  <body>
    <div id="controls"></div>
    <div id="display"></div>
    <script type="text/javascript">{jquery}</script>
    <script type="text/javascript">
var LANGS = {langs};
var LANG_ORDER = {order};
var TEXT = {text};

{js}
    </script>
  </body>
</html>
'''

def make_html(doc):
    def readall(fname):
        with open(fname) as fin:
            return fin.read()
    blob = doc.json()
    return HTML_TEMPLATE.format(
        title=blob['title'],
        css=readall('multigloss.css'),
        jquery=readall('jquery-3.6.0.slim.min.js'),
        langs=json.dumps(blob['langs']),
        order=json.dumps(blob['order']),
        text=json.dumps(blob['sents']),
        js=readall('multigloss.js')
    )

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', action='store')
    parser.add_argument('outfile', action='store')
    parser.add_argument('-m', '--warn-morphemes', action='store_true',
                        help="Warn on un-glossed morphemes")
    args = parser.parse_args()

    with open(args.infile) as fin:
        d = Document()
        d.from_tsv(fin)
        d.apply_dicts()
        if args.warn_morphemes:
            d.find_unglossed_morphs()
        #print(json.dumps(d.json(), indent=2))
        #print(make_html(d))
        with open(args.outfile, 'w') as fout:
            fout.write(make_html(d))
