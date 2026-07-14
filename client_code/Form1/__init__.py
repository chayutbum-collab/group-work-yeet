# ======================================================================
#  Event Platform - Owner Console  v3   (SINGLE FILE)
#  Requires: one Column Panel named "column_panel_1" on the form.
#  Login ->  admin / admin123
#
#  PAGES: Login | Dashboard | Organizers | Organizer detail | Events
#         | Reports | Audit log
# ======================================================================
from ._anvil_designer import Form1Template
from anvil import *
from functools import partial
import anvil.media
import datetime

USERNAME = "admin"
PASSWORD = "admin123"

PLANS = {"Free": 0.08, "Pro": 0.05, "Business": 0.03}   # commission rate per plan
PLAN_NAMES = ["Free", "Pro", "Business"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
STATUSES = ["Approved", "Pending", "Flagged", "Featured"]

_ORGS = [
  ("Bangkok Runners Club", "Pro",      "Active"),
  ("MUIC Music Society",   "Free",     "Active"),
  ("TechConf Asia",        "Business", "Active"),
  ("Chiang Mai Food Fest", "Pro",      "Active"),
  ("Indie Game Meetup",    "Free",     "Suspended"),
]
_EVENTS = [
  ("E001", "Sunday Half Marathon", "Bangkok Runners Club", 4, 12, 320, 450),
  ("E002", "Night Trail 10K",      "Bangkok Runners Club", 5, 17, 210, 500),
  ("E003", "Riverside Fun Run",    "Bangkok Runners Club", 6, 14, 180, 350),
  ("E004", "Spring Recital",       "MUIC Music Society",   4, 26,  90, 200),
  ("E005", "Jazz Night",           "MUIC Music Society",   6,  6, 140, 250),
  ("E006", "Cloud & AI Summit",    "TechConf Asia",        5,  8, 640, 1800),
  ("E007", "DevOps Workshop",      "TechConf Asia",        6, 19, 120, 2500),
  ("E008", "Street Food Festival", "Chiang Mai Food Fest", 4,  5, 850, 150),
  ("E009", "Craft Beer & BBQ",     "Chiang Mai Food Fest", 5, 24, 430, 300),
  ("E010", "Northern Coffee Fair", "Chiang Mai Food Fest", 6, 21, 510, 180),
  ("E011", "Indie Showcase Vol.4", "Indie Game Meetup",    4, 30, 160, 120),
  ("E012", "Retro Arcade Night",   "Indie Game Meetup",    5, 29, 110, 150),
]


def _fmt(m, d):
  """Turn month+day into a readable date string, e.g. 12 Apr 2026."""
  return "%02d %s 2026" % (d, MONTHS[m - 1])


def _now():
  """Current time as a short string for the audit log."""
  n = datetime.datetime.now()
  return "%02d/%02d/%04d %02d:%02d" % (n.day, n.month, n.year, n.hour, n.minute)


class Form1(Form1Template):
  # ============================================================
  #  STARTUP
  # ============================================================
  def __init__(self, **properties):
    super().__init__(**properties)
    self._build_data()
    self.audit = []
    self.evt_filter = "(All statuses)"
    self.evt_search = ""
    self.evt_sort = "Date"
    self.show_add_evt = False
    self.org_search = ""
    self.org_sort = "GMV"
    self.show_add_org = False
    self.detail_org = None
    self.rep_org = "(All organizers)"
    self.rep_period = "(All periods)"
    self.root = self.column_panel_1
    self._show_login()

    # ============================================================
    #  DATA LAYER  (in-memory "database")
    # ============================================================
  def _build_data(self):
    """Build organizers, events and monthly invoices from the seed lists."""
    rate = {}
    self.orgs = []
    for name, plan, status in _ORGS:
      rate[name] = PLANS[plan]
      self.orgs.append({"name": name, "plan": plan, "rate": PLANS[plan], "status": status})

    self.events = []
    buckets = {}
    for ref, title, org, m, d, part, price in _EVENTS:
      gmv = part * price                       # gross merchandise value
      comm = int(round(gmv * rate[org]))       # platform commission
      self.events.append({"ref": ref, "title": title, "organizer": org, "month": m,
                          "day": d, "date_str": _fmt(m, d), "participants": part,
                          "price": price, "gmv": gmv, "commission": comm,
                          "status": "Approved"})
      b = buckets.setdefault((org, "2026-%02d" % m), [0, 0, m])
      b[0] += gmv
      b[1] += comm

    self.invoices = []
    for (org, period), (gmv, comm, m) in buckets.items():
      status = "Paid"
      if m == 6:
        status = "Due"
      if org == "Indie Game Meetup" and m == 5:
        status = "Overdue"
      self.invoices.append({"organizer": org, "period": period, "gmv": gmv,
                            "commission": comm, "status": status,
                            "issued_str": _fmt(m, 28)})

  def _log(self, action):
    """Record an action in the audit trail (newest first)."""
    self.audit.insert(0, {"time": _now(), "user": USERNAME, "action": action})

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
    return sum(i['commission'] for i in self._invoices_of(name)
               if i['status'] in ('Due', 'Overdue'))

  def _overdue_of(self, name):
    return sum(i['commission'] for i in self._invoices_of(name)
               if i['status'] == 'Overdue')

  def _next_ref(self):
    n = 1
    used = set(e['ref'] for e in self.events)
    while ("E%03d" % n) in used:
      n += 1
    return "E%03d" % n

  def _apply_to_invoice(self, org, m, gmv, comm):
    """Add (or subtract, if negative) an event's money on that month's bill."""
    period = "2026-%02d" % m
    for i in self.invoices:
      if i['organizer'] == org and i['period'] == period:
        i['gmv'] += gmv
        i['commission'] += comm
        if comm > 0 and i['status'] == 'Paid':
          i['status'] = 'Due'          # new charges -> becomes payable again
        if i['commission'] <= 0:
          self.invoices.remove(i)
        return
    if comm > 0:
      self.invoices.append({"organizer": org, "period": period, "gmv": gmv,
                            "commission": comm, "status": "Due",
                            "issued_str": _fmt(m, 28)})

    # ============================================================
    #  LOGIN
    # ============================================================
  def _show_login(self):
    self.root.clear()
    card = ColumnPanel(role='card')
    card.add_component(Label(text="Owner Console - Staff Login", role="headline"))
    card.add_component(Label(text="Platform staff only. This console holds every organizer's billing data.",
                             foreground="#6b6975", spacing_below="small"))
    self.tb_user = TextBox(placeholder="Username")
    self.tb_pass = TextBox(placeholder="Password", hide_text=True)
    self.tb_pass.set_event_handler('pressed_enter', self._do_login)
    card.add_component(self.tb_user)
    card.add_component(self.tb_pass)
    btn = Button(text="Log in", role="primary-color", spacing_above="small")
    btn.set_event_handler('click', self._do_login)
    card.add_component(btn)
    card.add_component(Label(text="Demo login  ->  username: admin   password: admin123",
                             foreground="#6b6975", spacing_above="small"))
    self.root.add_component(card)

  def _do_login(self, **e):
    if self.tb_user.text == USERNAME and self.tb_pass.text == PASSWORD:
      self._log("Logged in")
      self._build_console()
    else:
      Notification("Wrong username or password.", style="danger").show()

  def _logout(self, **e):
    self._log("Logged out")
    self._show_login()

  def _build_console(self):
    """Draw the permanent top navigation + the swappable content area."""
    self.root.clear()
    nav = FlowPanel(align="left", spacing_below="medium")
    for name in ["Dashboard", "Organizers", "Events", "Reports", "Audit log"]:
      link = Link(text=name)
      link.set_event_handler('click', partial(self._show, name))
      nav.add_component(link)
    out = Link(text="|  Log out")
    out.set_event_handler('click', self._logout)
    nav.add_component(out)
    self.root.add_component(nav)
    self.content = ColumnPanel()
    self.root.add_component(self.content)
    self._show("Dashboard")

  def _show(self, page, **e):
    """Router: clear the content area and draw the requested page."""
    self.content.clear()
    {"Dashboard": self._dashboard,
     "Organizers": self._organizers,
     "OrgDetail": self._org_detail,
     "Events": self._events,
     "Reports": self._reports,
     "Audit log": self._audit_page}[page]()

    # ============================================================
    #  PAGE 1 - DASHBOARD
    # ============================================================
  def _dashboard(self):
    self.content.add_component(Label(text="Event Platform - Owner Console", role="headline"))
    self.content.add_component(Label(text="Billing & commission across every organizer",
                                     foreground="#6b6975", spacing_below="medium"))

    overdue = [o for o in self.orgs if self._overdue_of(o['name']) > 0]
    if overdue:
      alert = ColumnPanel(role='card', spacing_below="medium")
      alert.add_component(Label(text="! Overdue invoices need attention",
                                bold=True, font_size=16, foreground="#b3372f"))
      for o in overdue:
        alert.add_component(Label(
          text="{}  -  overdue THB {:,.0f}  ({})".format(
            o['name'], self._overdue_of(o['name']), o['status']),
          foreground="#b3372f"))
      self.content.add_component(alert)

    gmv = sum(e['gmv'] for e in self.events)
    earned = sum(i['commission'] for i in self.invoices)
    collected = sum(i['commission'] for i in self.invoices if i['status'] == 'Paid')
    outstanding = sum(i['commission'] for i in self.invoices if i['status'] in ('Due', 'Overdue'))
    kpis = FlowPanel(align="left")
    for cap, val in [("Organizers", len(self.orgs)),
                     ("Active", sum(1 for o in self.orgs if o['status'] == 'Active')),
                     ("Events", len(self.events)),
                     ("Participants", sum(e['participants'] for e in self.events)),
                     ("GMV (THB)", gmv), ("Commission earned (THB)", earned),
                     ("Collected (THB)", collected), ("Outstanding (THB)", outstanding)]:
      card = ColumnPanel(role='card')
      card.add_component(Label(text="{:,}".format(val), font_size=22, bold=True))
      card.add_component(Label(text=cap, foreground="#6b6975"))
      kpis.add_component(card)
    self.content.add_component(kpis)

    by = {}
    for i in self.invoices:
      by[i['organizer']] = by.get(i['organizer'], 0) + i['commission']
    pairs = sorted(by.items(), key=lambda kv: kv[1], reverse=True)
    months = {}
    for i in self.invoices:
      months[i['period']] = months.get(i['period'], 0) + i['commission']
    mpairs = sorted(months.items())
    try:
      import plotly.graph_objs as go
      p1 = Plot()
      p1.data = [go.Bar(x=[k for k, v in pairs], y=[v for k, v in pairs],
                        marker={'color': '#5b45d4'})]
      p1.layout.height = 320
      p1.layout.title = "Commission earned by organizer (THB)"
      p1.layout.margin = {'t': 40, 'b': 120, 'l': 70, 'r': 20}
      self.content.add_component(p1)

      p2 = Plot()
      p2.data = [go.Scatter(x=[k for k, v in mpairs], y=[v for k, v in mpairs],
                            mode="lines+markers", line={'color': '#1a7f4b', 'width': 3})]
      p2.layout.height = 300
      p2.layout.title = "Monthly commission trend (THB)"
      p2.layout.margin = {'t': 40, 'b': 60, 'l': 70, 'r': 20}
      self.content.add_component(p2)
    except Exception:
      pass

    # ============================================================
    #  PAGE 2 - ORGANIZERS  (search / sort / CRUD / billing)
    # ============================================================
  def _organizers(self):
    self.content.add_component(Label(text="Organizers", role="headline"))
    self.content.add_component(Label(text="Search, sort, edit plans, collect commission",
                                     foreground="#6b6975"))
    bar = FlowPanel(align="left", spacing_below="medium")
    bar.add_component(Label(text="Search:"))
    self.tb_org = TextBox(text=self.org_search, placeholder="organizer name")
    self.tb_org.set_event_handler('pressed_enter', self._org_search_go)
    bar.add_component(self.tb_org)
    b = Button(text="Go")
    b.set_event_handler('click', self._org_search_go)
    bar.add_component(b)
    bar.add_component(Label(text="  Sort by:"))
    dd = DropDown(items=["GMV", "Commission due", "Name"], selected_value=self.org_sort)
    dd.set_event_handler('change', self._org_sort_changed)
    bar.add_component(dd)
    badd = Button(text="+ Add organizer", role="primary-color")
    badd.set_event_handler('click', self._toggle_add_org)
    bar.add_component(badd)
    bcsv = Button(text="Export organizers CSV")
    bcsv.set_event_handler('click', self._export_orgs)
    bar.add_component(bcsv)
    self.content.add_component(bar)

    if self.show_add_org:
      box = ColumnPanel(role='card', spacing_below="medium")
      box.add_component(Label(text="New organizer", bold=True, font_size=16))
      self.tb_new_name = TextBox(placeholder="Organizer name")
      box.add_component(self.tb_new_name)
      row = FlowPanel(align="left")
      row.add_component(Label(text="Plan:"))
      self.dd_new_plan = DropDown(items=PLAN_NAMES, selected_value="Pro")
      row.add_component(self.dd_new_plan)
      s = Button(text="Save", role="primary-color")
      s.set_event_handler('click', self._save_new_org)
      row.add_component(s)
      c = Button(text="Cancel")
      c.set_event_handler('click', self._toggle_add_org)
      row.add_component(c)
      box.add_component(row)
      self.content.add_component(box)

    rows = [o for o in self.orgs if self.org_search.lower() in o['name'].lower()]
    if self.org_sort == "GMV":
      rows.sort(key=lambda o: sum(e['gmv'] for e in self._events_of(o['name'])), reverse=True)
    elif self.org_sort == "Commission due":
      rows.sort(key=lambda o: self._due_of(o['name']), reverse=True)
    else:
      rows.sort(key=lambda o: o['name'])

    if not rows:
      self.content.add_component(Label(text="No organizer matches that search.",
                                       foreground="#6b6975"))
    for o in rows:
      self.content.add_component(self._org_card(o))

  def _org_card(self, o):
    mine = self._events_of(o['name'])
    due = self._due_of(o['name'])
    od = self._overdue_of(o['name'])
    card = ColumnPanel(role='card', spacing_below="small")
    card.add_component(Label(
      text="{}   -   {} plan ({:.0f}% commission)".format(o['name'], o['plan'], o['rate'] * 100),
      bold=True, font_size=16))
    if od > 0:
      card.add_component(Label(text="! OVERDUE THB {:,.0f}".format(od),
                               bold=True, foreground="#b3372f"))
    card.add_component(Label(
      text="{} events  -  {:,} participants  -  GMV THB {:,.0f}  -  commission due THB {:,.0f}".format(
        len(mine), sum(e['participants'] for e in mine),
        sum(e['gmv'] for e in mine), due), foreground="#6b6975"))
    row = FlowPanel(align="left")
    row.add_component(Label(text="Status: " + o['status'], bold=True,
                            foreground=("#1a7f4b" if o['status'] == 'Active' else "#b3372f")))
    row.add_component(Label(text="  Plan:"))
    ddp = DropDown(items=PLAN_NAMES, selected_value=o['plan'])
    ddp.set_event_handler('change', partial(self._change_plan, o))
    row.add_component(ddp)
    bview = Button(text="View")
    bview.set_event_handler('click', partial(self._open_detail, o['name']))
    row.add_component(bview)
    b1 = Button(text=("Suspend" if o['status'] == 'Active' else "Activate"),
                role="secondary-color")
    b1.set_event_handler('click', partial(self._toggle, o))
    row.add_component(b1)
    b2 = Button(text="Mark commission paid", role="primary-color")
    b2.set_event_handler('click', partial(self._paid, o['name']))
    row.add_component(b2)
    b3 = Button(text="Delete")
    b3.set_event_handler('click', partial(self._delete_org, o))
    row.add_component(b3)
    card.add_component(row)
    return card

  def _org_search_go(self, **e):
    self.org_search = self.tb_org.text or ""
    self._show("Organizers")

  def _org_sort_changed(self, **e):
    self.org_sort = e['sender'].selected_value
    self._show("Organizers")

  def _toggle_add_org(self, **e):
    self.show_add_org = not self.show_add_org
    self._show("Organizers")

  def _save_new_org(self, **e):
    name = (self.tb_new_name.text or "").strip()
    if not name:
      Notification("Please type an organizer name.", style="warning").show()
      return
    if any(o['name'].lower() == name.lower() for o in self.orgs):
      Notification("That organizer already exists.", style="warning").show()
      return
    plan = self.dd_new_plan.selected_value
    self.orgs.append({"name": name, "plan": plan, "rate": PLANS[plan], "status": "Active"})
    self.show_add_org = False
    self._log("Added organizer '%s' on the %s plan" % (name, plan))
    Notification("Added organizer '%s'." % name, style="success").show()
    self._show("Organizers")

  def _delete_org(self, o, **e):
    if not confirm("Delete '%s' and all of its events and invoices?" % o['name']):
      return
    self.events = [x for x in self.events if x['organizer'] != o['name']]
    self.invoices = [x for x in self.invoices if x['organizer'] != o['name']]
    self.orgs.remove(o)
    self._log("Deleted organizer '%s'" % o['name'])
    Notification("Deleted '%s'." % o['name'], style="success").show()
    self._show("Organizers")

  def _change_plan(self, o, **e):
    plan = e['sender'].selected_value
    old = o['plan']
    o['plan'] = plan
    o['rate'] = PLANS[plan]
    self._log("Changed %s plan: %s -> %s (%.0f%% commission)" % (o['name'], old, plan, o['rate'] * 100))
    Notification("%s is now on the %s plan." % (o['name'], plan), style="success").show()
    self._show("Organizers")

  def _toggle(self, o, **e):
    o['status'] = "Suspended" if o['status'] == 'Active' else "Active"
    self._log("Set %s to %s" % (o['name'], o['status']))
    self._show("Organizers")

  def _paid(self, name, **e):
    n = 0
    for i in self.invoices:
      if i['organizer'] == name and i['status'] in ('Due', 'Overdue'):
        i['status'] = 'Paid'
        n += 1
    self._log("Marked %d invoice(s) paid for %s" % (n, name))
    Notification("Marked %d invoice(s) paid for %s." % (n, name), style="success").show()
    self._show("Organizers")

  def _open_detail(self, name, **e):
    self.detail_org = name
    self._show("OrgDetail")

    # ============================================================
    #  PAGE 3 - ORGANIZER DETAIL (drill-down)
    # ============================================================
  def _org_detail(self):
    org = None
    for o in self.orgs:
      if o['name'] == self.detail_org:
        org = o
    if org is None:
      self._show("Organizers")
      return
    back = Link(text="< Back to organizers")
    back.set_event_handler('click', partial(self._show, "Organizers"))
    self.content.add_component(back)
    self.content.add_component(Label(text=org['name'], role="headline"))
    self.content.add_component(Label(
      text="{} plan  -  {:.0f}% commission  -  {}".format(
        org['plan'], org['rate'] * 100, org['status']),
      foreground="#6b6975", spacing_below="medium"))

    mine = self._events_of(org['name'])
    kpis = FlowPanel(align="left")
    for cap, val in [("Events", len(mine)),
                     ("Participants", sum(e['participants'] for e in mine)),
                     ("GMV (THB)", sum(e['gmv'] for e in mine)),
                     ("Commission due (THB)", self._due_of(org['name']))]:
      c = ColumnPanel(role='card')
      c.add_component(Label(text="{:,}".format(val), font_size=22, bold=True))
      c.add_component(Label(text=cap, foreground="#6b6975"))
      kpis.add_component(c)
    self.content.add_component(kpis)

    self.content.add_component(Label(text="Events", bold=True, font_size=16,
                                     spacing_above="medium"))
    if not mine:
      self.content.add_component(Label(text="No events yet.", foreground="#6b6975"))
    for ev in sorted(mine, key=lambda e: (e['month'], e['ref'])):
      c = ColumnPanel(role='card', spacing_below="small")
      c.add_component(Label(text="{} ({})".format(ev['title'], ev['ref']), bold=True))
      c.add_component(Label(
        text="{}  -  {:,} participants  -  GMV THB {:,.0f}  -  commission THB {:,.0f}  -  {}".format(
          ev['date_str'], ev['participants'], ev['gmv'], ev['commission'], ev['status']),
        foreground="#6b6975"))
      self.content.add_component(c)

    self.content.add_component(Label(text="Invoices", bold=True, font_size=16,
                                     spacing_above="medium"))
    inv = self._invoices_of(org['name'])
    if not inv:
      self.content.add_component(Label(text="No invoices yet.", foreground="#6b6975"))
    for i in sorted(inv, key=lambda i: i['period']):
      colour = {'Paid': '#1a7f4b', 'Due': '#c2620a', 'Overdue': '#b3372f'}.get(i['status'])
      c = ColumnPanel(role='card', spacing_below="small")
      c.add_component(Label(text="{}  -  commission THB {:,.0f}".format(
        i['period'], i['commission']), bold=True))
      c.add_component(Label(text="{}  -  issued {}".format(i['status'], i['issued_str']),
                            foreground=colour))
      self.content.add_component(c)

    # ============================================================
    #  PAGE 4 - EVENTS  (search / filter / sort / add / delete)
    # ============================================================
  def _events(self):
    self.content.add_component(Label(text="Events oversight", role="headline"))
    self.content.add_component(Label(text="Every event across all organizers",
                                     foreground="#6b6975"))
    bar = FlowPanel(align="left", spacing_below="medium")
    bar.add_component(Label(text="Search:"))
    self.tb_evt = TextBox(text=self.evt_search, placeholder="event or organizer")
    self.tb_evt.set_event_handler('pressed_enter', self._evt_search_go)
    bar.add_component(self.tb_evt)
    b = Button(text="Go")
    b.set_event_handler('click', self._evt_search_go)
    bar.add_component(b)
    bar.add_component(Label(text="  Status:"))
    dd = DropDown(items=["(All statuses)"] + STATUSES, selected_value=self.evt_filter)
    dd.set_event_handler('change', self._evt_filter_changed)
    bar.add_component(dd)
    bar.add_component(Label(text="  Sort:"))
    dds = DropDown(items=["Date", "GMV", "Commission"], selected_value=self.evt_sort)
    dds.set_event_handler('change', self._evt_sort_changed)
    bar.add_component(dds)
    badd = Button(text="+ Add event", role="primary-color")
    badd.set_event_handler('click', self._toggle_add_evt)
    bar.add_component(badd)
    self.content.add_component(bar)

    if self.show_add_evt:
      self.content.add_component(self._add_event_form())

    q = self.evt_search.lower()
    rows = [e for e in self.events
            if (self.evt_filter == "(All statuses)" or e['status'] == self.evt_filter)
            and (q in e['title'].lower() or q in e['organizer'].lower())]
    if self.evt_sort == "GMV":
      rows.sort(key=lambda e: e['gmv'], reverse=True)
    elif self.evt_sort == "Commission":
      rows.sort(key=lambda e: e['commission'], reverse=True)
    else:
      rows.sort(key=lambda e: (e['month'], e['ref']))

    if not rows:
      self.content.add_component(Label(text="No event matches that filter.",
                                       foreground="#6b6975"))
    for ev in rows:
      self.content.add_component(self._event_card(ev))

  def _add_event_form(self):
    box = ColumnPanel(role='card', spacing_below="medium")
    box.add_component(Label(text="New event", bold=True, font_size=16))
    self.tb_ev_title = TextBox(placeholder="Event title")
    box.add_component(self.tb_ev_title)
    r1 = FlowPanel(align="left")
    r1.add_component(Label(text="Organizer:"))
    self.dd_ev_org = DropDown(items=sorted(o['name'] for o in self.orgs))
    r1.add_component(self.dd_ev_org)
    r1.add_component(Label(text="Month:"))
    self.dd_ev_month = DropDown(items=["Apr", "May", "Jun"], selected_value="Jun")
    r1.add_component(self.dd_ev_month)
    r1.add_component(Label(text="Day:"))
    self.tb_ev_day = TextBox(text="15")
    r1.add_component(self.tb_ev_day)
    box.add_component(r1)
    r2 = FlowPanel(align="left")
    r2.add_component(Label(text="Participants:"))
    self.tb_ev_part = TextBox(text="100")
    r2.add_component(self.tb_ev_part)
    r2.add_component(Label(text="Ticket price (THB):"))
    self.tb_ev_price = TextBox(text="300")
    r2.add_component(self.tb_ev_price)
    s = Button(text="Save", role="primary-color")
    s.set_event_handler('click', self._save_new_event)
    r2.add_component(s)
    c = Button(text="Cancel")
    c.set_event_handler('click', self._toggle_add_evt)
    r2.add_component(c)
    box.add_component(r2)
    return box

  def _event_card(self, ev):
    card = ColumnPanel(role='card', spacing_below="small")
    card.add_component(Label(text="{}  ({})".format(ev['title'], ev['ref']),
                             bold=True, font_size=16))
    card.add_component(Label(
      text="{}  -  {}  -  {:,} participants  -  GMV THB {:,.0f}  -  commission THB {:,.0f}".format(
        ev['organizer'], ev['date_str'], ev['participants'], ev['gmv'], ev['commission']),
      foreground="#6b6975"))
    row = FlowPanel(align="left")
    row.add_component(Label(text="Status:"))
    sd = DropDown(items=STATUSES, selected_value=ev['status'])
    sd.set_event_handler('change', partial(self._set_status, ev))
    row.add_component(sd)
    bdel = Button(text="Delete")
    bdel.set_event_handler('click', partial(self._delete_event, ev))
    row.add_component(bdel)
    card.add_component(row)
    return card

  def _toggle_add_evt(self, **e):
    self.show_add_evt = not self.show_add_evt
    self._show("Events")

  def _save_new_event(self, **e):
    title = (self.tb_ev_title.text or "").strip()
    if not title:
      Notification("Please type an event title.", style="warning").show()
      return
    try:
      day = int(self.tb_ev_day.text)
      part = int(self.tb_ev_part.text)
      price = int(self.tb_ev_price.text)
    except Exception:
      Notification("Day, participants and price must be numbers.", style="warning").show()
      return
    org = self.dd_ev_org.selected_value
    if not org:
      Notification("Add an organizer first.", style="warning").show()
      return
    m = {"Apr": 4, "May": 5, "Jun": 6}[self.dd_ev_month.selected_value]
    gmv = part * price
    comm = int(round(gmv * self._rate_of(org)))
    ref = self._next_ref()
    self.events.append({"ref": ref, "title": title, "organizer": org, "month": m,
                        "day": day, "date_str": _fmt(m, day), "participants": part,
                        "price": price, "gmv": gmv, "commission": comm,
                        "status": "Pending"})
    self._apply_to_invoice(org, m, gmv, comm)
    self.show_add_evt = False
    self._log("Added event '%s' (%s) for %s - commission THB %d" % (title, ref, org, comm))
    Notification("Added event '%s'." % title, style="success").show()
    self._show("Events")

  def _delete_event(self, ev, **e):
    if not confirm("Delete event '%s'?" % ev['title']):
      return
    self._apply_to_invoice(ev['organizer'], ev['month'], -ev['gmv'], -ev['commission'])
    self.events.remove(ev)
    self._log("Deleted event '%s' (%s)" % (ev['title'], ev['ref']))
    Notification("Deleted '%s'." % ev['title'], style="success").show()
    self._show("Events")

  def _evt_search_go(self, **e):
    self.evt_search = self.tb_evt.text or ""
    self._show("Events")

  def _evt_filter_changed(self, **e):
    self.evt_filter = e['sender'].selected_value
    self._show("Events")

  def _evt_sort_changed(self, **e):
    self.evt_sort = e['sender'].selected_value
    self._show("Events")

  def _set_status(self, ev, **e):
    ev['status'] = e['sender'].selected_value
    self._log("Set event %s to %s" % (ev['ref'], ev['status']))
    Notification("%s set to %s." % (ev['ref'], ev['status']), style="success").show()

    # ============================================================
    #  PAGE 5 - REPORTS & EXPORT
    # ============================================================
  def _reports(self):
    self.content.add_component(Label(text="Reports & data export", role="headline"))
    self.content.add_component(Label(text="Commission billing records - filter and export as CSV",
                                     foreground="#6b6975"))
    names = sorted(set(o['name'] for o in self.orgs))
    periods = sorted(set(i['period'] for i in self.invoices))
    bar = FlowPanel(align="left")
    bar.add_component(Label(text="Organizer:"))
    self.dd_org = DropDown(items=["(All organizers)"] + names, selected_value=self.rep_org)
    bar.add_component(self.dd_org)
    bar.add_component(Label(text="Period:"))
    self.dd_period = DropDown(items=["(All periods)"] + periods, selected_value=self.rep_period)
    bar.add_component(self.dd_period)
    b1 = Button(text="Apply")
    b1.set_event_handler('click', self._apply)
    bar.add_component(b1)
    b2 = Button(text="Export CSV", role="primary-color")
    b2.set_event_handler('click', self._export)
    bar.add_component(b2)
    self.content.add_component(bar)

    rows = self._report_rows()
    total = sum(r['commission'] for r in rows)
    self.content.add_component(Label(
      text="{} invoice(s)   -   commission total THB {:,.0f}".format(len(rows), total),
      bold=True, spacing_above="medium"))
    for r in rows:
      colour = {'Paid': '#1a7f4b', 'Due': '#c2620a', 'Overdue': '#b3372f'}.get(r['status'])
      card = ColumnPanel(role='card', spacing_below="small")
      card.add_component(Label(text="{}  -  {}  -  GMV THB {:,.0f}  -  commission THB {:,.0f}".format(
        r['organizer'], r['period'], r['gmv'], r['commission']), bold=True))
      card.add_component(Label(text="{}  -  issued {}".format(r['status'], r['issued_str']),
                               foreground=colour))
      self.content.add_component(card)

  def _report_rows(self):
    rows = []
    for i in self.invoices:
      if self.rep_org != "(All organizers)" and i['organizer'] != self.rep_org:
        continue
      if self.rep_period != "(All periods)" and i['period'] != self.rep_period:
        continue
      rows.append(i)
    rows.sort(key=lambda r: (r['period'], r['organizer']))
    return rows

  def _apply(self, **e):
    self.rep_org = self.dd_org.selected_value
    self.rep_period = self.dd_period.selected_value
    self._show("Reports")

  def _csv_cell(self, v):
    s = str(v)
    if any(c in s for c in (',', '"', '\n')):
      return '"' + s.replace('"', '""') + '"'
    return s

  def _download(self, lines, filename):
    media = anvil.BlobMedia("text/csv", "\r\n".join(lines).encode("utf-8"), name=filename)
    anvil.media.download(media)

  def _export(self, **e):
    self.rep_org = self.dd_org.selected_value
    self.rep_period = self.dd_period.selected_value
    lines = ["Organizer,Period,GMV (THB),Commission (THB),Status,Issued"]
    tg = tc = 0
    for r in self._report_rows():
      tg += r['gmv']
      tc += r['commission']
      lines.append(",".join(self._csv_cell(x) for x in
                            [r['organizer'], r['period'], r['gmv'], r['commission'],
                             r['status'], r['issued_str']]))
    lines.append("")
    lines.append(",".join(self._csv_cell(x) for x in ["TOTAL", "", tg, tc, "", ""]))
    self._log("Exported commission report CSV")
    self._download(lines, "commission_report.csv")

  def _export_orgs(self, **e):
    lines = ["Organizer,Plan,Commission rate %,Status,Events,Participants,GMV (THB),Commission due (THB)"]
    for o in self.orgs:
      mine = self._events_of(o['name'])
      lines.append(",".join(self._csv_cell(x) for x in
                            [o['name'], o['plan'], round(o['rate'] * 100), o['status'], len(mine),
                             sum(e['participants'] for e in mine),
                             sum(e['gmv'] for e in mine), self._due_of(o['name'])]))
    self._log("Exported organizers CSV")
    self._download(lines, "organizers.csv")

    # ============================================================
    #  PAGE 6 - AUDIT LOG
    # ============================================================
  def _audit_page(self):
    self.content.add_component(Label(text="Audit log", role="headline"))
    self.content.add_component(Label(
      text="Every action taken in this console, newest first (accountability trail)",
      foreground="#6b6975", spacing_below="medium"))
    if not self.audit:
      self.content.add_component(Label(text="No actions recorded yet.", foreground="#6b6975"))
    for a in self.audit:
      card = ColumnPanel(role='card', spacing_below="small")
      card.add_component(Label(text=a['action'], bold=True))
      card.add_component(Label(text="{}  -  by {}".format(a['time'], a['user']),
                               foreground="#6b6975"))
      self.content.add_component(card)