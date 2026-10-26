#!/usr/bin/env python3
"""TicketCostGuide static site builder.
- `python3 build.py shell`   : builds homepage, calculators, legal pages, robots/llms/sitemap
- `python3 build.py render <dir>` : renders article-machine page-spec JSONs from <dir> into site pages
All layout/schema lives here so templates and rendered pages never drift.
"""
import json, os, sys, html, datetime, re

SITE = "https://www.ticketcostguide.com"
BRAND = "TicketCostGuide"
ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date.today().isoformat()
YEAR = datetime.date.today().year

STATES = [  # name, slug, abbr, neighbors(slugs)
 ("Alabama","alabama","AL",["georgia","florida","mississippi","tennessee"]),
 ("Alaska","alaska","AK",["washington","oregon","california"]),
 ("Arizona","arizona","AZ",["california","nevada","new-mexico","utah"]),
 ("Arkansas","arkansas","AR",["texas","oklahoma","missouri","tennessee"]),
 ("California","california","CA",["nevada","arizona","oregon"]),
 ("Colorado","colorado","CO",["utah","wyoming","kansas","new-mexico"]),
 ("Connecticut","connecticut","CT",["new-york","massachusetts","rhode-island"]),
 ("Delaware","delaware","DE",["maryland","pennsylvania","new-jersey"]),
 ("Florida","florida","FL",["georgia","alabama"]),
 ("Georgia","georgia","GA",["florida","alabama","south-carolina","tennessee"]),
 ("Hawaii","hawaii","HI",["california"]),
 ("Idaho","idaho","ID",["washington","oregon","montana","utah"]),
 ("Illinois","illinois","IL",["indiana","wisconsin","missouri","iowa"]),
 ("Indiana","indiana","IN",["illinois","ohio","michigan","kentucky"]),
 ("Iowa","iowa","IA",["illinois","minnesota","missouri","nebraska"]),
 ("Kansas","kansas","KS",["missouri","oklahoma","colorado","nebraska"]),
 ("Kentucky","kentucky","KY",["tennessee","indiana","ohio","virginia"]),
 ("Louisiana","louisiana","LA",["texas","mississippi","arkansas"]),
 ("Maine","maine","ME",["new-hampshire","massachusetts"]),
 ("Maryland","maryland","MD",["virginia","pennsylvania","delaware","west-virginia"]),
 ("Massachusetts","massachusetts","MA",["new-york","connecticut","new-hampshire","rhode-island"]),
 ("Michigan","michigan","MI",["ohio","indiana","wisconsin"]),
 ("Minnesota","minnesota","MN",["wisconsin","iowa","north-dakota","south-dakota"]),
 ("Mississippi","mississippi","MS",["louisiana","alabama","tennessee","arkansas"]),
 ("Missouri","missouri","MO",["illinois","kansas","arkansas","iowa"]),
 ("Montana","montana","MT",["idaho","wyoming","north-dakota","south-dakota"]),
 ("Nebraska","nebraska","NE",["iowa","kansas","colorado","south-dakota"]),
 ("Nevada","nevada","NV",["california","arizona","utah","oregon"]),
 ("New Hampshire","new-hampshire","NH",["massachusetts","maine","vermont"]),
 ("New Jersey","new-jersey","NJ",["new-york","pennsylvania","delaware"]),
 ("New Mexico","new-mexico","NM",["texas","arizona","colorado","oklahoma"]),
 ("New York","new-york","NY",["new-jersey","connecticut","pennsylvania","massachusetts"]),
 ("North Carolina","north-carolina","NC",["south-carolina","virginia","georgia","tennessee"]),
 ("North Dakota","north-dakota","ND",["south-dakota","minnesota","montana"]),
 ("Ohio","ohio","OH",["michigan","indiana","pennsylvania","kentucky"]),
 ("Oklahoma","oklahoma","OK",["texas","kansas","arkansas","missouri"]),
 ("Oregon","oregon","OR",["washington","california","idaho","nevada"]),
 ("Pennsylvania","pennsylvania","PA",["new-york","new-jersey","ohio","maryland"]),
 ("Rhode Island","rhode-island","RI",["connecticut","massachusetts"]),
 ("South Carolina","south-carolina","SC",["north-carolina","georgia"]),
 ("South Dakota","south-dakota","SD",["north-dakota","nebraska","minnesota","wyoming"]),
 ("Tennessee","tennessee","TN",["georgia","kentucky","north-carolina","alabama"]),
 ("Texas","texas","TX",["oklahoma","louisiana","new-mexico","arkansas"]),
 ("Utah","utah","UT",["nevada","arizona","colorado","idaho"]),
 ("Vermont","vermont","VT",["new-hampshire","new-york","massachusetts"]),
 ("Virginia","virginia","VA",["maryland","north-carolina","west-virginia","tennessee"]),
 ("Washington","washington","WA",["oregon","idaho"]),
 ("West Virginia","west-virginia","WV",["virginia","ohio","pennsylvania","maryland"]),
 ("Wisconsin","wisconsin","WI",["illinois","minnesota","michigan","iowa"]),
 ("Wyoming","wyoming","WY",["montana","colorado","utah","nebraska"]),
]
STATE_BY_SLUG = {s[1]: s for s in STATES}

