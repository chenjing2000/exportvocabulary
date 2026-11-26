#!/usr/bin/env python3
"""Export vocabulary JSON to standalone LaTeX (Python 3.10+)."""
import argparse
import copy
import json
import math
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from datetime import datetime

HOME = Path(__file__).resolve().parent
DEFAULTS = {
    'page': {'paper':'a4paper','orientation':'portrait','margin_top_mm':18,'margin_bottom_mm':18,'margin_left_mm':18,'margin_right_mm':18,'page_number':True},
    'fonts': {'english':'TeX Gyre Termes','chinese':'Source Han Serif SC','phonetic':'Charis SIL'},
    'title': {'font_size_pt':18,'line_height_pt':22,'space_after_pt':10},
    'columns': {'count':2,'gap_mm':8,'rule_width_pt':0},
    'word': {'font_size_pt':12,'line_height_pt':15,'color':'#B7394D'},
    'phonetic': {'font_size_pt':10,'color':'#0A7785','space_before_pt':5},
    'meaning': {'font_size_pt':11,'line_height_pt':14,'pos_gap_pt':4},
    'spacing': {'entry_gap_pt':5,'meaning_gap_pt':0},
}
PAPERS = {'a4paper':(210,297),'a5paper':(148,210),'letterpaper':(215.9,279.4),'legalpaper':(215.9,355.6),'a3paper':(297,420)}
EXCLUDED = {'audio','cache','userdata','__pycache__','latex-vocabulary'}
ESCAPES = dict(zip('&%$#_{}', (r'\&',r'\%',r'\$',r'\#',r'\_',r'\{',r'\}')))
ESCAPES.update({'\\':r'\textbackslash{}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'})


def warn(message):
    print(f'[WARNING] {message}', file=sys.stderr)


def escape_latex(value):
    return ''.join(ESCAPES.get(c,c) for c in value.replace('\r\n',' ').replace('\r',' ').replace('\n',' ').replace('\t',' '))


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'), parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f'Invalid JSON constant: {x}')))


