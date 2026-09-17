from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, urlencode
import copy, json, re, sys
from jinja2 import Environment, DictLoader, ChoiceLoader, FileSystemLoader, StrictUndefined, select_autoescape
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from services.saved_vacancy_labels import UI, ERROR_MESSAGES
from services.saved_vacancy_snapshot import build_snapshot
from services.vacancy_presenter import present_vacancy
from tests.test_job001_service import payload
import tempfile
OUT=Path(tempfile.mkdtemp(prefix='job001-ui-'))
def url_for(endpoint,**values):
    if endpoint=='static':return '/static/'+values['filename']
    names={'vacancies':'/vacancies','saved_vacancies.index':'/saved-vacancies',
           'saved_vacancies.save':'/saved-vacancies/save','saved_vacancies.import_legacy':'/saved-vacancies/import-legacy',
           'saved_vacancies.detail':'/saved-vacancies/'+values.get('saved_id','00000000-0000-0000-0000-000000000001')}
    return names.get(endpoint,'/'+endpoint.replace('.','/'))
env=Environment(loader=FileSystemLoader(R/'templates'),undefined=StrictUndefined,autoescape=select_autoescape(['html']))
env.globals.update(url_for=url_for,csrf_token=lambda:'test-only-csrf',csp_nonce='test-only-nonce',
                   current_user=SimpleNamespace(id='test-owner'),search_admin_access=True,
                   request=SimpleNamespace(path='/saved-vacancies',full_path='/saved-vacancies'))
env.filters['saved_time']=lambda value:'17.09.2026 12:00 UTC'
snap=build_snapshot(payload(title='Python Backend Developer',description='Maintain existing services and document changes.\nWrite API integration tests and SQL queries.'))
record={'id':'00000000-0000-0000-0000-000000000001','snapshot':snap,'card':present_vacancy(snap),
        'created_at':1,'updated_at':1,'revision':2,'note':'Ask about the team, onboarding and remote-work schedule.',
        'old_snapshot':True,'sources':[{'source':'hh','url':'https://hh.ru/vacancy/123','state':'not_in_cache','observed_at':None}]}
results={'items':[record,copy.deepcopy(record)],'query':'','page':1,'pages':2,'total':25}
htmls={
 'library':env.get_template('saved_vacancies/index.html').render(ui=UI,results=results),
 'empty':env.get_template('saved_vacancies/index.html').render(ui=UI,results={**results,'items':[],'pages':1,'total':0}),
 'detail':env.get_template('saved_vacancies/detail.html').render(ui=UI,record=record,error=None,draft_note=record['note'],note_limit=4000),
 'conflict':env.get_template('saved_vacancies/conflict.html').render(ui=UI,record=record,error=ERROR_MESSAGES['stale_write'],draft_note='Unsaved personal question.\n'+'long-note-without-spaces-'*80),
 'error':env.get_template('saved_vacancies/error.html').render(ui=UI,error=ERROR_MESSAGES['stale_source'])}
search=(R/'templates/vacancies_unified.html').read_text()
form=re.search(r'<div class="vacancy-actions">.*?<p class="job001-save-status".*?</p>\s*</div>',search,re.S).group(0)
search_tpl="{% extends 'base.html' %}{% block head_extra %}<link rel='stylesheet' href='/static/saved_vacancies.css'>{% endblock %}{% block content %}<main class='section'><div class='container'><article class='unified-vacancy-card'><h1>Python Backend Developer</h1>"+form+"</article></div></main><script src='/static/saved_vacancies.js'></script>{% endblock %}"
htmls['search_save']=env.from_string(search_tpl).render(vacancy={'saved_control':{'saved_id':None,'reference':'test-only-reference'},'url':'https://hh.ru/vacancy/123'})
for name,data in htmls.items():(OUT/(name+'.html')).write_text(data)