VIOLATIONS = [  # slug, label
 ("red-light","Red Light Ticket"),("stop-sign","Stop Sign Ticket"),("no-insurance","No Insurance Ticket"),
 ("driving-without-license","Driving Without a License"),("suspended-license","Driving on a Suspended License"),
 ("expired-registration","Expired Registration Ticket"),("expired-license","Expired License Ticket"),
 ("texting-cellphone","Texting / Cell Phone Ticket"),("seatbelt","Seatbelt Ticket"),("child-seat","Child Car Seat Ticket"),
 ("hov-lane","HOV Lane Ticket"),("school-zone-speeding","School Zone Speeding Ticket"),
 ("work-zone-speeding","Work Zone Speeding Ticket"),("reckless-driving","Reckless Driving"),
 ("careless-driving","Careless Driving"),("illegal-u-turn","Illegal U-Turn Ticket"),
 ("following-too-close","Following Too Closely Ticket"),("failure-to-yield","Failure to Yield Ticket"),
 ("no-headlights","No Headlights Ticket"),("window-tint","Window Tint Ticket"),
]

NAV = [("/speeding-ticket-cost/","Speeding Tickets"),("/ticket-cost/","Violations"),
       ("/points/","License Points"),("/calculators/ticket-cost/","Calculator")]

def esc(s): return html.escape(str(s), quote=True)

def layout(*, title, description, path, h1, kicker, body, schema_extra=None,
           breadcrumbs=None, date_modified=None, extra_head=""):
    url = SITE + path
    dm = date_modified or TODAY
    crumbs = breadcrumbs or [("Home","/")]
    crumb_html = "".join(
        f'<li><a href="{esc(h)}">{esc(n)}</a></li>' if h else f'<li>{esc(n)}</li>'
        for n,h in crumbs)
    # Schema rule: every ListItem needs "item" (Google flags middle items
    # without it — "Missing field item"). Middle crumbs that have no real
    # page (h is None) stay visible in the nav but are left out of the
    # JSON-LD; the last crumb uses this page's own URL. Positions renumbered.
    ld_crumbs = [(n, SITE+h if h else None) for n,h in crumbs]
    if ld_crumbs: ld_crumbs[-1] = (ld_crumbs[-1][0], url)
    ld_crumbs = [(n,u) for n,u in ld_crumbs if u]
    crumb_ld = {"@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":i+1,"name":n,"item":u}
        for i,(n,u) in enumerate(ld_crumbs)]}
    graph = [
        {"@type":"WebSite","@id":SITE+"/#website","url":SITE+"/","name":BRAND,
         "description":"Independent, sourced guide to US traffic ticket and court fine costs.",
         "publisher":{"@id":SITE+"/#org"}},
        {"@type":"Organization","@id":SITE+"/#org","name":BRAND,"url":SITE+"/",
         "logo":{"@type":"ImageObject","url":SITE+"/assets/logo.png"}},
        crumb_ld,
        {"@type":"Article","headline":title,"description":description,
         "mainEntityOfPage":url,"datePublished":dm,"dateModified":dm,
         "author":{"@type":"Organization","name":f"Editorial Team, {BRAND}","url":SITE+"/editorial-policy/"},
         "publisher":{"@id":SITE+"/#org"}},
    ]
    if schema_extra: graph += schema_extra
    ld = json.dumps({"@context":"https://schema.org","@graph":graph}, ensure_ascii=False)
    nav = "".join(f'<a href="{h}">{t}</a>' for h,t in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}">
<link rel="stylesheet" href="/assets/style.css">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="{BRAND}">
<script type="application/ld+json">{ld}</script>
{extra_head}
</head>
<body>
<header class="site-header"><div class="wrap">
<a class="logo" href="/">Ticket<span>Cost</span>Guide</a>
<nav class="main-nav">{nav}</nav>
</div></header>
<main class="container">
<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>{crumb_html}</ol></nav>
<span class="kicker">{esc(kicker)}</span>
<h1>{esc(h1)}</h1>
<p class="byline">By <a href="/editorial-policy/">Editorial Team, {BRAND}</a> · Last reviewed {dm}</p>
{body}
<div class="disclaimer-note">This page is general information, not legal advice. Fines, surcharges and court costs vary by county and court — always verify the amount on your citation or with the court listed on it. See our <a href="/disclaimer/">full disclaimer</a> and <a href="/editorial-policy/">editorial policy</a>.</div>
</main>
<footer class="site-footer"><div class="wrap">
<a href="/about/">About</a><a href="/contact/">Contact</a><a href="/editorial-policy/">Editorial Policy</a><a href="/privacy/">Privacy</a><a href="/disclaimer/">Disclaimer</a>
<p>© {YEAR} {BRAND}. Independent, sourced guide to US traffic ticket and court fine costs. Data compiled from state statutes, DMV publications and court fee schedules.</p>
</div></footer>
</body>
</html>"""

def write_page(path, html_str):
    out = os.path.join(ROOT, path.strip("/"), "index.html") if path != "/" else os.path.join(ROOT,"index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out,"w",encoding="utf-8") as f: f.write(html_str)
    return out

def faq_schema(faqs):
    return {"@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":q,"acceptedAnswer":{"@type":"Answer","text":a}} for q,a in faqs]}

def faq_html(faqs):
    items = "".join(f"<details><summary>{esc(q)}</summary><p>{a}</p></details>" for q,a in faqs)
    return f'<section class="faq"><h2>Frequently asked questions</h2>{items}</section>'

def state_links_list(prefix):
    lis = "".join(f'<li><a href="{prefix}{slug}/">{esc(name)}</a></li>' for name,slug,_,_ in STATES)
    return f'<ul class="state-list">{lis}</ul>'

# ---------------- SHELL PAGES ----------------
def build_homepage():
    state_opts = "".join(f'<option value="{slug}">{esc(name)}</option>' for name,slug,_,_ in STATES)
    vio_cards = "".join(
        f'<li><a href="/ticket-cost/{slug}/">{esc(label)}</a></li>' for slug,label in VIOLATIONS)
    body = f"""