def atomic_write(path, content, overwrite=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.exportvocabulary-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if overwrite:
            os.replace(name, path)
        else:
            # Atomic no-clobber publication on NTFS and ordinary local filesystems.
            os.link(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def validate_settings(raw):
    if not isinstance(raw, dict):
        raise ValueError('Settings must be an object')
    result = copy.deepcopy(raw)
    for section, fields in DEFAULTS.items():
        group = result.setdefault(section, {})
        if not isinstance(group, dict):
            raise ValueError(f'{section} must be an object')
        for key, default in fields.items():
            val = group.setdefault(key, default)
            label = f'{section}.{key}'
            if isinstance(default, bool):
                valid = type(val) is bool
            elif isinstance(default, int):
                valid = type(val) in (int,float) and math.isfinite(val) and 0 <= val <= 1000
                if key in ('font_size_pt','line_height_pt'):
                    valid = valid and 0 < val <= 100
                if key == 'count':
                    valid = type(val) is int and 2 <= val <= 4
            else:
                valid = isinstance(val,str) and bool(val.strip())
                if valid and key == 'color':
                    valid = re.fullmatch(r'#[0-9a-fA-F]{6}',val) is not None
                elif valid and section == 'fonts':
                    valid = all(c.isalnum() or c in ' ._-(),' for c in val) and '\n' not in val
                elif key == 'paper':
                    valid = valid and val in PAPERS
                elif key == 'orientation':
                    valid = valid and val in ('portrait','landscape')
            if not valid:
                raise ValueError(f'Invalid setting: {label}')
    p,c = result['page'],result['columns']
    w,h = PAPERS[p['paper']]
    if p['orientation']=='landscape': w,h=h,w
    if (w-p['margin_left_mm']-p['margin_right_mm']-(c['count']-1)*c['gap_mm'])/c['count'] < 20 or h-p['margin_top_mm']-p['margin_bottom_mm'] < 30:
        raise ValueError('Page has insufficient usable space')
    return result


def settings_candidate(path):
    try:
        raw = read_json(path)
    except FileNotFoundError:
        return None, False
    except (ValueError, UnicodeError) as exc:
        warn(f'{path}: {exc}')
        return None, True
    try:
        return validate_settings(raw), False
    except ValueError as exc:
        warn(f'{path}: {exc}')
        return None, True


def preserve(path):
    suffix = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    target = path.with_name(f'{path.stem}.corrupted.{suffix}.json')
    os.replace(path,target)
    warn(f'Damaged settings preserved: {target}')


def load_settings(home=HOME):
    primary = home/'latex-vocabulary-settings.json'
    backup = home/'latex-vocabulary-settings.backup.json'
    if unsafe(primary) or unsafe(backup):
        raise ValueError('Unsafe settings path')
    current, bad_primary = settings_candidate(primary)
    saved, bad_backup = settings_candidate(backup)
    if current is None:
        current = saved if saved is not None else copy.deepcopy(DEFAULTS)
        if bad_primary: preserve(primary)
        atomic_write(primary,json.dumps(current,ensure_ascii=False,indent=4,allow_nan=False)+'\n')
        print('[INFO] Settings restored from backup.' if saved is not None else '[INFO] Default settings initialized.')
    if bad_backup: preserve(backup)
    if saved != current:
        atomic_write(backup,json.dumps(current,ensure_ascii=False,indent=4,allow_nan=False)+'\n')
    return current


def unsafe(path):
    for p in (path,*path.parents):
        try: s=p.lstat()
        except FileNotFoundError: continue
        if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&0x400:
            return True
    return False


def natural_key(path):
    s=str(path).casefold()
    return ([ (1,int(x)) if x.isdigit() else (0,x) for x in re.split(r'(\d+)',s)],str(path))


def discover_files(inputs):
    found=[]; errors=[]; seen=set()
    for item in inputs:
        path=Path(os.path.abspath(item))
        if unsafe(path):
            errors.append(f'Unsafe input: {path}'); continue
        if path.is_dir():
            candidates=[]
            def onerror(exc): errors.append(str(exc))
            for root,dirs,files in os.walk(path,onerror=onerror,followlinks=False):
                dirs[:]=[d for d in dirs if not d.startswith('.') and d.casefold() not in EXCLUDED and not unsafe(Path(root)/d) and not getattr((Path(root)/d).stat(),'st_file_attributes',0)&2]
                candidates.extend(Path(root)/f for f in files if f.casefold().endswith('.vocabulary.json') and not f.startswith('.') and not unsafe(Path(root)/f))
            candidates.sort(key=lambda p:natural_key(p.relative_to(path)))
        elif path.is_file(): candidates=[path]
        else: errors.append(f'Input not found: {path}'); continue
        for p in candidates:
            key=os.path.normcase(str(p.resolve()))
            if key not in seen: found.append(p); seen.add(key)
    return found,errors


def stem(path):
    suffix='.vocabulary.json'
    return path.name[:-len(suffix)] if path.name.lower().endswith(suffix) else path.stem


def load_vocabulary(path):
    data=read_json(path)
    if not isinstance(data,dict) or data.get('filetype')!='vocabulary' or not isinstance(data.get('words'),list):
        raise ValueError('Expected filetype=vocabulary and a words array')
    for i,w in enumerate(data['words'],1):
        if not isinstance(w,dict) or not isinstance(w.get('word'),str) or not w['word'].strip() or not isinstance(w.get('meanings'),list):
            raise ValueError(f'Invalid word entry {i}')
        for key in ('phonetic_uk','phonetic_us'):
            if key in w and not isinstance(w[key],str): raise ValueError(f'Entry {i}: {key} must be a string')
        for m in w['meanings']:
            if not isinstance(m,dict) or any(not isinstance(m.get(k),str) for k in ('pos','meaning')):
                raise ValueError(f'Entry {i}: invalid meaning')
    return data['words']


def render_article(words,title):
    lines=[]
    if title: lines.append(r'\articletitle{'+escape_latex(title)+'}')
    if not words:
        return '\n'.join(lines) or r'\null'
    lines.append(r'\begin{multicols}{\VocabularyColumns}')
    for w in words:
        ipa=w.get('phonetic_uk','')
        if not ipa.strip(): ipa=w.get('phonetic_us','')
        if not ipa.strip(): ipa=''
        lines.append(r'\vocab{'+escape_latex(w['word'])+'}{'+escape_latex(ipa)+'}{%')
        for m in w['meanings']:
            lines.append(r'  \vocabmeaning{'+escape_latex(m['pos'])+'}{'+escape_latex(m['meaning'])+'}%')
        lines.append('}')
    lines.append(r'\end{multicols}')
    return '\n'.join(lines)


def render_document(articles,settings,template):
    values={f'{section}_{key}':str(settings[section][key]) for section,fields in DEFAULTS.items() for key in fields}
    values['page_page_number']='plain' if settings['page']['page_number'] else 'empty'
    for key in ('word_color','phonetic_color'): values[key]=values[key][1:]
    values['body']='\n\\clearpage\n\n'.join(articles)
    return re.sub(r'@@([a-z_]+)@@',lambda m:values[m[1]],template)


def output_file(path):
    return path.parent/'latex-vocabulary'/(stem(path)+'.vocabulary.tex')


def check_output(path):
    if path.suffix.lower()!='.tex': raise ValueError('Output must use .tex extension')
    if unsafe(path): raise ValueError(f'Unsafe output path: {path}')
    if path.resolve()==(HOME/'template.tex').resolve(): raise ValueError('Cannot overwrite template.tex')


def show_info():
    print(f'''ExportVocabulary\nConvert vocabulary JSON into standalone LaTeX documents.\nInputs: <stem>.vocabulary.json, vocabulary.json, files or directories.\nFormat specification: {HOME/'FORMAT.md'}\nModes: single, batch, merged (each article starts on a new page).\nDefault output: latex-vocabulary/<stem>.vocabulary.tex\nSettings: {HOME/'latex-vocabulary-settings.json'}\nTwo-column layout, centered titles, configurable fonts and colors.\nUK phonetics preferred; US fallback. No data correction or deduplication.\nSource files are read-only. Python 3.10+; no third-party packages.\nXeLaTeX is needed only for optional manual PDF compilation.\nRun --help for options. Usage: {HOME/'README.md'}''')


def main(argv=None):
    parser=argparse.ArgumentParser(description='Export vocabulary JSON to LaTeX.')
    parser.add_argument('inputs',nargs='*',help='Vocabulary files or directories')
    parser.add_argument('--merge',action='store_true',help='Merge into one document')
    parser.add_argument('-o','--output',type=Path,help='Output path for a single resulting document')
    parser.add_argument('--title',help='Override title for one input article')
    parser.add_argument('--overwrite',action='store_true',help='Replace existing output files')
    parser.add_argument('--info',action='store_true',help='Show program and input format information')
    args=parser.parse_args(argv)
    if args.info: show_info(); return 0
    if not args.inputs: parser.error('at least one input is required')
    try:
        files,errors=discover_files(args.inputs)
        for e in errors: print(f'[ERROR] {e}',file=sys.stderr)
        if not files: raise ValueError('No vocabulary files found')
        if args.title is not None and len(files)!=1: parser.error('--title requires one article')
        if args.output and not args.merge and len(files)!=1: parser.error('--output requires one resulting document')
        if args.output and args.output.suffix.lower()!='.tex': parser.error('--output must end in .tex')
        if args.merge and errors: return 1
        settings=load_settings()
        template=(HOME/'template.tex').read_text(encoding='utf-8')
        ok=skip=0; failed=len(errors)
        def save(target,articles):
            nonlocal ok,skip
            check_output(target)
            if any(target.resolve() == p.resolve() for p in files):
                raise ValueError('Cannot overwrite an input file')
            try: atomic_write(target,render_document(articles,settings,template),args.overwrite)
            except FileExistsError:
                print(f'[SKIP] {target} already exists'); skip+=1; return
            print(f'[OK] {target}'); ok+=1
        def article(p): return render_article(load_vocabulary(p),args.title if args.title is not None else stem(p))
        if args.merge:
            articles=[]
            for p in files:
                try: articles.append(article(p))
                except (OSError,ValueError,UnicodeError) as e: raise ValueError(f'{p}: {e}') from e
            root=Path(args.inputs[0])
            target=args.output or (root/'latex-vocabulary'/(root.resolve().name+'.vocabulary.tex') if len(args.inputs)==1 and root.is_dir() else output_file(files[0]) if len(files)==1 else Path.cwd()/'latex-vocabulary'/'Vocabulary.tex')
            save(target,articles)
        else:
            for p in files:
                try: save(args.output or output_file(p),[article(p)])
                except (OSError,ValueError,UnicodeError) as e:
                    print(f'[ERROR] {p}: {e}',file=sys.stderr); failed+=1
        print(f'Succeeded: {ok}; Skipped: {skip}; Failed: {failed}')
        return int(failed>0)
    except (OSError,ValueError,UnicodeError) as exc:
        print(f'[ERROR] {exc}',file=sys.stderr); return 1


if __name__=='__main__':
    sys.exit(main())