def inline_local_assets(html):
    def css(match):
        name=match.group(1)
        file=R/'static'/name
        return '<style>'+file.read_text()+'</style>' if file.is_file() else ''
    html=re.sub(r'<link[^>]*href=["\x27]/static/([^?"\x27]+)(?:\?[^"\x27]*)?["\x27][^>]*>',css,html)
    html=re.sub(r'<link[^>]*>', '', html)
    html=re.sub(r'<script[^>]*src=[^>]*>.*?</script>', '', html, flags=re.S)
    return html.replace("<head>","<head><base href=\"https://offline.example.test/\">")
measurements=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
    page=browser.new_page();page.set_default_timeout(5000)
    page.route('**/*',lambda route:route.abort())
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':900})
        for name,data in htmls.items():
            page.set_content(inline_local_assets(data),wait_until='load')
            sizes=page.evaluate('({width:innerWidth,document:document.documentElement.scrollWidth,main:document.querySelector("main").scrollWidth})')
            overflow=page.evaluate('Array.from(document.querySelectorAll("main *")).filter(e=>{let r=e.getBoundingClientRect();return r.width>0 && (r.right>innerWidth+1||r.left< -1)}).map(e=>({tag:e.tagName,cls:e.className,text:e.textContent.slice(0,60)})).slice(0,10)')
            measurements.append({'page':name,'width':width,**sizes,'main_overflow':overflow})
            if (width,name) in [(390,'detail'),(1440,'library'),(390,'search_save')]:page.screenshot(path=str(OUT/f'{name}_{width}.png'),full_page=True)
    (OUT/'layouts_only.json').write_text(json.dumps(measurements,indent=2))
    print('Layout stage complete',flush=True)
    # Isolated DOM/JS tests, supplied location/fetch/storage bindings. No actual browser network/storage authority claim.
    js=(R/'static/saved_vacancies.js').read_text()
    setup="""window.testCalls=[];window.testStore={value:'["known","unresolved"]',getItem(){return this.value},setItem(key,value){this.value=value}};
    window.testPost=async function(url,options){testCalls.push(url);return {ok:true,json:async()=>url.endsWith('/save')?{ok:true,url:'/saved-vacancies/00000000-0000-0000-0000-000000000001'}:{ok:true,saved_keys:['known'],saved_count:1,unresolved_count:1}}};"""
    def load_js():
        page.evaluate(setup+"void 0;")
        page.evaluate("(function(location,fetch,localStorage){"+js+"})({origin:'https://offline.example.test'},window.testPost,window.testStore)")
    page.set_content(inline_local_assets(htmls['search_save']),wait_until='load');load_js()
    print('Before save click',flush=True)
    page.locator('[data-server-save] button').click()
    print('After save click',page.evaluate('testCalls'),page.locator('[data-save-status]').inner_text(),flush=True)
    page.wait_for_selector('a.is-saved')
    assert page.locator('a.is-saved').get_attribute('href')=='/saved-vacancies/'+record['id']
    assert len(page.evaluate('testCalls'))==1
    page.set_content(inline_local_assets(htmls['library']),wait_until='load');load_js()
    assert page.locator('[data-legacy-panel]').is_visible()
    print('Before legacy click',flush=True)
    page.locator('[data-legacy-form] button').click()
    assert page.evaluate('testCalls')==[]
    page.locator('[data-legacy-form] input[type=checkbox]').check()
    print('Before legacy click',flush=True)
    page.locator('[data-legacy-form] button').click()
    page.wait_for_function('testStore.value===JSON.stringify(["unresolved"])')
    assert len(page.evaluate('testCalls'))==1
    browser.close()
(OUT/'layout_results.json').write_text(json.dumps({'checks':measurements,'isolated_dom_js':'PASS','network_and_storage':'test bindings only','external_fonts':'blocked','flask_http':'NOT RUN'},indent=2))
print('layouts',len(measurements),'global overflow',[(r['page'],r['width'],r['document']) for r in measurements if r['document']>r['width']+1])
print('main overflow',[(r['page'],r['width'],r['main_overflow']) for r in measurements if r['main_overflow']])