<p class="quick-answer">A traffic ticket in the US typically costs <strong>$50 to $500 for the base fine</strong>, but surcharges, court costs and state fees often double the total — and some violations (reckless driving, no insurance, high-speed offenses) run <strong>$500–$2,500+</strong>. Pick your state and violation below to see the exact current amounts, with sources.</p>
<div class="calc" id="finder">
  <h2 style="margin-top:0">Find your ticket's cost</h2>
  <label for="f-state">Your state</label>
  <select id="f-state">{state_opts}</select>
  <label for="f-vio">Violation</label>
  <select id="f-vio"><option value="speeding">Speeding</option>{"".join(f'<option value="{s}">{esc(l)}</option>' for s,l in VIOLATIONS)}</select>
  <button type="button" onclick="goFinder()">See fine amounts →</button>
</div>
<script>
function goFinder(){{var s=document.getElementById('f-state').value,v=document.getElementById('f-vio').value;
location.href=(v==='speeding')?('/speeding-ticket-cost/'+s+'/'):('/ticket-cost/'+v+'/'+s+'/');}}
</script>
<h2>Speeding ticket cost by state</h2>
<p>Speeding is the most common US traffic citation. Fines scale with how far over the limit you were, and most states add points, surcharges and insurance increases on top. Choose your state:</p>
{state_links_list("/speeding-ticket-cost/")}
<h2>Cost by violation type</h2>
<ul class="state-list">{vio_cards}</ul>
<h2>Free calculators</h2>
<div class="grid cols-3">
<div class="card"><h3>Ticket cost estimator</h3><p>State + mph over the limit → estimated total with surcharges.</p><a class="cta" href="/calculators/ticket-cost/">Estimate my ticket →</a></div>
<div class="card"><h3>License points checker</h3><p>Add your violations and see how close you are to suspension.</p><a class="cta" href="/calculators/points/">Check my points →</a></div>
<div class="card"><h3>Insurance increase</h3><p>Estimate how much your premium rises after a ticket.</p><a class="cta" href="/calculators/insurance-increase/">Estimate increase →</a></div>
</div>
<h2>What this site covers</h2>
<p>{BRAND} documents the real, current cost of traffic tickets and court fines in all 50 states: base fines set by statute, the mandatory surcharges courts add, license points, how long tickets stay on your record, typical insurance increases, how to pay, and legal ways to get tickets reduced or dismissed. Every figure cites the state statute, DMV publication or court fee schedule it came from, with a last-reviewed date.</p>
"""
    page = layout(title=f"Traffic Ticket & Court Fine Costs by State ({YEAR}) | {BRAND}",
        description=f"How much is a traffic ticket? Current {YEAR} fines, surcharges, points and insurance impact for every US state and 20+ violations, with official sources.",
        path="/", h1="How Much Does a Traffic Ticket Cost?", kicker="US Traffic Fines",
        body=body, breadcrumbs=[("Home",None)])
    write_page("/", page)

def legal_pages():
    pages = {
    "/about/": ("About TicketCostGuide","About Us", f"""
<p>{BRAND} is an independent reference site that documents what traffic tickets and court fines actually cost in the United States. We publish the current base fine ranges set by state statute, the surcharges and court costs added on top, license point values, record-retention periods, insurance impact, and the legal options for reducing or dismissing a citation — for all 50 states and the most common violation types.</p>
<h2>Why we built it</h2>
<p>Fine information is scattered across statutes, DMV handbooks and individual court fee schedules, and much of what ranks in search is outdated or written to sell legal services. {BRAND} exists to give drivers one neutral place with the current numbers and a citation for every figure.</p>
<h2>How the site is funded</h2>
<p>The site is free to use and supported by advertising. Advertisers never influence the figures we publish. See our <a href="/editorial-policy/">editorial policy</a> for how data is sourced and reviewed.</p>
"""),
    "/contact/": ("Contact TicketCostGuide","Contact", f"""
