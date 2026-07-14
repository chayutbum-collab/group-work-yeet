from ._anvil_designer import Form1Template
from anvil import *
from functools import partial
import anvil.media
import anvil.tables as tables
from anvil.tables import app_tables
import datetime
USERNAME = 'admin'
PASSWORD = 'admin123'
PLANS = {'Free': 0.08, 'Pro': 0.05, 'Business': 0.03}
PLAN_NAMES = ['Free', 'Pro', 'Business']
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
STATUSES = ['Approved', 'Pending', 'Flagged', 'Featured']
THEME = '#176b87'
OK_GREEN = '#1a7f4b'
BAD_RED = '#b3372f'
WARN_ORANGE = '#c2620a'
BG_PAID = '#eaf6ee'
BG_DUE = '#fdf3e6'
BG_OVERDUE = '#fdeaea'
TITLE_SIZE = 27
NAV_PAGES = ['Dashboard', 'Organizers', 'Events', 'Reports', 'Audit log', 'Settings']
ICONS = {'Dashboard': 'fa:dashboard', 'Organizers': 'fa:users', 'Events': 'fa:calendar', 'Reports': 'fa:file-text-o', 'Audit log': 'fa:history', 'Settings': 'fa:cog'}
_ORGS = [('Bangkok Runners Club', 'Pro', 'Active'), ('MUIC Music Society', 'Free', 'Active'), ('TechConf Asia', 'Business', 'Active'), ('Chiang Mai Food Fest', 'Pro', 'Active'), ('Indie Game Meetup', 'Free', 'Suspended')]
_EVENTS = [('E001', 'Sunday Half Marathon', 'Bangkok Runners Club', 4, 12, 320, 450), ('E002', 'Night Trail 10K', 'Bangkok Runners Club', 5, 17, 210, 500), ('E003', 'Riverside Fun Run', 'Bangkok Runners Club', 6, 14, 180, 350), ('E004', 'Spring Recital', 'MUIC Music Society', 4, 26, 90, 200), ('E005', 'Jazz Night', 'MUIC Music Society', 6, 6, 140, 250), ('E006', 'Cloud and AI Summit', 'TechConf Asia', 5, 8, 640, 1800), ('E007', 'DevOps Workshop', 'TechConf Asia', 6, 19, 120, 2500), ('E008', 'Street Food Festival', 'Chiang Mai Food Fest', 4, 5, 850, 150), ('E009', 'Craft Beer and BBQ', 'Chiang Mai Food Fest', 5, 24, 430, 300), ('E010', 'Northern Coffee Fair', 'Chiang Mai Food Fest', 6, 21, 510, 180), ('E011', 'Indie Showcase Vol.4', 'Indie Game Meetup', 4, 30, 160, 120), ('E012', 'Retro Arcade Night', 'Indie Game Meetup', 5, 29, 110, 150)]

def _fmt(m, d):
  return '%02d %s 2026' % (d, MONTHS[int(m) - 1])

def _now():
  n = datetime.datetime.now()
  return '%02d/%02d/%04d %02d:%02d' % (n.day, n.month, n.year, n.hour, n.minute)

