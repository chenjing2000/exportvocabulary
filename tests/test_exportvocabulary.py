import copy
import json
from pathlib import Path
import tempfile
import unittest
import exportvocabulary as e


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_settings_recovery(self):
        self.assertEqual(e.load_settings(self.root), e.DEFAULTS)
        p=self.root/'latex-vocabulary-settings.json'
        config=copy.deepcopy(e.DEFAULTS); config['word']['color']='#123456'
        p.write_text(json.dumps(config),encoding='utf8')
        self.assertEqual(e.load_settings(self.root),config)
        p.unlink(); self.assertEqual(e.load_settings(self.root),config)
        p.write_text('{bad',encoding='utf8')
        self.assertEqual(e.load_settings(self.root),config)
        self.assertEqual(len(list(self.root.glob('*.corrupted.*.json'))),1)

    def test_invalid_settings(self):
        for obj in [{'word':{'color':'red'}},{'page':{'margin_top_mm':-1}},{'columns':{'count':1}},{'fonts':{'english':r'\input'}}]:
            with self.assertRaises(ValueError): e.validate_settings(obj)
        self.assertEqual(e.validate_settings({'word':{'color':'#000000'}})['word']['color'],'#000000')

    def test_data(self):
        p=self.root/'A.vocabulary.json'
        w={'word':'A&B','phonetic_us':'/ə/','family': ['IGNORE'],'meanings':[{'pos':'n.','meaning':'中文 50%'},{'pos':'n.','meaning':'中文 50%'}]}
        p.write_text(json.dumps({'filetype':'vocabulary','words':[w,w]}),encoding='utf8')
        original=p.read_bytes(); words=e.load_vocabulary(p)
        a=e.render_article(words,e.stem(p))
        self.assertEqual(a.count(r'\vocab{A\&B}{/ə/}'),2)
        self.assertEqual(a.count(r'中文 50\%'),4)
        self.assertNotIn('IGNORE',a); self.assertEqual(p.read_bytes(),original)
        self.assertEqual(e.output_file(p),self.root/'latex-vocabulary'/'A.vocabulary.tex')
        w['phonetic_uk']='/UK/'; self.assertIn('/UK/',e.render_article([w],'A'))
        self.assertNotIn('/ə/',e.render_article([w],'A'))

    def test_merge_and_empty(self):
        a=e.render_article([],'A'); b=e.render_article([],'B')
        t=(e.HOME/'template.tex').read_text(encoding='utf8')
        out=e.render_document([a,b],e.DEFAULTS,t)
        self.assertEqual(out.count(r'\clearpage'),1)
        self.assertIn('B7394D',out); self.assertIn('0A7785',out)
        self.assertNotIn('@@',out)
        self.assertEqual(out,e.render_document([a,b],e.DEFAULTS,t))

    def test_discovery(self):
        for n in ['Article 10','Article 2','Article 1','audio','latex-vocabulary']:
            d=self.root/n; d.mkdir(); (d/'A.vocabulary.json').touch()
        found,errors=e.discover_files([self.root,self.root/'Article 2'/'A.vocabulary.json'])
        self.assertFalse(errors)
        self.assertEqual([p.parent.name for p in found],['Article 1','Article 2','Article 10'])

    def test_no_overwrite(self):
        p=self.root/'A.tex'; e.atomic_write(p,'old',False)
        with self.assertRaises(FileExistsError): e.atomic_write(p,'new',False)
        self.assertEqual(p.read_text(),'old')
        e.atomic_write(p,'new'); self.assertEqual(p.read_text(),'new')
        with self.assertRaises(ValueError): e.check_output(self.root/'A.json')
        with self.assertRaises(ValueError): e.check_output(e.HOME/'template.tex')

    def test_invalid_input(self):
        p=self.root/'bad.json'; p.write_text('{"filetype":"vocabulary","words":[null]}')
        with self.assertRaises(ValueError): e.load_vocabulary(p)

    def test_escaping(self):
        self.assertEqual(e.escape_latex('\\{}%#&_$~^'),r'\textbackslash{}\{\}\%\#\&\_\$\textasciitilde{}\textasciicircum{}')

if __name__=='__main__': unittest.main()