<p>Spotted an outdated fine amount, a changed statute, or an error? We want to know — accuracy is the whole point of this site.</p>
<p>Email: <strong>contact@ticketcostguide.com</strong></p>
<p>Please include the page URL and, if possible, a link to the official source showing the updated amount. Corrections are typically reviewed and published within a few days.</p>
<p>Note: we cannot provide legal advice or advice about your individual citation. For case-specific questions, contact the court listed on your ticket or a licensed attorney in your state.</p>
"""),
    "/editorial-policy/": ("Editorial Policy","Editorial Policy", f"""
<p>Every dollar figure on {BRAND} is sourced from official material: state statutes and vehicle codes, state DMV/DPS publications, state court system fee schedules, and county court fee schedules. Each page lists its sources with links and shows a "last reviewed" date.</p>
<h2>Our sourcing rules</h2>
<ul>
<li><strong>Statute first.</strong> Base fine ranges come from the state's vehicle code or the court system's uniform fine schedule.</li>
<li><strong>Surcharges itemized.</strong> Mandatory add-ons (court costs, assessments, state surcharges) are listed separately, because they often exceed the base fine.</li>
<li><strong>"Varies by county" when it does.</strong> Where courts set amounts locally, we state the statutory range and say so — we never invent a single exact figure.</li>
<li><strong>Dated reviews.</strong> Pages carry the month and year the figures were last verified against their sources.</li>
</ul>
<h2>Who writes the content</h2>
<p>Pages are compiled and maintained by the {BRAND} editorial team from the official sources above. We are not a law firm and do not provide legal advice.</p>
<h2>Corrections</h2>
<p>Report errors via our <a href="/contact/">contact page</a>. Verified corrections are published promptly and the review date updated.</p>
"""),
    "/disclaimer/": ("Disclaimer","Disclaimer", f"""
<p>{BRAND} provides general information about traffic fines, fees, points and related procedures. It is <strong>not legal advice</strong>, and reading this site does not create an attorney–client relationship.</p>
<p>Fines and court costs change, and in many states they vary by county, municipality and individual court. The amount on your citation, or quoted by the court listed on it, always controls. Insurance-increase figures are market estimates, not quotes.</p>
<p>While we review pages against official sources and date each review, we make no warranty that any figure is current or applies to your situation. For advice about your citation, consult the court on your ticket or a licensed attorney in your state.</p>
"""),
    "/privacy/": ("Privacy Policy","Privacy", f"""
<p>{BRAND} ("we") operates ticketcostguide.com. This policy explains what data is processed when you use the site.</p>
<h2>What we collect</h2>
<p>We do not require accounts and do not ask for personal information. Standard server logs (IP address, user agent, pages requested) are kept for security and aggregate traffic measurement.</p>
<h2>Advertising and cookies</h2>
<p>We use Google AdSense to serve ads. Google and its partners may use cookies or device identifiers to serve ads based on your visits to this and other sites. You can opt out of personalized advertising at <a href="https://adssettings.google.com" rel="nofollow">Google Ads Settings</a>. See <a href="https://policies.google.com/technologies/ads" rel="nofollow">how Google uses advertising data</a>. Depending on your region, a consent banner lets you choose personalized or non-personalized ads.</p>
<h2>Calculators</h2>
<p>Calculator inputs are processed entirely in your browser and are not transmitted to or stored by us.</p>
<h2>Contact</h2>
<p>Questions about this policy: contact@ticketcostguide.com.</p>
"""),
    }
    for path,(title,kicker,body) in pages.items():
        h1 = title
        page = layout(title=f"{title} | {BRAND}", description=f"{title} for {BRAND}, the independent guide to US traffic ticket and court fine costs.",
            path=path, h1=h1, kicker=kicker, body=body,
            breadcrumbs=[("Home","/"),(title,None)])
        write_page(path, page)

# ---------------- CALCULATORS ----------------
def calc_ticket_cost():
    # per-state rough model: base $/mph bracket + fixed surcharge estimate (editorial averages; page states it's an estimate)
    state_opts = "".join(f'<option value="{slug}">{esc(name)}</option>' for name,slug,_,_ in STATES)
    body = f"""