class Form1(Form1Template):

  def __init__(self, **properties):
    super().__init__(**properties)
    self.audit = []
    self.plans = dict(PLANS)
    self.dash_period = '(All periods)'
    self.evt_filter = '(All statuses)'
    self.evt_search = ''
    self.evt_sort = 'Date'
    self.show_add_evt = False
    self.org_search = ''
    self.org_sort = 'GMV'
    self.show_add_org = False
    self.detail_org = None
    self.detail_evt = None
    self.rep_org = '(All organizers)'
    self.rep_period = '(All periods)'
    self.root = self.column_panel_1
    self._seed_if_empty()
    self._reload()
    self._show_login()

  def _seed_if_empty(self):
    if len(app_tables.organizers.search()) > 0:
      return
    for (name, plan, status) in _ORGS:
      app_tables.organizers.add_row(name=name, plan=plan, status=status)
    for (ref, title, org, m, d, part, price) in _EVENTS:
      app_tables.events.add_row(ref=ref, title=title, organizer=org, month=m, day=d, participants=part, price=price, status='Approved')
    seen = set()
    for (ref, title, org, m, d, part, price) in _EVENTS:
      key = (org, '2026-%02d' % m)
      if key in seen:
        continue
      seen.add(key)
      st = 'Paid'
      if m == 6:
        st = 'Due'
      if org == 'Indie Game Meetup' and m == 5:
        st = 'Overdue'
      app_tables.invoices.add_row(organizer=org, period=key[1], status=st)

  def _reload(self):
    self.orgs = []
    for r in app_tables.organizers.search():
      plan = r['plan']
      self.orgs.append({'row': r, 'name': r['name'], 'plan': plan, 'rate': self.plans.get(plan, 0.05), 'status': r['status']})
    self.events = []
    for r in app_tables.events.search():
      org = r['organizer']
      part = r['participants'] or 0
      price = r['price'] or 0
      gmv = part * price
      comm = int(round(gmv * self._rate_of(org)))
      self.events.append({'row': r, 'ref': r['ref'], 'title': r['title'], 'organizer': org, 'month': r['month'], 'day': r['day'], 'participants': part, 'price': price, 'gmv': gmv, 'commission': comm, 'status': r['status'], 'date_str': _fmt(r['month'], r['day'])})
    self.invoices = []
    for r in app_tables.invoices.search():
      org = r['organizer']
      period = r['period']
      evs = [e for e in self.events if e['organizer'] == org and '2026-%02d' % e['month'] == period]
      self.invoices.append({'row': r, 'organizer': org, 'period': period, 'gmv': sum([e['gmv'] for e in evs]), 'commission': sum([e['commission'] for e in evs]), 'status': r['status'], 'issued_str': _fmt(int(period[5:7]), 28)})

  def _refresh(self, page, **e):
    self._reload()
    self._show(page)

  def _log(self, action):
    self.audit.insert(0, {'time': _now(), 'user': USERNAME, 'action': action})

  def _rate_of(self, name):
    for o in self.orgs:
      if o['name'] == name:
        return o['rate']
    return 0.05

  def _events_of(self, name):
    return [e for e in self.events if e['organizer'] == name]

  def _invoices_of(self, name):
    return [i for i in self.invoices if i['organizer'] == name]

  def _due_of(self, name):
    return sum([i['commission'] for i in self._invoices_of(name) if i['status'] in ('Due', 'Overdue')])

  def _overdue_of(self, name):
    return sum([i['commission'] for i in self._invoices_of(name) if i['status'] == 'Overdue'])

  def _periods(self):
    return sorted(set([i['period'] for i in self.invoices]))

  def _next_ref(self):
    n = 1
    used = set([e['ref'] for e in self.events])
    while 'E%03d' % n in used:
      n += 1
    return 'E%03d' % n

  def _ensure_invoice(self, org, m):
    period = '2026-%02d' % m
    row = app_tables.invoices.get(organizer=org, period=period)
    if row is None:
      app_tables.invoices.add_row(organizer=org, period=period, status='Due')

  def _show_login(self):
    self.root.clear()
    card = ColumnPanel(role='card')
    card.add_component(Label(text='Owner Console - Staff Login', role='headline', font_size=TITLE_SIZE, bold=True))
    card.add_component(Label(text='Platform staff only. This console holds every organizer billing data.', foreground='#6b6975', spacing_below='small'))
    self.tb_user = TextBox(placeholder='Username')
    self.tb_pass = TextBox(placeholder='Password', hide_text=True)
    self.tb_pass.set_event_handler('pressed_enter', self._do_login)
    card.add_component(self.tb_user)
    card.add_component(self.tb_pass)
    btn = Button(text='Log in', icon='fa:sign-in', role='primary-color', spacing_above='small')
    btn.set_event_handler('click', self._do_login)
    card.add_component(btn)
    card.add_component(Label(text='Demo login  ->  username: admin   password: admin123', foreground='#6b6975', spacing_above='small'))
    self.root.add_component(card)

  def _do_login(self, **e):
    if self.tb_user.text == USERNAME and self.tb_pass.text == PASSWORD:
      self._log('Logged in')
      self._build_console()
    else:
      Notification('Wrong username or password.', style='danger').show()

  def _logout(self, **e):
    self._log('Logged out')
    self._show_login()

  def _build_console(self):
    self.root.clear()
    self.nav = FlowPanel(align='left', spacing_below='medium')
    self.root.add_component(self.nav)
    self.content = ColumnPanel()
    self.root.add_component(self.content)
    self._refresh('Dashboard')

  def _draw_nav(self, current):
    self.nav.clear()
    for name in NAV_PAGES:
      if name == current:
        b = Button(text=name, icon=ICONS[name], role='primary-color')
        self.nav.add_component(b)
      else:
        link = Link(text=name, icon=ICONS[name])
        link.set_event_handler('click', partial(self._refresh, name))
        self.nav.add_component(link)
    out = Link(text='Log out', icon='fa:sign-out')
    out.set_event_handler('click', self._logout)
    self.nav.add_component(out)

  def _show(self, page, **e):
    self.current_page = page
    nav_for = page
    if page == 'OrgDetail':
      nav_for = 'Organizers'
    if page == 'EvtDetail':
      nav_for = 'Events'
    self._draw_nav(nav_for)
    self.content.clear()
    pages = {'Dashboard': self._dashboard, 'Organizers': self._organizers, 'OrgDetail': self._org_detail, 'Events': self._events, 'EvtDetail': self._evt_detail, 'Reports': self._reports, 'Audit log': self._audit_page, 'Settings': self._settings_page}
    pages[page]()

  def _dash_change(self, **e):
    self.dash_period = e['sender'].selected_value
    self._show('Dashboard')

  def _dashboard(self):
    self.content.add_component(Label(text='Event Platform - Owner Console', role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='Billing and commission across every organizer', foreground='#6b6975'))
    bar = FlowPanel(align='left', spacing_below='medium')
    bar.add_component(Label(text='Period:'))
    ddp = DropDown(items=['(All periods)'] + self._periods(), selected_value=self.dash_period)
    ddp.set_event_handler('change', self._dash_change)
    bar.add_component(ddp)
    self.content.add_component(bar)
    evs = self.events
    invs = self.invoices
    if self.dash_period != '(All periods)':
      evs = [e for e in self.events if '2026-%02d' % e['month'] == self.dash_period]
      invs = [i for i in self.invoices if i['period'] == self.dash_period]
    overdue = [o for o in self.orgs if self._overdue_of(o['name']) > 0]
    if overdue:
      alert = ColumnPanel(role='card', spacing_below='medium')
      alert.add_component(Label(text='! Overdue invoices need attention', bold=True, font_size=16, foreground=BAD_RED))
      for o in overdue:
        alert.add_component(Label(text='%s  -  overdue THB %s  (%s)' % (o['name'], '{:,.0f}'.format(self._overdue_of(o['name'])), o['status']), foreground=BAD_RED))
      self.content.add_component(alert)
    gmv = sum([e['gmv'] for e in evs])
    earned = sum([i['commission'] for i in invs])
    collected = sum([i['commission'] for i in invs if i['status'] == 'Paid'])
    outstanding = sum([i['commission'] for i in invs if i['status'] in ('Due', 'Overdue')])
    n_ev = len(evs)
    n_part = sum([e['participants'] for e in evs])
    coll_rate = collected * 100.0 / earned if earned else 0
    take_rate = earned * 100.0 / gmv if gmv else 0
    avg_rate = sum([o['rate'] for o in self.orgs]) / len(self.orgs) * 100 if self.orgs else 0
    avg_gmv = gmv / n_ev if n_ev else 0
    avg_part = n_part / n_ev if n_ev else 0
    avg_price = sum([e['price'] for e in evs]) / n_ev if n_ev else 0
    avg_comm = earned / n_ev if n_ev else 0
    groups = []
    groups.append(('PLATFORM', [('Organizers', '{:,}'.format(len(self.orgs))), ('Active', '{:,}'.format(len([o for o in self.orgs if o['status'] == 'Active']))), ('Suspended', '{:,}'.format(len([o for o in self.orgs if o['status'] == 'Suspended']))), ('Events', '{:,}'.format(n_ev)), ('Participants', '{:,}'.format(n_part))]))
    groups.append(('MONEY  (THB)', [('GMV', '{:,.0f}'.format(gmv)), ('Commission earned', '{:,.0f}'.format(earned)), ('Collected', '{:,.0f}'.format(collected)), ('Outstanding', '{:,.0f}'.format(outstanding))]))
    groups.append(('RATES', [('Collection rate', '{:.0f}%'.format(coll_rate)), ('Take rate (comm/GMV)', '{:.1f}%'.format(take_rate)), ('Avg commission rate', '{:.1f}%'.format(avg_rate))]))
    groups.append(('INVOICES', [('Total', '{:,}'.format(len(invs))), ('Due', '{:,}'.format(len([i for i in invs if i['status'] == 'Due']))), ('Overdue', '{:,}'.format(len([i for i in invs if i['status'] == 'Overdue'])))]))
    groups.append(('AVERAGE PER EVENT', [('GMV (THB)', '{:,.0f}'.format(avg_gmv)), ('Commission (THB)', '{:,.0f}'.format(avg_comm)), ('Participants', '{:,.0f}'.format(avg_part)), ('Ticket price (THB)', '{:,.0f}'.format(avg_price)), ('Pending review', '{:,}'.format(len([e for e in evs if e['status'] == 'Pending'])))]))
    for (gtitle, items) in groups:
      self.content.add_component(Label(text=gtitle, bold=True, font_size=13, foreground='#8a8894', spacing_above='medium'))
      rowp = FlowPanel(align='left')
      for (cap, val) in items:
        c = ColumnPanel(role='card')
        c.add_component(Label(text=val, font_size=24, bold=True, foreground=THEME))
        c.add_component(Label(text=cap, foreground='#6b6975'))
        rowp.add_component(c)
      self.content.add_component(rowp)
    by = {}
    for i in invs:
      by[i['organizer']] = by.get(i['organizer'], 0) + i['commission']
    pairs = sorted(by.items(), key=lambda kv: kv[1], reverse=True)
    if pairs:
      self.content.add_component(Label(text='Top organizer by commission: %s  (THB %s)' % (pairs[0][0], '{:,.0f}'.format(pairs[0][1])), bold=True, spacing_above='small'))
    months = {}
    for i in self.invoices:
      months[i['period']] = months.get(i['period'], 0) + i['commission']
    mpairs = sorted(months.items())
    try:
      import plotly.graph_objs as go
      p1 = Plot()
      p1.data = [go.Bar(x=[k for (k, v) in pairs], y=[v for (k, v) in pairs], marker={'color': THEME})]
      p1.layout.height = 320
      p1.layout.title = 'Commission earned by organizer (THB)'
      p1.layout.margin = {'t': 40, 'b': 120, 'l': 70, 'r': 20}
      self.content.add_component(p1)
      p2 = Plot()
      p2.data = [go.Scatter(x=[k for (k, v) in mpairs], y=[v for (k, v) in mpairs], mode='lines+markers', line={'color': OK_GREEN, 'width': 3})]
      p2.layout.height = 300
      p2.layout.title = 'Monthly commission trend (THB)'
      p2.layout.margin = {'t': 40, 'b': 60, 'l': 70, 'r': 20}
      self.content.add_component(p2)
    except Exception:
      pass

  def _organizers(self):
    self.content.add_component(Label(text='Organizers', role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='Click an organizer name to open its detail page', foreground='#6b6975'))
    bar = FlowPanel(align='left', spacing_below='medium')
    bar.add_component(Label(text='Search:'))
    self.tb_org = TextBox(text=self.org_search, placeholder='organizer name')
    self.tb_org.set_event_handler('pressed_enter', self._org_search_go)
    bar.add_component(self.tb_org)
    b = Button(text='Go', icon='fa:search')
    b.set_event_handler('click', self._org_search_go)
    bar.add_component(b)
    bar.add_component(Label(text='  Sort by:'))
    dd = DropDown(items=['GMV', 'Commission due', 'Name'], selected_value=self.org_sort)
    dd.set_event_handler('change', self._org_sort_changed)
    bar.add_component(dd)
    badd = Button(text='Add organizer', icon='fa:plus', role='primary-color')
    badd.set_event_handler('click', self._toggle_add_org)
    bar.add_component(badd)
    bcsv = Button(text='Export organizers CSV', icon='fa:download')
    bcsv.set_event_handler('click', self._export_orgs)
    bar.add_component(bcsv)
    bauto = Button(text='Auto-suspend overdue', icon='fa:ban', role='secondary-color')
    bauto.set_event_handler('click', self._auto_suspend)
    bar.add_component(bauto)
    self.content.add_component(bar)
    if self.show_add_org:
      box = ColumnPanel(role='card', spacing_below='medium')
      box.add_component(Label(text='New organizer', bold=True, font_size=16))
      self.tb_new_name = TextBox(placeholder='Organizer name')
      box.add_component(self.tb_new_name)
      row = FlowPanel(align='left')
      row.add_component(Label(text='Plan:'))
      self.dd_new_plan = DropDown(items=PLAN_NAMES, selected_value='Pro')
      row.add_component(self.dd_new_plan)
      s = Button(text='Save', icon='fa:check', role='primary-color')
      s.set_event_handler('click', self._save_new_org)
      row.add_component(s)
      c = Button(text='Cancel', icon='fa:times')
      c.set_event_handler('click', self._toggle_add_org)
      row.add_component(c)
      box.add_component(row)
      self.content.add_component(box)
    rows = [o for o in self.orgs if self.org_search.lower() in o['name'].lower()]
    if self.org_sort == 'GMV':
      rows.sort(key=lambda o: sum([e['gmv'] for e in self._events_of(o['name'])]), reverse=True)
    elif self.org_sort == 'Commission due':
      rows.sort(key=lambda o: self._due_of(o['name']), reverse=True)
    else:
      rows.sort(key=lambda o: o['name'])
    if not rows:
      self.content.add_component(Label(text='No organizer matches that search.', foreground='#6b6975'))
    for o in rows:
      self.content.add_component(self._org_card(o))

  def _org_card(self, o):
    mine = self._events_of(o['name'])
    due = self._due_of(o['name'])
    od = self._overdue_of(o['name'])
    inv = self._invoices_of(o['name'])
    bg = None
    if od > 0:
      bg = BG_OVERDUE
    elif due > 0:
      bg = BG_DUE
    elif o['status'] == 'Active':
      bg = BG_PAID
    card = ColumnPanel(role='card', spacing_below='small', background=bg)
    title = Link(text='%s   (%s plan - %.0f%% commission)   >' % (o['name'], o['plan'], o['rate'] * 100), bold=True, font_size=16)
    title.set_event_handler('click', partial(self._open_org, o['name']))
    card.add_component(title)
    if od > 0:
      card.add_component(Label(text='! OVERDUE THB ' + '{:,.0f}'.format(od), bold=True, foreground=BAD_RED))
    card.add_component(Label(text='%d events  -  %s participants  -  GMV THB %s  -  commission due THB %s' % (len(mine), '{:,}'.format(sum([e['participants'] for e in mine])), '{:,.0f}'.format(sum([e['gmv'] for e in mine])), '{:,.0f}'.format(due)), foreground='#6b6975'))
    paid_n = len([i for i in inv if i['status'] == 'Paid'])
    last_str = 'no events yet'
    if mine:
      last = sorted(mine, key=lambda e: (e['month'], e['day']))[-1]
      last_str = '%s (%s)' % (last['title'], last['date_str'])
    card.add_component(Label(text='%d invoice(s): %d paid / %d unpaid   |   latest event: %s' % (len(inv), paid_n, len(inv) - paid_n, last_str), foreground='#8a8894'))
    row = FlowPanel(align='left')
    row.add_component(Label(text='Status: ' + o['status'], bold=True, foreground=OK_GREEN if o['status'] == 'Active' else BAD_RED))
    row.add_component(Label(text='  Plan:'))
    ddp = DropDown(items=PLAN_NAMES, selected_value=o['plan'])
    ddp.set_event_handler('change', partial(self._change_plan, o))
    row.add_component(ddp)
    b1 = Button(text='Suspend' if o['status'] == 'Active' else 'Activate', icon='fa:ban' if o['status'] == 'Active' else 'fa:check', role='secondary-color')
    b1.set_event_handler('click', partial(self._toggle, o))
    row.add_component(b1)
    b2 = Button(text='Mark commission paid', icon='fa:money', role='primary-color')
    b2.set_event_handler('click', partial(self._paid, o['name']))
    row.add_component(b2)
    b3 = Button(text='Send reminder', icon='fa:envelope')
    b3.set_event_handler('click', partial(self._send_reminder, o['name']))
    row.add_component(b3)
    b4 = Button(text='Delete', icon='fa:trash')
    b4.set_event_handler('click', partial(self._delete_org, o))
    row.add_component(b4)
    card.add_component(row)
    return card

  def _org_search_go(self, **e):
    self.org_search = self.tb_org.text or ''
    self._show('Organizers')

  def _org_sort_changed(self, **e):
    self.org_sort = e['sender'].selected_value
    self._show('Organizers')

  def _toggle_add_org(self, **e):
    self.show_add_org = not self.show_add_org
    self._show('Organizers')

  def _save_new_org(self, **e):
    name = (self.tb_new_name.text or '').strip()
    if not name:
      Notification('Please type an organizer name.', style='warning').show()
      return
    if app_tables.organizers.get(name=name) is not None:
      Notification('That organizer already exists.', style='warning').show()
      return
    plan = self.dd_new_plan.selected_value
    app_tables.organizers.add_row(name=name, plan=plan, status='Active')
    self.show_add_org = False
    self._log('Added organizer %s on the %s plan' % (name, plan))
    Notification('Added organizer %s.' % name, style='success').show()
    self._refresh('Organizers')

  def _delete_org(self, o, **e):
    if not confirm('Delete %s and all of its events and invoices?' % o['name']):
      return
    for e2 in app_tables.events.search(organizer=o['name']):
      e2.delete()
    for i2 in app_tables.invoices.search(organizer=o['name']):
      i2.delete()
    o['row'].delete()
    self._log('Deleted organizer %s' % o['name'])
    Notification('Deleted %s.' % o['name'], style='success').show()
    self._refresh('Organizers')

  def _change_plan(self, o, **e):
    plan = e['sender'].selected_value
    o['row'].update(plan=plan)
    self._log('Changed %s plan: %s -> %s' % (o['name'], o['plan'], plan))
    Notification('%s is now on the %s plan.' % (o['name'], plan), style='success').show()
    self._refresh('Organizers')

  def _toggle(self, o, **e):
    new = 'Suspended' if o['status'] == 'Active' else 'Active'
    o['row'].update(status=new)
    self._log('Set %s to %s' % (o['name'], new))
    self._refresh('Organizers')

  def _paid(self, name, **e):
    n = 0
    for i in self._invoices_of(name):
      if i['status'] in ('Due', 'Overdue'):
        i['row'].update(status='Paid')
        n += 1
    self._log('Marked %d invoice(s) paid for %s' % (n, name))
    Notification('Marked %d invoice(s) paid for %s.' % (n, name), style='success').show()
    self._refresh('Organizers')

  def _send_reminder(self, name, **e):
    due = self._due_of(name)
    if due <= 0:
      Notification('%s has nothing outstanding.' % name, style='info').show()
      return
    self._log('Sent payment reminder to %s (THB %d outstanding)' % (name, due))
    Notification('Reminder sent to %s.' % name, style='success').show()
    self._show('Organizers')

  def _auto_suspend(self, **e):
    targets = [o for o in self.orgs if self._overdue_of(o['name']) > 0 and o['status'] == 'Active']
    if not targets:
      Notification('No active organizer is overdue.', style='info').show()
      return
    if not confirm('Suspend %d organizer(s) with overdue invoices?' % len(targets)):
      return
    for o in targets:
      o['row'].update(status='Suspended')
      self._log('Auto-suspended %s' % o['name'])
    Notification('Suspended %d overdue organizer(s).' % len(targets), style='success').show()
    self._refresh('Organizers')

  def _pay_one(self, inv, **e):
    inv['row'].update(status='Paid')
    self._log('Marked invoice %s / %s as Paid' % (inv['organizer'], inv['period']))
    Notification('Invoice %s marked Paid.' % inv['period'], style='success').show()
    self._refresh('OrgDetail')

  def _open_org(self, name, **e):
    self.detail_org = name
    self._show('OrgDetail')

  def _org_detail(self):
    org = None
    for o in self.orgs:
      if o['name'] == self.detail_org:
        org = o
    if org is None:
      self._show('Organizers')
      return
    back = Link(text='< Back to organizers')
    back.set_event_handler('click', partial(self._show, 'Organizers'))
    self.content.add_component(back)
    self.content.add_component(Label(text=org['name'], role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='%s plan  -  %.0f%% commission  -  %s' % (org['plan'], org['rate'] * 100, org['status']), foreground='#6b6975', spacing_below='medium'))
    mine = self._events_of(org['name'])
    my_inv = self._invoices_of(org['name'])
    my_earned = sum([i['commission'] for i in my_inv])
    my_paid = sum([i['commission'] for i in my_inv if i['status'] == 'Paid'])
    my_gmv = sum([e['gmv'] for e in mine])
    my_price = sum([e['price'] for e in mine]) / len(mine) if mine else 0
    kpis = FlowPanel(align='left')
    cards = [('Events', '{:,}'.format(len(mine))), ('Participants', '{:,}'.format(sum([e['participants'] for e in mine]))), ('GMV (THB)', '{:,.0f}'.format(my_gmv)), ('Commission earned (THB)', '{:,.0f}'.format(my_earned)), ('Collected (THB)', '{:,.0f}'.format(my_paid)), ('Commission due (THB)', '{:,.0f}'.format(self._due_of(org['name']))), ('Invoices', '{:,}'.format(len(my_inv))), ('Avg ticket price (THB)', '{:,.0f}'.format(my_price))]
    for (cap, val) in cards:
      c = ColumnPanel(role='card')
      c.add_component(Label(text=val, font_size=22, bold=True))
      c.add_component(Label(text=cap, foreground='#6b6975'))
      kpis.add_component(c)
    self.content.add_component(kpis)
    self.content.add_component(Label(text='Events (click to open)', bold=True, font_size=16, spacing_above='medium'))
    if not mine:
      self.content.add_component(Label(text='No events yet.', foreground='#6b6975'))
    for ev in sorted(mine, key=lambda e: (e['month'], e['ref'])):
      c = ColumnPanel(role='card', spacing_below='small')
      lk = Link(text='%s (%s)  >' % (ev['title'], ev['ref']))
      lk.set_event_handler('click', partial(self._open_evt, ev['ref']))
      c.add_component(lk)
      c.add_component(Label(text='%s  -  %s participants  -  GMV THB %s  -  commission THB %s  -  %s' % (ev['date_str'], '{:,}'.format(ev['participants']), '{:,.0f}'.format(ev['gmv']), '{:,.0f}'.format(ev['commission']), ev['status']), foreground='#6b6975'))
      self.content.add_component(c)
    self.content.add_component(Label(text='Invoices', bold=True, font_size=16, spacing_above='medium'))
    if not my_inv:
      self.content.add_component(Label(text='No invoices yet.', foreground='#6b6975'))
    for i in sorted(my_inv, key=lambda i: i['period']):
      colour = {'Paid': OK_GREEN, 'Due': WARN_ORANGE, 'Overdue': BAD_RED}.get(i['status'])
      bgi = {'Paid': BG_PAID, 'Due': BG_DUE, 'Overdue': BG_OVERDUE}.get(i['status'])
      c = ColumnPanel(role='card', spacing_below='small', background=bgi)
      c.add_component(Label(text='%s  -  commission THB %s' % (i['period'], '{:,.0f}'.format(i['commission'])), bold=True))
      c.add_component(Label(text='%s  -  issued %s' % (i['status'], i['issued_str']), foreground=colour))
      if i['status'] in ('Due', 'Overdue'):
        bp = Button(text='Mark this invoice paid', icon='fa:money', role='primary-color')
        bp.set_event_handler('click', partial(self._pay_one, i))
        c.add_component(bp)
      self.content.add_component(c)

  def _open_evt(self, ref, **e):
    self.detail_evt = ref
    self._show('EvtDetail')

  def _evt_detail(self):
    ev = None
    for x in self.events:
      if x['ref'] == self.detail_evt:
        ev = x
    if ev is None:
      self._show('Events')
      return
    back = Link(text='< Back to events')
    back.set_event_handler('click', partial(self._show, 'Events'))
    self.content.add_component(back)
    self.content.add_component(Label(text='%s (%s)' % (ev['title'], ev['ref']), role='headline', font_size=TITLE_SIZE, bold=True))
    lk = Link(text='Organizer: %s  >' % ev['organizer'])
    lk.set_event_handler('click', partial(self._open_org, ev['organizer']))
    self.content.add_component(lk)
    self.content.add_component(Label(text='%s  -  status: %s' % (ev['date_str'], ev['status']), foreground='#6b6975', spacing_below='medium'))
    rate = self._rate_of(ev['organizer'])
    kpis = FlowPanel(align='left')
    cards = [('Participants', '{:,}'.format(ev['participants'])), ('Ticket price (THB)', '{:,.0f}'.format(ev['price'])), ('GMV (THB)', '{:,.0f}'.format(ev['gmv'])), ('Commission rate', '{:.0f}%'.format(rate * 100)), ('Commission (THB)', '{:,.0f}'.format(ev['commission'])), ('Organizer keeps (THB)', '{:,.0f}'.format(ev['gmv'] - ev['commission']))]
    for (cap, val) in cards:
      c = ColumnPanel(role='card')
      c.add_component(Label(text=val, font_size=22, bold=True))
      c.add_component(Label(text=cap, foreground='#6b6975'))
      kpis.add_component(c)
    self.content.add_component(kpis)
    box = ColumnPanel(role='card', spacing_above='medium')
    box.add_component(Label(text='How this commission was calculated', bold=True, font_size=16))
    box.add_component(Label(text='GMV = %s participants x THB %s ticket = THB %s' % ('{:,}'.format(ev['participants']), '{:,.0f}'.format(ev['price']), '{:,.0f}'.format(ev['gmv'])), foreground='#6b6975'))
    box.add_component(Label(text='Commission = GMV x %.0f%% (%s plan) = THB %s' % (rate * 100, self._plan_of(ev['organizer']), '{:,.0f}'.format(ev['commission'])), foreground='#6b6975'))
    period = '2026-%02d' % ev['month']
    inv = app_tables.invoices.get(organizer=ev['organizer'], period=period)
    st = inv['status'] if inv is not None else 'no invoice'
    box.add_component(Label(text='This amount is billed on invoice %s  (status: %s)' % (period, st), foreground='#6b6975'))
    self.content.add_component(box)
    row = FlowPanel(align='left', spacing_above='medium')
    row.add_component(Label(text='Set status:'))
    sd = DropDown(items=STATUSES, selected_value=ev['status'])
    sd.set_event_handler('change', partial(self._set_status_detail, ev))
    row.add_component(sd)
    bdel = Button(text='Delete event', icon='fa:trash')
    bdel.set_event_handler('click', partial(self._delete_event, ev))
    row.add_component(bdel)
    self.content.add_component(row)

  def _plan_of(self, name):
    for o in self.orgs:
      if o['name'] == name:
        return o['plan']
    return '-'

  def _set_status_detail(self, ev, **e):
    ev['row'].update(status=e['sender'].selected_value)
    self._log('Set event %s to %s' % (ev['ref'], e['sender'].selected_value))
    self._refresh('EvtDetail')

  def _events(self):
    self.content.add_component(Label(text='Events oversight', role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='Click an event title to open its detail page', foreground='#6b6975'))
    bar = FlowPanel(align='left', spacing_below='medium')
    bar.add_component(Label(text='Search:'))
    self.tb_evt = TextBox(text=self.evt_search, placeholder='event or organizer')
    self.tb_evt.set_event_handler('pressed_enter', self._evt_search_go)
    bar.add_component(self.tb_evt)
    b = Button(text='Go', icon='fa:search')
    b.set_event_handler('click', self._evt_search_go)
    bar.add_component(b)
    bar.add_component(Label(text='  Status:'))
    dd = DropDown(items=['(All statuses)'] + STATUSES, selected_value=self.evt_filter)
    dd.set_event_handler('change', self._evt_filter_changed)
    bar.add_component(dd)
    bar.add_component(Label(text='  Sort:'))
    dds = DropDown(items=['Date', 'GMV', 'Commission'], selected_value=self.evt_sort)
    dds.set_event_handler('change', self._evt_sort_changed)
    bar.add_component(dds)
    badd = Button(text='Add event', icon='fa:plus', role='primary-color')
    badd.set_event_handler('click', self._toggle_add_evt)
    bar.add_component(badd)
    self.content.add_component(bar)
    if self.show_add_evt:
      self.content.add_component(self._add_event_form())
    q2 = self.evt_search.lower()
    rows = [e for e in self.events if (self.evt_filter == '(All statuses)' or e['status'] == self.evt_filter) and (q2 in e['title'].lower() or q2 in e['organizer'].lower())]
    if self.evt_sort == 'GMV':
      rows.sort(key=lambda e: e['gmv'], reverse=True)
    elif self.evt_sort == 'Commission':
      rows.sort(key=lambda e: e['commission'], reverse=True)
    else:
      rows.sort(key=lambda e: (e['month'], e['ref']))
    if not rows:
      self.content.add_component(Label(text='No event matches that filter.', foreground='#6b6975'))
    for ev in rows:
      self.content.add_component(self._event_card(ev))

  def _event_card(self, ev):
    card = ColumnPanel(role='card', spacing_below='small')
    lk = Link(text='%s  (%s)   >' % (ev['title'], ev['ref']))
    lk.set_event_handler('click', partial(self._open_evt, ev['ref']))
    card.add_component(lk)
    card.add_component(Label(text='%s  -  %s' % (ev['organizer'], ev['date_str']), foreground='#6b6975'))
    card.add_component(Label(text='%s participants  x  THB %s ticket  =  GMV THB %s   ->   commission THB %s  (%.0f%%)' % ('{:,}'.format(ev['participants']), '{:,.0f}'.format(ev['price']), '{:,.0f}'.format(ev['gmv']), '{:,.0f}'.format(ev['commission']), self._rate_of(ev['organizer']) * 100), foreground='#8a8894'))
    row = FlowPanel(align='left')
    row.add_component(Label(text='Status:'))
    sd = DropDown(items=STATUSES, selected_value=ev['status'])
    sd.set_event_handler('change', partial(self._set_status, ev))
    row.add_component(sd)
    bdel = Button(text='Delete', icon='fa:trash')
    bdel.set_event_handler('click', partial(self._delete_event, ev))
    row.add_component(bdel)
    card.add_component(row)
    return card

  def _add_event_form(self):
    box = ColumnPanel(role='card', spacing_below='medium')
    box.add_component(Label(text='New event', bold=True, font_size=16))
    self.tb_ev_title = TextBox(placeholder='Event title')
    box.add_component(self.tb_ev_title)
    r1 = FlowPanel(align='left')
    r1.add_component(Label(text='Organizer:'))
    self.dd_ev_org = DropDown(items=sorted([o['name'] for o in self.orgs]))
    r1.add_component(self.dd_ev_org)
    r1.add_component(Label(text='Month:'))
    self.dd_ev_month = DropDown(items=['Apr', 'May', 'Jun'], selected_value='Jun')
    r1.add_component(self.dd_ev_month)
    r1.add_component(Label(text='Day:'))
    self.tb_ev_day = TextBox(text='15')
    r1.add_component(self.tb_ev_day)
    box.add_component(r1)
    r2 = FlowPanel(align='left')
    r2.add_component(Label(text='Participants:'))
    self.tb_ev_part = TextBox(text='100')
    r2.add_component(self.tb_ev_part)
    r2.add_component(Label(text='Ticket price (THB):'))
    self.tb_ev_price = TextBox(text='300')
    r2.add_component(self.tb_ev_price)
    s = Button(text='Save', icon='fa:check', role='primary-color')
    s.set_event_handler('click', self._save_new_event)
    r2.add_component(s)
    c = Button(text='Cancel', icon='fa:times')
    c.set_event_handler('click', self._toggle_add_evt)
    r2.add_component(c)
    box.add_component(r2)
    return box

  def _toggle_add_evt(self, **e):
    self.show_add_evt = not self.show_add_evt
    self._show('Events')

  def _save_new_event(self, **e):
    title = (self.tb_ev_title.text or '').strip()
    if not title:
      Notification('Please type an event title.', style='warning').show()
      return
    try:
      day = int(self.tb_ev_day.text)
      part = int(self.tb_ev_part.text)
      price = int(self.tb_ev_price.text)
    except Exception:
      Notification('Day, participants and price must be numbers.', style='warning').show()
      return
    org = self.dd_ev_org.selected_value
    if not org:
      Notification('Add an organizer first.', style='warning').show()
      return
    m = {'Apr': 4, 'May': 5, 'Jun': 6}[self.dd_ev_month.selected_value]
    ref = self._next_ref()
    app_tables.events.add_row(ref=ref, title=title, organizer=org, month=m, day=day, participants=part, price=price, status='Pending')
    self._ensure_invoice(org, m)
    self.show_add_evt = False
    self._log('Added event %s (%s) for %s' % (title, ref, org))
    Notification('Added event %s.' % title, style='success').show()
    self._refresh('Events')

  def _delete_event(self, ev, **e):
    if not confirm('Delete event %s?' % ev['title']):
      return
    ev['row'].delete()
    self._log('Deleted event %s (%s)' % (ev['title'], ev['ref']))
    Notification('Deleted %s.' % ev['title'], style='success').show()
    self._refresh('Events')

  def _evt_search_go(self, **e):
    self.evt_search = self.tb_evt.text or ''
    self._show('Events')

  def _evt_filter_changed(self, **e):
    self.evt_filter = e['sender'].selected_value
    self._show('Events')

  def _evt_sort_changed(self, **e):
    self.evt_sort = e['sender'].selected_value
    self._show('Events')

  def _set_status(self, ev, **e):
    ev['row'].update(status=e['sender'].selected_value)
    self._log('Set event %s to %s' % (ev['ref'], e['sender'].selected_value))
    self._refresh('Events')

  def _reports(self):
    self.content.add_component(Label(text='Reports and data export', role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='Commission billing records - filter and export as CSV', foreground='#6b6975'))
    names = sorted(set([o['name'] for o in self.orgs]))
    bar = FlowPanel(align='left')
    bar.add_component(Label(text='Organizer:'))
    self.dd_org = DropDown(items=['(All organizers)'] + names, selected_value=self.rep_org)
    bar.add_component(self.dd_org)
    bar.add_component(Label(text='Period:'))
    self.dd_period = DropDown(items=['(All periods)'] + self._periods(), selected_value=self.rep_period)
    bar.add_component(self.dd_period)
    b1 = Button(text='Apply', icon='fa:filter')
    b1.set_event_handler('click', self._apply)
    bar.add_component(b1)
    b2 = Button(text='Export CSV', icon='fa:download', role='primary-color')
    b2.set_event_handler('click', self._export)
    bar.add_component(b2)
    self.content.add_component(bar)
    rows = self._report_rows()
    total = sum([r['commission'] for r in rows])
    tgmv = sum([r['gmv'] for r in rows])
    npaid = len([r for r in rows if r['status'] == 'Paid'])
    self.content.add_component(Label(text='%d invoice(s)  (%d paid / %d unpaid)   |   GMV THB %s   |   commission total THB %s' % (len(rows), npaid, len(rows) - npaid, '{:,.0f}'.format(tgmv), '{:,.0f}'.format(total)), bold=True, spacing_above='medium'))
    for r in rows:
      colour = {'Paid': OK_GREEN, 'Due': WARN_ORANGE, 'Overdue': BAD_RED}.get(r['status'])
      bgr = {'Paid': BG_PAID, 'Due': BG_DUE, 'Overdue': BG_OVERDUE}.get(r['status'])
      card = ColumnPanel(role='card', spacing_below='small', background=bgr)
      card.add_component(Label(text='%s  -  %s  -  GMV THB %s  -  commission THB %s' % (r['organizer'], r['period'], '{:,.0f}'.format(r['gmv']), '{:,.0f}'.format(r['commission'])), bold=True))
      card.add_component(Label(text='%s  -  issued %s' % (r['status'], r['issued_str']), foreground=colour))
      self.content.add_component(card)

  def _report_rows(self):
    rows = []
    for i in self.invoices:
      if self.rep_org != '(All organizers)' and i['organizer'] != self.rep_org:
        continue
      if self.rep_period != '(All periods)' and i['period'] != self.rep_period:
        continue
      rows.append(i)
    rows.sort(key=lambda r: (r['period'], r['organizer']))
    return rows

  def _apply(self, **e):
    self.rep_org = self.dd_org.selected_value
    self.rep_period = self.dd_period.selected_value
    self._show('Reports')

  def _csv_cell(self, v):
    s = str(v)
    if ',' in s or '"' in s:
      return '"' + s.replace('"', '""') + '"'
    return s

  def _download(self, lines, filename):
    media = anvil.BlobMedia('text/csv', '\r\n'.join(lines).encode('utf-8'), name=filename)
    anvil.media.download(media)

  def _export(self, **e):
    self.rep_org = self.dd_org.selected_value
    self.rep_period = self.dd_period.selected_value
    lines = ['Organizer,Period,GMV (THB),Commission (THB),Status,Issued']
    tg = 0
    tc = 0
    for r in self._report_rows():
      tg += r['gmv']
      tc += r['commission']
      lines.append(','.join([self._csv_cell(x) for x in [r['organizer'], r['period'], r['gmv'], r['commission'], r['status'], r['issued_str']]]))
    lines.append('')
    lines.append(','.join([self._csv_cell(x) for x in ['TOTAL', '', tg, tc, '', '']]))
    self._log('Exported commission report CSV')
    self._download(lines, 'commission_report.csv')

  def _export_orgs(self, **e):
    lines = ['Organizer,Plan,Commission rate %,Status,Events,Participants,GMV (THB),Commission due (THB)']
    for o in self.orgs:
      mine = self._events_of(o['name'])
      lines.append(','.join([self._csv_cell(x) for x in [o['name'], o['plan'], round(o['rate'] * 100), o['status'], len(mine), sum([e['participants'] for e in mine]), sum([e['gmv'] for e in mine]), self._due_of(o['name'])]]))
    self._log('Exported organizers CSV')
    self._download(lines, 'organizers.csv')

  def _audit_page(self):
    self.content.add_component(Label(text='Audit log', role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='Every action taken in this console, newest first', foreground='#6b6975', spacing_below='medium'))
    if not self.audit:
      self.content.add_component(Label(text='No actions recorded yet.', foreground='#6b6975'))
    for a in self.audit:
      card = ColumnPanel(role='card', spacing_below='small')
      card.add_component(Label(text=a['action'], bold=True))
      card.add_component(Label(text='%s  -  by %s' % (a['time'], a['user']), foreground='#6b6975'))
      self.content.add_component(card)

  def _settings_page(self):
    self.content.add_component(Label(text='Platform settings', role='headline', font_size=TITLE_SIZE, bold=True))
    self.content.add_component(Label(text='Commission rate charged on each plan. Changing a rate re-prices every organizer on that plan.', foreground='#6b6975', spacing_below='medium'))
    box = ColumnPanel(role='card')
    self.tb_rates = {}
    for plan in PLAN_NAMES:
      row = FlowPanel(align='left')
      row.add_component(Label(text='%s plan commission %%:' % plan))
      tb = TextBox(text='{:.0f}'.format(self.plans[plan] * 100))
      self.tb_rates[plan] = tb
      row.add_component(tb)
      n = len([o for o in self.orgs if o['plan'] == plan])
      row.add_component(Label(text='  (%d organizer(s) on this plan)' % n, foreground='#6b6975'))
      box.add_component(row)
    b = Button(text='Save rates', icon='fa:check', role='primary-color', spacing_above='small')
    b.set_event_handler('click', self._save_rates)
    box.add_component(b)
    self.content.add_component(box)
    info = ColumnPanel(role='card', spacing_above='medium')
    info.add_component(Label(text='How commission works', bold=True, font_size=16))
    info.add_component(Label(text='GMV = participants x ticket price', foreground='#6b6975'))
    info.add_component(Label(text='Commission = GMV x the organizer plan rate', foreground='#6b6975'))
    info.add_component(Label(text='Each month commission becomes one invoice per organizer.', foreground='#6b6975'))
    self.content.add_component(info)

  def _save_rates(self, **e):
    new = {}
    for plan in PLAN_NAMES:
      try:
        pct = float(self.tb_rates[plan].text)
      except Exception:
        Notification('Rates must be numbers.', style='warning').show()
        return
      if pct < 0 or pct > 50:
        Notification('Rate must be between 0 and 50 percent.', style='warning').show()
        return
      new[plan] = pct / 100.0
    self.plans = new
    self._log('Updated commission rates')
    Notification('Commission rates saved.', style='success').show()
    self._refresh('Settings')