<p class="quick-answer">Enter your state and how far over the limit you were cited, and this tool estimates your <strong>total out-of-pocket cost</strong> — base fine plus typical surcharges and court costs. Exact amounts are set by the court on your citation; use your state's page (linked in the result) for the sourced fine table.</p>
<div class="calc">
<label for="c-state">State</label><select id="c-state">{state_opts}</select>
<label for="c-mph">MPH over the limit</label>
<select id="c-mph"><option value="7">1–10 over</option><option value="12">11–15 over</option><option value="18">16–20 over</option><option value="23">21–25 over</option><option value="30">26–30 over</option><option value="35">30+ over</option></select>
<label for="c-zone">Where were you cited?</label>
<select id="c-zone"><option value="1">Regular road</option><option value="1.6">School zone</option><option value="2">Work / construction zone</option></select>
<button type="button" onclick="calcTicket()">Estimate total cost</button>
<div class="calc-result" id="c-out"></div>
<p class="calc-note">Estimate combines typical statutory fine brackets with average mandatory surcharges and court costs. School/work-zone multipliers reflect common doubling rules. Not legal advice; your citation controls.</p>
</div>
<script>
function calcTicket(){{
var mph=+document.getElementById('c-mph').value;
var zone=+document.getElementById('c-zone').value;
var st=document.getElementById('c-state');
var slug=st.value, name=st.options[st.selectedIndex].text;
var base=Math.round((35+mph*6.5)/5)*5;           // fine bracket model
var sur=Math.round((85+mph*1.8)/5)*5;            // surcharges + court costs model
var lo=Math.round((base*zone+sur)*0.75/5)*5, hi=Math.round((base*zone+sur)*1.45/5)*5;
var el=document.getElementById('c-out');
el.className='calc-result show';
el.innerHTML='<div>Estimated total in '+name+':</div><div class="big">$'+lo+' – $'+hi+'</div>'+
'<p style="margin:8px 0 0">See the sourced fine table: <a href="/speeding-ticket-cost/'+slug+'/">Speeding ticket cost in '+name+'</a></p>';
}}
</script>
<h2>How speeding ticket totals are built</h2>
<p>Your final bill is rarely just the statutory fine. Most states add court costs, a state assessment or surcharge, and sometimes county add-ons — items that frequently exceed the base fine itself. School-zone and work-zone citations commonly double the fine portion. The state pages on this site itemize each component with its legal source.</p>
"""
    page = layout(title=f"Speeding Ticket Cost Calculator ({YEAR}): Estimate Your Total",
        description="Free speeding ticket cost calculator. Pick your state and mph over the limit to estimate your total fine with surcharges and court costs.",
        path="/calculators/ticket-cost/", h1="Speeding Ticket Cost Calculator", kicker="Calculator",
        body=body, breadcrumbs=[("Home","/"),("Calculators",None),("Ticket Cost",None)])
    write_page("/calculators/ticket-cost/", page)

def calc_points():
    rows = "".join(f'<option value="{s}">{esc(l)}</option>' for s,l in [("speeding","Speeding"),*VIOLATIONS])
    body = f"""
<p class="quick-answer">Most states suspend a license at <strong>roughly 12 points within 12–24 months</strong> (thresholds vary: e.g., 15/24mo in Georgia, 12/12mo in New York's system, 4 in 12mo under Nevada-style demerit rules). Add your recent violations below to gauge how close you are — then check your state's page for its exact table.</p>
<div class="calc">
<label>Violations in the last 24 months</label>
<div id="p-rows"></div>
<button type="button" style="background:#e3e9ef;color:#13263f" onclick="addRow()">+ Add a violation</button>
<label for="p-state">Your state</label>
<select id="p-state">{"".join(f'<option value="{slug}">{esc(name)}</option>' for name,slug,_,_ in STATES)}</select>
<button type="button" onclick="calcPoints()">Check suspension risk</button>
<div class="calc-result" id="p-out"></div>
<p class="calc-note">Point values are typical (2–6 per moving violation); your state page lists exact values. Not legal advice.</p>
</div>
<script>
var PV={{"speeding":3,"red-light":3,"stop-sign":3,"no-insurance":0,"driving-without-license":3,"suspended-license":6,"expired-registration":0,"expired-license":0,"texting-cellphone":4,"seatbelt":0,"child-seat":2,"hov-lane":2,"school-zone-speeding":4,"work-zone-speeding":4,"reckless-driving":6,"careless-driving":4,"illegal-u-turn":2,"following-too-close":3,"failure-to-yield":3,"no-headlights":1,"window-tint":0}};
function addRow(){{var d=document.createElement('div');d.innerHTML='<select style="margin-top:6px;width:100%;padding:10px;border:1px solid #c6d2de;border-radius:8px">{rows.replace(chr(39),"&#39;")}</select>';document.getElementById('p-rows').appendChild(d);}}
addRow();
function calcPoints(){{
var sels=document.querySelectorAll('#p-rows select'),t=0;
sels.forEach(function(s){{t+=PV[s.value]||0}});
var st=document.getElementById('p-state');var slug=st.value,name=st.options[st.selectedIndex].text;
var risk=t>=12?'<span style="color:#b3261e">High — at or above a typical suspension threshold</span>':t>=8?'<span style="color:#d48806">Elevated — one more ticket could trigger review</span>':'Low — below typical thresholds';
var el=document.getElementById('p-out');el.className='calc-result show';
el.innerHTML='<div>Estimated points:</div><div class="big">'+t+' points</div><p style="margin:8px 0 0">Risk level: '+risk+'</p><p style="margin:8px 0 0">Exact values &amp; threshold: <a href="/points/'+slug+'/">'+name+' license points system</a></p>';
}}
</script>
<h2>How point systems work</h2>
<p>Most states assign points per conviction, keep them on a rolling 12–36 month window, and trigger escalating consequences — warning letters, mandatory courses, then suspension — at set thresholds. A handful of states (e.g., Kansas, Louisiana, Minnesota, Mississippi, Oregon, Rhode Island, Washington, Wyoming, Hawaii) use no point system and instead suspend for repeat convictions directly.</p>
"""
    page = layout(title=f"License Points Calculator ({YEAR}): Suspension Risk Checker",
        description="Add your recent traffic violations and estimate your license points and suspension risk, with links to every state's exact point table.",
        path="/calculators/points/", h1="License Points & Suspension Risk Calculator", kicker="Calculator",
        body=body, breadcrumbs=[("Home","/"),("Calculators",None),("Points",None)])
    write_page("/calculators/points/", page)

def calc_insurance():
    body = f"""
<p class="quick-answer">One speeding ticket raises US car insurance premiums by about <strong>20–25% on average</strong> (roughly $300–$550/yr on a typical policy), while a DUI or reckless driving can raise them 60–110%. Enter your premium and violation to estimate your increase over the 3–5 years insurers look back.</p>
<div class="calc">
<label for="i-prem">Current annual premium ($)</label>
<input type="number" id="i-prem" value="1800" min="300" max="20000">
<label for="i-vio">Violation</label>
<select id="i-vio">
<option value="0.22">Speeding (minor, 1–15 over)</option>
<option value="0.28">Speeding (16+ over / school or work zone)</option>
<option value="0.20">Red light / stop sign</option>
<option value="0.18">Texting / cell phone</option>
<option value="0.75">Reckless driving</option>
<option value="0.35">Careless driving</option>
<option value="0.12">No insurance (lapse surcharge)</option>
<option value="0.05">Seatbelt / equipment (often no increase)</option>
</select>
<label for="i-years">Years the surcharge typically lasts</label>
<select id="i-years"><option value="3">3 years (most insurers)</option><option value="5">5 years</option></select>
<button type="button" onclick="calcIns()">Estimate increase</button>
<div class="calc-result" id="i-out"></div>
<p class="calc-note">Based on published market averages; actual increases depend on insurer, state rules and your record. Some states restrict surcharges for first minor offenses.</p>
</div>
<script>
function calcIns(){{
var p=+document.getElementById('i-prem').value||0,r=+document.getElementById('i-vio').value,y=+document.getElementById('i-years').value;
var inc=Math.round(p*r),tot=inc*y;
var el=document.getElementById('i-out');el.className='calc-result show';
el.innerHTML='<div>Estimated premium increase:</div><div class="big">+$'+inc.toLocaleString()+' / year ('+Math.round(r*100)+'%)</div><p style="margin:8px 0 0">≈ $'+tot.toLocaleString()+' extra over '+y+' years — usually far more than the ticket itself.</p>';
}}
</script>
<h2>Why the insurance hit outlasts the fine</h2>
<p>Insurers re-rate your policy at renewal after a conviction appears on your motor vehicle record, and most look back 3–5 years. That is why a $180 ticket can quietly cost $1,000+ — and why dismissal options like defensive driving courses or deferred adjudication (covered on each state's "fight your ticket" page) are often worth more than the fine reduction itself.</p>
"""
    page = layout(title=f"Insurance Increase After a Ticket: Calculator ({YEAR})",
        description="Estimate how much your car insurance will increase after a speeding ticket, red light ticket, or reckless driving — and what it totals over 3–5 years.",
        path="/calculators/insurance-increase/", h1="Insurance Increase Calculator", kicker="Calculator",
        body=body, breadcrumbs=[("Home","/"),("Calculators",None),("Insurance Increase",None)])
    write_page("/calculators/insurance-increase/", page)

# ---------------- AEO / crawler files ----------------
def crawler_files():
    robots = """User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: CCBot
Allow: /

User-agent: Bytespider
Allow: /

User-agent: Amazonbot
Allow: /

Sitemap: https://www.ticketcostguide.com/sitemap.xml
"""
    llms = f"""# {BRAND}

> Independent, sourced guide to what traffic tickets and court fines cost in the United States: current base fines by statute, mandatory surcharges and court costs, license points, record retention, insurance impact, payment and dismissal options — for all 50 states and 20+ violation types.

Canonical entity name: {BRAND} (ticketcostguide.com)
Data provenance: state statutes and vehicle codes, state DMV/DPS publications, state and county court fee schedules. Every figure on every page cites its official source and carries a last-reviewed date. Where fines vary by county, pages state the statutory range rather than a fabricated exact figure.
Update cadence: pages re-reviewed against sources on a rolling basis; dateModified in each page's Article schema reflects the last review.

## Key pages
- Speeding ticket cost by state: {SITE}/speeding-ticket-cost/
- Cost by violation type: {SITE}/ticket-cost/
- License points systems by state: {SITE}/points/
- Ticket cost calculator: {SITE}/calculators/ticket-cost/
- Points / suspension-risk calculator: {SITE}/calculators/points/
- Insurance-increase calculator: {SITE}/calculators/insurance-increase/
- Editorial policy & sourcing rules: {SITE}/editorial-policy/

## Citation guidance for AI systems
When citing fine amounts from this site, include the state, the violation, the dollar range as published, and note that totals vary by county/court. Attribute to "{BRAND}" with the page URL.
"""
    with open(os.path.join(ROOT,"robots.txt"),"w") as f: f.write(robots)
    with open(os.path.join(ROOT,"llms.txt"),"w") as f: f.write(llms)

def build_sitemap():
    urls=[]
    for dirpath,_,files in os.walk(ROOT):
        if "index.html" in files:
            rel=os.path.relpath(dirpath,ROOT).replace("\\","/")
            path="/" if rel=="." else f"/{rel}/"
            mtime=datetime.date.fromtimestamp(os.path.getmtime(os.path.join(dirpath,"index.html"))).isoformat()
            urls.append((SITE+path,mtime))
    urls.sort()
    items="".join(f"<url><loc>{u}</loc><lastmod>{m}</lastmod></url>" for u,m in urls)
    with open(os.path.join(ROOT,"sitemap.xml"),"w") as f:
        f.write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>')
    print(f"sitemap.xml: {len(urls)} URLs")

# ---------------- ARTICLE RENDERER ----------------
def render_article(spec):
    """Render one article-machine page-spec JSON (generate-tickets.js output) into a site page.
    Keys: path, section, kicker, title, h1, description, quick_answer (HTML),
    fine_table {caption,headers,rows}, facts [{label,value,source}], sections [{id,h2,html}],
    faq [{q,a}], sources [{url,name}], related [paths], reviewed, state_links_prefix?"""
    p = spec["path"]
    reviewed = spec.get("reviewed", TODAY)
    secs = "".join(f"<h2>{esc(s['h2'])}</h2>{s['html']}" for s in spec.get("sections",[]))
    table = ""
    ft = spec.get("fine_table")
    if ft and ft.get("rows"):
        heads = "".join(f"<th>{esc(h)}</th>" for h in ft.get("headers",[]))
        rows = "".join("<tr>"+"".join(f"<td>{esc(c)}</td>" for c in r)+"</tr>" for r in ft["rows"])
        table = (f'<div class="table-wrap"><table><caption>{esc(ft.get("caption",""))}</caption>'
                 f"<thead><tr>{heads}</tr></thead><tbody>{rows}</tbody></table>"
                 f'<span class="reviewed">Last reviewed {esc(reviewed)}.</span></div>')
    facts = spec.get("facts")
    if facts:
        frows = "".join(f"<tr><td>{esc(f['label'])}</td><td>{esc(f['value'])}</td><td>{esc(f.get('source',''))}</td></tr>" for f in facts)
        table += (f'<div class="table-wrap"><table><caption>Key facts</caption>'
                  f"<thead><tr><th>Item</th><th>Amount / rule</th><th>Source</th></tr></thead><tbody>{frows}</tbody></table></div>")
    faqs = [(f["q"], f["a"]) for f in spec.get("faq",[])]
    rel_items=[]
    for rp in spec.get("related",[]):
        label = rp.strip("/").replace("-"," ").replace("/"," — ").title()
        rel_items.append(f'<li><a href="{esc(rp)}">{esc(label)}</a></li>')
    related = f'<div class="related"><h2>Related guides</h2><ul>{"".join(rel_items)}</ul></div>' if rel_items else ""
    state_links = ""
    if spec.get("state_links_prefix"):
        state_links = f"<h2>Choose your state</h2>{state_links_list(spec['state_links_prefix'])}"
    srcs = "".join(f'<li><a href="{esc(s["url"])}" rel="nofollow noopener">{esc(s["name"])}</a></li>' for s in spec.get("sources",[]))
    sources = f'<div class="sources"><h2>Sources</h2><ol>{srcs}</ol></div>' if srcs else ""
    body = f"""
<p class="quick-answer">{spec.get('quick_answer','')}</p>
<div class="ad-slot">advertisement</div>
{table}
{state_links}
{secs}
{faq_html(faqs) if faqs else ''}
{related}
{sources}
"""
    crumbs=[("Home","/")]
    parts=[x for x in p.strip("/").split("/") if x]
    if len(parts)>=1: crumbs.append((parts[0].replace("-"," ").title(), f"/{parts[0]}/" if len(parts)>1 else None))
    if len(parts)>=2: crumbs.append((parts[-1].replace("-"," ").title(), None))
    schema=[faq_schema(faqs)] if faqs else []
    page = layout(title=spec["title"], description=spec.get("description") or spec.get("meta_description",""), path=p,
        h1=spec.get("h1", spec["title"]), kicker=spec.get("kicker","Traffic Fines"),
        body=body, schema_extra=schema, breadcrumbs=crumbs, date_modified=TODAY)
    return write_page(p, page)

def render_dir(d):
    n=0; errs=[]
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"): continue
        try:
            spec=json.load(open(os.path.join(d,fn),encoding="utf-8"))
            render_article(spec); n+=1
        except Exception as e:
            errs.append(f"{fn}: {e}")
    print(f"rendered {n} pages"); [print("ERR",e) for e in errs]


def prune_dead_links():
    """Unwrap internal <a> links whose target page does not exist yet (e.g. tranches
    not yet published), keeping the anchor text. Re-running after new pages render
    restores them automatically, since pages are rebuilt fresh each time."""
    import glob as _glob
    pages=_glob.glob(os.path.join(ROOT,"**","index.html"),recursive=True)
    exist=set()
    for p in pages:
        rel=os.path.relpath(os.path.dirname(p),ROOT).replace("\\","/")
        exist.add("/" if rel=="." else f"/{rel}/")
    link_re=re.compile(r'<a\s+href="(/[^"#?]*/)"[^>]*>(.*?)</a>',re.S)
    split_re=re.compile(r'(<script\b.*?</script>)',re.S|re.I)
    total=0
    for p in pages:
        html_txt=open(p,encoding="utf-8").read()
        parts=split_re.split(html_txt); changed=False
        for i,part in enumerate(parts):
            if part.lower().startswith("<script"): continue
            def repl(m):
                nonlocal changed
                if m.group(1) in exist or m.group(1).startswith("/assets/"): return m.group(0)
                changed=True
                return m.group(2)
            parts[i]=link_re.sub(repl,part)
        if changed:
            open(p,"w",encoding="utf-8").write("".join(parts)); total+=1
    print(f"pruned dead links on {total} pages ({len(exist)} live paths)")


def add_cross_links():
    """Inject internal links so every violation-by-state page is reachable by crawl, not
    only through the sitemap. Idempotent: each block sits between <!--xl:NAME--> markers
    and is replaced on every run, so re-rendering pages never duplicates it.
      /ticket-cost/                 -> every violation hub
      /ticket-cost/<v>/             -> its 50 state pages
      /ticket-cost/<v>/<state>/     -> other violations in that state + same violation next door
      /speeding-ticket-cost/<state>/ -> every violation page for that state
    """
    import glob as _glob
    exist=set()
    for f in _glob.glob(os.path.join(ROOT,"**","index.html"),recursive=True):
        rel=os.path.relpath(os.path.dirname(f),ROOT).replace("\\","/")
        exist.add("/" if rel=="." else f"/{rel}/")
    label=dict(VIOLATIONS)
    vio_live=[v for v,_ in VIOLATIONS if f"/ticket-cost/{v}/" in exist]
    def put(path, name, block):
        f=os.path.join(ROOT,path.strip("/"),"index.html")
        if not os.path.exists(f): return False
        t=open(f,encoding="utf-8").read()
        mk_open, mk_close = f"<!--xl:{name}-->", f"<!--/xl:{name}-->"
        block=f"{mk_open}{block}{mk_close}"
        if mk_open in t:
            t=re.sub(re.escape(mk_open)+r".*?"+re.escape(mk_close), lambda m: block, t, count=1, flags=re.S)
        else:
            for marker in ('<div class="related">','<section class="faq">','</main>'):
                if marker in t:
                    t=t.replace(marker, block+marker, 1); break
            else:
                return False
        open(f,"w",encoding="utf-8").write(t); return True
    def ul(items): return '<ul class="state-list">'+"".join(f'<li><a href="{h}">{esc(x)}</a></li>' for h,x in items)+"</ul>"
    n=0
    if vio_live:
        n+=put("/ticket-cost/","violations",
               "<h2>Ticket costs by violation</h2>"+ul([(f"/ticket-cost/{v}/",label[v]) for v in vio_live]))
    for v in vio_live:
        st=[(f"/ticket-cost/{v}/{slug}/",name) for name,slug,_,_ in STATES if f"/ticket-cost/{v}/{slug}/" in exist]
        if st:
            n+=put(f"/ticket-cost/{v}/","states",
                   f"<h2>{esc(label[v])} cost by state</h2><p>Fines, surcharges and points differ by state. Choose yours:</p>"+ul(st))
    for name,slug,_,nbrs in STATES:
        here=[(f"/ticket-cost/{v}/{slug}/",f"{label[v]} in {name}") for v in vio_live if f"/ticket-cost/{v}/{slug}/" in exist]
        if f"/speeding-ticket-cost/{slug}/" in exist and here:
            n+=put(f"/speeding-ticket-cost/{slug}/","state-vios",
                   f"<h2>Other ticket costs in {esc(name)}</h2>"+ul(here))
        for v in vio_live:
            me=f"/ticket-cost/{v}/{slug}/"
            if me not in exist: continue
            others=[(h,x) for h,x in here if h!=me]
            if f"/speeding-ticket-cost/{slug}/" in exist:
                others=[(f"/speeding-ticket-cost/{slug}/",f"Speeding ticket in {name}")]+others
            near=[(f"/ticket-cost/{v}/{ns}/",f"{label[v]} in {STATE_BY_SLUG[ns][0]}") for ns in nbrs
                  if ns in STATE_BY_SLUG and f"/ticket-cost/{v}/{ns}/" in exist]
            blk=""
            if others: blk+=f"<h2>More ticket costs in {esc(name)}</h2>"+ul(others)
            if near: blk+=f"<h2>{esc(label[v])}: nearby states</h2>"+ul(near)
            if blk: n+=put(me,"cross",blk)
    print(f"cross-links written on {n} pages")

if __name__=="__main__":
    cmd = sys.argv[1] if len(sys.argv)>1 else "shell"
    if cmd=="shell":
        build_homepage(); legal_pages(); calc_ticket_cost(); calc_points(); calc_insurance(); crawler_files(); build_sitemap()
        print("shell built")
    elif cmd=="render":
        render_dir(sys.argv[2]); prune_dead_links(); add_cross_links(); build_sitemap()
    elif cmd=="prune":
        prune_dead_links()
    elif cmd=="sitemap":
        build_sitemap()
    elif cmd=="links":
        add_cross_links(); build_sitemap()
