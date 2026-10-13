"""Make realistic records from a compact spec, so a model describes demo data and the server writes it."""

from __future__ import annotations

import random
import re
import unicodedata
import zlib
from datetime import date, datetime, timedelta
from typing import Any

import frappe
from frappe.model import no_value_fields, table_fields
from frappe.utils import add_days, cint, flt, getdate, nowdate

MAX_COUNT = 2000
TRIES = 50

INDIA = {  # region: (men, women, surnames), weight
	"hindi": (
		("Rahul", "Abhishek", "Manish", "Vikram", "Aarav", "Ankit", "Saurabh", "Gaurav", "Rohit", "Amit", "Varun", "Kunal"),
		("Neha", "Priya", "Shreya", "Ritu", "Anjali", "Divya", "Kavita", "Swati", "Nidhi", "Ananya", "Pooja", "Isha"),
		("Sharma", "Gupta", "Agarwal", "Jain", "Verma", "Mishra", "Srivastava", "Tiwari", "Saxena", "Chauhan", "Yadav", "Pandey"),
		20,
	),
	"marathi": (
		("Rohan", "Siddharth", "Omkar", "Swapnil", "Aditya", "Sagar", "Prathamesh", "Tushar", "Nikhil", "Amol", "Vinayak", "Aniket"),
		("Sneha", "Pooja", "Tanvi", "Rupali", "Shruti", "Ashwini", "Prajakta", "Sayali", "Madhura", "Gauri", "Mrunal", "Ketaki"),
		("Kulkarni", "Deshpande", "Joshi", "Bhosale", "Pawar", "Patil", "Jadhav", "Gokhale", "Apte", "Shinde", "Kale", "Deshmukh"),
		14,
	),
	"gujarati": (
		("Harsh", "Jay", "Parth", "Hardik", "Chirag", "Nirav", "Ketan", "Dhaval", "Kunal", "Jignesh"),
		("Bhavna", "Krupa", "Hetal", "Disha", "Riddhi", "Nidhi", "Khushi", "Foram", "Mansi", "Dhara"),
		("Patel", "Shah", "Mehta", "Desai", "Trivedi", "Parikh", "Modi", "Thakkar", "Dave", "Vyas"),
		9,
	),
	"punjabi": (
		("Harpreet", "Gurpreet", "Jaspreet", "Manpreet", "Amandeep", "Karan", "Arjun", "Harjot", "Navdeep"),
		("Simran", "Gurleen", "Navneet", "Jasleen", "Harleen", "Manpreet", "Kirandeep", "Rupinder"),
		("Singh", "Gill", "Sandhu", "Dhillon", "Sidhu", "Grewal", "Bedi", "Ahluwalia", "Kaur"),
		6,
	),
	"bengali": (
		("Arijit", "Sourav", "Debashish", "Anirban", "Subhajit", "Rajarshi", "Sayan", "Arnab", "Indranil"),
		("Ananya", "Moumita", "Priyanka", "Sreeja", "Rituparna", "Payel", "Tanushree", "Debolina", "Sohini"),
		("Banerjee", "Chatterjee", "Mukherjee", "Das", "Ghosh", "Bose", "Sen", "Roy", "Dutta", "Bhattacharya"),
		8,
	),
	"tamil": (
		("Karthik", "Venkatesh", "Senthil", "Arun", "Prakash", "Vignesh", "Saravanan", "Ramesh", "Hari", "Gokul"),
		("Lakshmi", "Divya", "Deepika", "Priya", "Kavya", "Meenakshi", "Janani", "Revathi", "Nithya", "Sangeetha"),
		("Iyer", "Iyengar", "Subramanian", "Krishnan", "Raman", "Natarajan", "Sundaram", "Rajan", "Balaji", "Murugan"),
		9,
	),
	"telugu": (
		("Sai", "Venkat", "Srinivas", "Ravi", "Kiran", "Praveen", "Naveen", "Chaitanya", "Mahesh", "Teja"),
		("Lakshmi", "Sravani", "Keerthi", "Swathi", "Anusha", "Divya", "Harika", "Bhavya", "Sirisha", "Mounika"),
		("Reddy", "Rao", "Naidu", "Chowdary", "Varma", "Raju", "Prasad", "Kumar", "Goud"),
		9,
	),
	"kannada": (
		("Vinay", "Prashanth", "Manjunath", "Sudeep", "Raghav", "Chetan", "Darshan", "Pradeep"),
		("Kavya", "Shwetha", "Pallavi", "Rashmi", "Apoorva", "Sahana", "Bhoomika", "Spoorthi"),
		("Hegde", "Shetty", "Bhat", "Rao", "Gowda", "Kamath", "Pai", "Acharya"),
		7,
	),
	"malayali": (
		("Arjun", "Vishnu", "Anoop", "Sreejith", "Rahul", "Nikhil", "Akhil", "Jithin", "Sanjay"),
		("Meera", "Anjali", "Lakshmi", "Aparna", "Divya", "Athira", "Reshma", "Gayathri", "Nimisha"),
		("Nair", "Menon", "Pillai", "Kurup", "Panicker", "Warrier", "Namboothiri", "Varghese", "Kurian"),
		7,
	),
	"muslim": (
		("Imran", "Farhan", "Arshad", "Salman", "Faizan", "Aamir", "Zaid", "Sameer", "Irfan", "Asif"),
		("Fatima", "Zoya", "Ayesha", "Sana", "Nazia", "Rukhsar", "Mehreen", "Sara", "Heena", "Afreen"),
		("Khan", "Shaikh", "Qureshi", "Ansari", "Siddiqui", "Syed", "Pathan", "Mirza", "Momin"),
		7,
	),
	"christian": (
		("Joseph", "Aaron", "Neil", "Clinton", "Joel", "Savio", "Glen", "Ryan"),
		("Maria", "Sharon", "Rachel", "Anita", "Sonia", "Joanne", "Natasha", "Lynette"),
		("D'Souza", "Fernandes", "Pereira", "Rodrigues", "Pinto", "Lobo", "Mathew", "Thomas", "George"),
		3,
	),
	"himalayan": (
		("Tenzin", "Karma", "Sonam", "Rinchen", "Pema", "Dorjee"),
		("Tenzin", "Pema", "Dolma", "Sonam", "Yangchen", "Diki"),
		("Bhutia", "Lepcha", "Gurung", "Tamang", "Sherpa", "Negi"),
		1,
	),
}
ABROAD = {  # faker locale: country, weight
	"en_US": ("United States", 4),
	"en_GB": ("United Kingdom", 2),
	"de_DE": ("Germany", 2),
	"nl_NL": ("Netherlands", 1),
	"fr_FR": ("France", 1),
	"es_ES": ("Spain", 1),
	"it_IT": ("Italy", 1),
	"pt_BR": ("Brazil", 2),
	"id_ID": ("Indonesia", 2),
	"en_KE": ("Kenya", 2),
	"en_NG": ("Nigeria", 1),
}
COMPANY_WORDS = (
	(
		"Konkan", "Saffron", "Deccan", "Nilgiri", "Monsoon", "Lotus", "Ashoka", "Sahyadri", "Ganga", "Kaveri",
		"Bluewater", "Arambh", "Udaan", "Pragati", "Indus", "Malabar", "Vasant", "Navrang", "Annapurna",
		"Himalaya", "Rangoli", "Sunrise", "Aravali", "Narmada", "Godavari", "Shivalik", "Chola", "Satpura",
		"Kesari", "Banyan", "Peacock", "Tapti", "Vindhya", "Sindhu", "Ajanta",
	),
	(
		"Cloud", "Ledger", "Software", "Code", "ERP", "Tech", "Digital", "Apps", "Data", "Logic", "Infotech",
		"Textiles", "Foods", "Pharma", "Logistics", "Exports", "Auto Components", "Organics", "Steel", "Plastics",
	),
	("Labs", "Works", "Solutions", "Consulting", "Partners", "Pvt Ltd", "Technologies", "Industries", "Systems", ""),
)
FREE_MAIL = {"gmail.com": 8, "outlook.com": 1, "yahoo.com": 1}
SKEWS = {"rising": 2, "falling": -2, "flat": 0}
PERSON_ATTRS = {"first_name", "last_name", "full_name", "country", "he", "He", "his", "His", "him", "Him"}
FAKER_BLOCKED = {"seed", "seed_instance", "seed_locale", "add_provider", "format", "parse", "provider"}

COMMON_PARAMS = {"kind", "empty", "unique"}
KINDS: dict[str, set[str]] = {
	"name": {"india", "women"},
	"first_name": {"india", "women"},
	"last_name": {"india", "women"},
	"company": {"names", "pool"},
	"email": {"company", "domain", "free"},
	"phone": {"prefix", "digits", "first"},
	"date": {"from", "to", "ranges", "skew", "weekdays"},
	"datetime": {"from", "to", "ranges", "skew", "weekdays", "times"},
	"int": {"min", "max", "skew"},
	"float": {"min", "max", "skew", "precision"},
	"choice": {"options", "pick"},
	"link": {"filters", "weights", "distribution", "unique", "each"},
	"text": {"template", "templates", "slots", "start", "words"},
	"constant": {"value"},
	"fake": {"method", "locale", "args"},
	"table": {"rows", "fields"},
}
PERSON_KINDS = {"name", "first_name", "last_name"}
PLACEHOLDER = re.compile(r"\{([^{}]+)\}")


class SpecError(ValueError):
	pass


class Bag:
	"""Draws from weighted outcomes. Given the number of draws, it hands out exactly the rounded
	share of each outcome, in random order, so a spec's proportions hold at any count."""

	def __init__(self, rng: random.Random, outcomes: list, weights: list[float], draws: int | None):
		self.rng, self.outcomes, self.weights = rng, outcomes, weights
		self.queue: list = []
		total = sum(weights)
		if draws and total > 0:
			exact = [w * draws / total for w in weights]
			counts = [int(x) for x in exact]
			by_remainder = sorted(range(len(exact)), key=lambda i: exact[i] - counts[i], reverse=True)
			for i in by_remainder[: draws - sum(counts)]:
				counts[i] += 1
			self.queue = [o for o, c in zip(outcomes, counts) for _ in range(c)]
			rng.shuffle(self.queue)

	def draw(self):
		if self.queue:
			return self.queue.pop()
		return self.rng.choices(self.outcomes, self.weights)[0]


def weighted(value: Any) -> tuple[list, list[float]]:
	"""A list (equal weights) or a {value: weight} dict as outcomes and weights."""
	if isinstance(value, dict):
		return list(value.keys()), [flt(w) for w in value.values()]
	return list(value), [1.0] * len(value)


def skewed(rng: random.Random, skew: float) -> float:
	"""A point in [0, 1) whose density grows as t**skew, toward 1 for a positive skew, toward 0 for a negative one."""
	u = rng.random()
	if skew > 0:
		return u ** (1 / (1 + skew))
	if skew < 0:
		return 1 - (1 - u) ** (1 / (1 - skew))
	return u


def parse_day(value: Any) -> date:
	text = str(value).strip().lower()
	if text == "today":
		return getdate(nowdate())
	if m := re.fullmatch(r"([+-]\d+)d", text):
		return getdate(add_days(nowdate(), int(m.group(1))))
	return getdate(str(value)[:10])


def parse_minutes(value: str) -> int:
	hours, minutes = str(value).split(":")[:2]
	return int(hours) * 60 + int(minutes)


def ascii_slug(text: str) -> str:
	return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower())


def company_domain(company: str) -> str:
	slug = ascii_slug(re.sub(r"\b(pvt|ltd|private|limited|llp|inc)\b\.?", "", company, flags=re.I)) or "example"
	return f"{slug}.{'in' if zlib.crc32(slug.encode()) % 2 else 'com'}"


class Person:
	def __init__(self, first: str, last: str, woman: bool, country: str):
		self.first_name, self.last_name, self.country = first, last, country
		self.full_name = f"{first} {last}"
		self.he, self.He = ("she", "She") if woman else ("he", "He")
		self.his, self.His = ("her", "Her") if woman else ("his", "His")
		self.him, self.Him = ("her", "Her") if woman else ("him", "Him")


class Generator:
	def __init__(
		self, doctype: str, count: int, fields: dict[str, Any], seed: int | None = None, given: list[dict] | None = None
	):
		self.doctype, self.count = doctype, count
		self.rng = random.Random(seed)
		self.meta = frappe.get_meta(doctype)
		self.fakers: dict[str, Any] = {}
		self.emails_taken: set[str] = set()
		self.link_values: dict[tuple[str, str], dict] = {}
		self.errors: list[str] = []
		self.read: set[str] = set()
		if not 1 <= count <= MAX_COUNT:
			self.errors.append(f"count must be 1 to {MAX_COUNT}; split larger sets into several calls")
		self.given = self.compile_given(given)
		self.given_keys = {key for row in self.given for key in row}
		self.specs = self.compile(self.meta, fields, "", count)
		self.check_required(self.meta, self.specs, "")
		for key in sorted(self.given_keys - set(value_fields(self.meta)) - self.read):
			self.errors.append(f"given {key} is not a field of {doctype}, and no template reads it")
		if self.errors:
			raise SpecError("Fix the spec: " + "; ".join(self.errors))
		self.person_spec = next(
			(s for s in self.walk(self.specs) if s["kind"] in PERSON_KINDS), {"kind": "name", "india": 1}
		)
		# a given name is the record's person, so its email and pronouns follow it
		self.person_fields = {f: s["kind"] for f, s in self.specs.items() if s["kind"] in PERSON_KINDS} or (
			{self.meta.title_field: "name"} if self.meta.title_field else {}
		)
		self.persons_taken: set[str] = set()
		self.persons_unique = False
		for spec in self.walk(self.specs):
			if spec["kind"] in PERSON_KINDS and spec.get("unique"):
				self.persons_taken |= spec["taken"]
				self.persons_unique = True
		self.india = Bag(self.rng, [True, False], [self.person_spec.get("india", 1), 1 - self.person_spec.get("india", 1)], count)
		women = self.person_spec.get("women", 0.5)
		self.women = Bag(self.rng, [True, False], [women, 1 - women], count)
		regions = list(INDIA)
		self.regions = Bag(self.rng, regions, [INDIA[r][3] for r in regions], None)
		locales = list(ABROAD)
		self.locales = Bag(self.rng, locales, [ABROAD[l][1] for l in locales], None)

	def walk(self, specs: dict) -> list[dict]:
		found = []
		for spec in specs.values():
			found.append(spec)
			if spec["kind"] == "table":
				found.extend(self.walk(spec["fields"]))
		return found

	# compile: check each spec against the DocType and prepare its draws

	def compile_given(self, given) -> list[dict]:
		"""Exact records, dealt one per generated record in order. Keys that are fields set the
		field; any key, field or not, reads in templates as {key}."""
		if given is None:
			return []
		if not isinstance(given, list) or not given or not all(isinstance(row, dict) and row for row in given):
			self.errors.append("given is a list of records, each a {field: value} map")
			return []
		if len(given) != self.count:
			self.errors.append(f"count is {self.count} but given has {len(given)} records; make them equal")
		known = value_fields(self.meta)
		for key in sorted({key for row in given for key in row} & set(known)):
			if not (known[key].unique or self.meta.autoname == f"field:{key}"):
				continue
			values = [str(row[key]) for row in given if row.get(key) not in (None, "")]
			repeated = sorted({v for v in values if values.count(v) > 1})
			existing = frappe.get_all(self.doctype, filters={key: ["in", values]}, pluck=key) if values else []
			if repeated or existing:
				self.errors.append(f"given {key} must be unique; {', '.join(repeated + existing)} repeat or exist")
		return given

	def compile(self, meta, fields: dict, prefix: str, draws: int | None) -> dict[str, dict]:
		given_keys = set() if prefix else self.given_keys
		if not isinstance(fields, dict) or not (fields or given_keys):
			self.errors.append(f"{prefix or 'fields'} must map fieldnames to specs")
			return {}
		known = value_fields(meta)
		specs = {}
		for fieldname, raw in fields.items():
			where = f"{prefix}{fieldname}"
			df = known.get(fieldname)
			if not df:
				self.errors.append(f"{meta.name} has no field {where}; fields: {', '.join(known)}")
				continue
			spec = dict(raw) if isinstance(raw, dict) else {"kind": "constant", "value": raw}
			kind = spec.get("kind")
			if kind not in KINDS:
				self.errors.append(f"{where}: kind must be one of {', '.join(KINDS)}")
				continue
			unknown = set(spec) - COMMON_PARAMS - KINDS[kind]
			if unknown:
				self.errors.append(f"{where}: {kind} takes {', '.join(sorted(KINDS[kind] | {'empty', 'unique'}))}, not {', '.join(sorted(unknown))}")
				continue
			spec["df"] = df
			spec["where"] = where
			if (df.unique or meta.autoname == f"field:{fieldname}") and kind != "link":
				spec["unique"] = True
			# people do not share an email or a phone, also across calls
			if kind in ("email", "phone"):
				spec.setdefault("unique", True)
			spec["taken"] = set()
			if spec.get("unique") and kind != "table" and not meta.istable:
				spec["taken"] = {str(v) for v in frappe.get_all(meta.name, pluck=fieldname, distinct=True) if v}
			try:
				getattr(self, f"compile_{kind}")(spec, df, draws)
			except SpecError as e:
				self.errors.append(f"{where}: {e}")
			except Exception as e:
				self.errors.append(f"{where}: {kind} spec is invalid ({e})")
			specs[fieldname] = spec
		slots: dict[str, Bag] = {}
		owners: dict[str, str] = {}
		for fieldname, spec in specs.items():
			for name, bag in spec.pop("own_slots", {}).items():
				if name in owners:
					self.errors.append(f"slot {name} is in both {owners[name]} and {fieldname}; give it once, every field of the record can use it")
				elif name in specs or name in given_keys:
					self.errors.append(f"{fieldname}: slot {name} has the name of a field or a given value; rename it")
				owners[name] = fieldname
				slots[name] = bag
		for spec in specs.values():
			if spec["kind"] in ("text", "choice"):
				spec["slot_bags"] = slots
		for spec in specs.values():
			if spec["kind"] == "text":
				self.check_text(spec, specs, meta, given_keys)
			if "options_from" in spec:
				try:
					self.check_choice(spec)
				except SpecError as e:
					self.errors.append(f"{spec['where']}: {e}")
			if spec.get("unique") and not prefix:
				spec["taken"] |= {str(row[spec["df"].fieldname]) for row in self.given if spec["df"].fieldname in row}
		return specs

	def check_required(self, meta, specs: dict, prefix: str) -> None:
		missing = [
			f"{prefix}{df.fieldname}"
			for df in meta.fields
			if df.reqd
			and not (df.default or df.fetch_from)
			and df.fieldname not in specs
			and not (not prefix and self.given and all(df.fieldname in row for row in self.given))
			and df.fieldtype not in no_value_fields
		]
		if missing:
			self.errors.append(f"add a spec for the required field(s) {', '.join(missing)}")
		for spec in specs.values():
			if spec["kind"] == "table":
				self.check_required(frappe.get_meta(spec["df"].options), spec["fields"], f"{spec['where']}.")

	def compile_name(self, spec, df, draws):
		for share in ("india", "women"):
			if not 0 <= flt(spec.get(share, 0)) <= 1:
				raise SpecError(f"{share} is a share from 0 to 1")

	compile_first_name = compile_last_name = compile_name

	def compile_company(self, spec, df, draws):
		if names := spec.get("names"):
			outcomes, weights = weighted(names)
		else:
			pool = cint(spec.get("pool")) or max(5, (draws or 50) // 8)
			outcomes = {self.random_company() for _ in range(pool * 3)}
			outcomes = sorted(outcomes)[:pool]
			self.rng.shuffle(outcomes)
			weights = [1 / (i + 1) ** 0.4 for i in range(len(outcomes))]  # a few big employers, a long tail
		spec["bag"] = Bag(self.rng, outcomes, weights, draws)

	def random_company(self) -> str:
		head, middle, tail = (self.rng.choice(words) for words in COMPANY_WORDS)
		return " ".join(w for w in (head, middle, tail) if w)

	def compile_email(self, spec, df, draws):
		if spec.get("domain") and spec.get("company"):
			raise SpecError("give domain or company, not both")
		free = flt(spec.get("free", 0))
		spec["free_bag"] = Bag(self.rng, [True, False], [free, 1 - free], draws)
		spec["mail_bag"] = Bag(self.rng, *weighted(FREE_MAIL), None)
		self.emails_taken |= {e.lower() for e in spec["taken"]}

	def compile_phone(self, spec, df, draws):
		spec.setdefault("prefix", "+91 ")
		spec.setdefault("digits", 10)
		spec.setdefault("first", "987")

	def compile_date(self, spec, df, draws):
		ranges = spec.get("ranges") or [[spec.get("from"), spec.get("to")]]
		if not ranges[0][0] or not ranges[0][1]:
			raise SpecError("give from and to, or ranges as [[from, to, weight], ...]")
		parsed = []
		for r in ranges:
			start, end = parse_day(r[0]), parse_day(r[1])
			if end < start:
				raise SpecError(f"range {r[0]} to {r[1]} ends before it starts")
			parsed.append((start, end))
		spec["range_bag"] = Bag(self.rng, parsed, [flt(r[2]) if len(r) > 2 else 1.0 for r in ranges], draws)
		spec["skew_value"] = flt(SKEWS.get(spec.get("skew"), spec.get("skew") or 0))
		weekdays = spec.get("weekdays")
		if weekdays and (len(weekdays) != 7 or not any(flt(w) > 0 for w in weekdays)):
			raise SpecError("weekdays is 7 weights, Monday to Sunday")

	def compile_datetime(self, spec, df, draws):
		self.compile_date(spec, df, draws)
		times = spec.get("times") or [["09:00", "18:00"]]
		windows = [(parse_minutes(t[0]), parse_minutes(t[1])) for t in times]
		if any(end <= start for start, end in windows):
			raise SpecError("each time window is [start HH:MM, end HH:MM, weight] with end after start")
		spec["time_bag"] = Bag(self.rng, windows, [flt(t[2]) if len(t) > 2 else 1.0 for t in times], draws)

	def compile_int(self, spec, df, draws):
		if "min" not in spec or "max" not in spec or flt(spec["max"]) < flt(spec["min"]):
			raise SpecError("give min and max, with max at least min")
		spec["skew_value"] = flt(SKEWS.get(spec.get("skew"), spec.get("skew") or 0))

	compile_float = compile_int

	def compile_choice(self, spec, df, draws):
		"""`options` is a list, a weight map, or {slot.key} for a list each object of a slot holds,
		so the options follow the record's slot value."""
		options = spec.get("options")
		if isinstance(options, str):
			if not (m := re.fullmatch(r"\{(\w+)\.(\w+)\}", options.strip())):
				raise SpecError("options is a list, a {value: weight} map, or {slot.key} naming a list in each object of a slot")
			spec["options_from"] = (m[1], m[2])
			return
		outcomes, weights = weighted(options or [])
		if not outcomes:
			raise SpecError("options is a list, a {value: weight} map, or {slot.key} naming a list in each object of a slot")
		self.check_options(spec, df, [outcomes])
		spec["bag"] = Bag(self.rng, outcomes, weights, draws)

	def check_options(self, spec, df, lists: list[list]) -> None:
		if "pick" in spec:
			pick = spec["pick"]
			low, high = (pick, pick) if isinstance(pick, int) else (pick[0], pick[1])
			if df.fieldtype == "Select":
				raise SpecError("a Select field holds one value; pick fills a text field")
			fewest = min(len(options) for options in lists)
			if not 1 <= cint(low) <= cint(high) <= fewest:
				raise SpecError(f"pick is a count or [min, max] options, at most the {fewest} options")
			spec["pick_range"] = (cint(low), cint(high))
		if df.fieldtype == "Select":
			allowed = [o for o in (df.options or "").split("\n")]
			bad = sorted({str(o) for options in lists for o in options if str(o) not in allowed})
			if bad:
				raise SpecError(f"{', '.join(bad)} not in the options {', '.join(o for o in allowed if o)}")

	def check_choice(self, spec) -> None:
		name, key = spec["options_from"]
		self.read.add(name)
		bag = spec["slot_bags"].get(name)
		if not bag:
			raise SpecError(f"options {{{name}.{key}}}: no slot {name}; give it in a text field's slots")
		if not all(isinstance(o, dict) and isinstance(o.get(key), list) and o[key] for o in bag.outcomes):
			raise SpecError(f"options {{{name}.{key}}}: every value of slot {name} must be an object with {key} as a list of options")
		self.check_options(spec, spec["df"], [o[key] for o in bag.outcomes])

	def compile_link(self, spec, df, draws):
		if df.fieldtype != "Link":
			raise SpecError(f"link needs a Link field; this one is {df.fieldtype}")
		target = df.options
		names = frappe.get_list(target, filters=spec.get("filters") or {}, pluck="name", order_by="creation asc", limit=100000)
		if not names:
			raise SpecError(f"no {target} records match; create them first")
		if spec.get("each"):
			if draws != len(names):
				raise SpecError(f"each gives each of the {len(names)} matching {target} records one record, so count must be {len(names)}")
			spec["queue"] = names[::-1]
			return
		if spec.get("unique"):
			if draws is None or draws > len(names):
				raise SpecError(f"unique needs at least {draws} {target} records; {len(names)} match")
			spec["queue"] = self.rng.sample(names, draws)
			return
		if weights := spec.get("weights"):
			missing = [n for n in weights if n not in names]
			if missing:
				raise SpecError(f"no {target} named {', '.join(missing)}")
			spec["bag"] = Bag(self.rng, *weighted(weights), draws)
			return
		distribution = spec.get("distribution") or "uniform"
		if distribution not in ("uniform", "skewed"):
			raise SpecError("distribution is uniform or skewed")
		order = list(names)
		self.rng.shuffle(order)
		weights = [1 / (i + 1) if distribution == "skewed" else 1.0 for i in range(len(order))]
		spec["bag"] = Bag(self.rng, order, weights, draws)

	def compile_text(self, spec, df, draws):
		templates = spec.get("templates") or ([spec["template"]] if spec.get("template") else None)
		if not templates:
			raise SpecError("give template, or templates as a list or a {template: weight} map")
		spec["bag"] = Bag(self.rng, *weighted(templates), draws)
		slots = spec.get("slots") or {}
		if not isinstance(slots, dict):
			raise SpecError("slots maps a slot name to a list or a {value: weight} map")
		spec["own_slots"] = {}
		for name, values in slots.items():
			outcomes, weights = weighted(values)
			if not outcomes:
				raise SpecError(f"slot {name} has no values")
			objects = [o for o in outcomes if isinstance(o, dict)]
			if objects and len(objects) != len(outcomes):
				raise SpecError(f"slot {name} mixes objects and plain values")
			if objects and not set.intersection(*(set(o) for o in objects)):
				raise SpecError(f"the objects of slot {name} share no key")
			spec["own_slots"][name] = Bag(self.rng, outcomes, weights, draws)
		spec["counter"] = cint(spec.get("start", 1))
		if "words" in spec:
			words = spec["words"]
			if not (isinstance(words, list) and len(words) == 2 and 0 < cint(words[0]) <= cint(words[1])):
				raise SpecError("words is [min, max]")
			spec["words"] = (cint(words[0]), cint(words[1]))

	def check_text(self, spec, specs: dict, meta, given_keys: set[str]) -> None:
		if "bag" not in spec:
			return
		slots = spec["slot_bags"]
		texts = list(spec["bag"].outcomes)
		for values in (spec.get("slots") or {}).values():
			for value in weighted(values)[0]:
				texts.extend(value.values() if isinstance(value, dict) else [value])
		for text in texts:
			for token in PLACEHOLDER.findall(str(text)):
				if problem := self.placeholder_problem(token, slots, specs, meta, given_keys):
					self.errors.append(f"{spec['where']}: {{{token}}} {problem}")

	def placeholder_problem(self, token: str, slots: dict, specs: dict, meta, given_keys: set[str]) -> str | None:
		if re.fullmatch(r"0+|\d+\.\.\d+|code:\d+", token):
			return None
		head, _, attr = token.partition(".")
		self.read.add(head)
		if head in slots:
			objects = [o for o in slots[head].outcomes if isinstance(o, dict)]
			if not objects:
				return None if not attr else f"{head} holds plain values, so write {{{head}}}"
			keys = set.intersection(*(set(o) for o in objects))
			return None if attr in keys else f"pick a key of {head}: {', '.join(sorted(keys))}"
		if head == "person":
			return None if attr in PERSON_ATTRS else f"person has {', '.join(sorted(PERSON_ATTRS))}"
		if head not in specs and head not in given_keys:
			return "is not a slot, a field in the spec, a given value, person.*, {0000}, {1..9} or {code:6}"
		if attr:
			df = specs[head]["df"] if head in specs else meta.get_field(head)
			if not df or df.fieldtype != "Link" or (attr != "name" and not frappe.get_meta(df.options).has_field(attr)):
				return f"{head} is not a Link whose DocType has {attr}"
		return None

	def compile_constant(self, spec, df, draws):
		if "value" not in spec:
			raise SpecError("give value")

	def compile_fake(self, spec, df, draws):
		method = spec.get("method") or ""
		faker = self.faker(spec.get("locale") or "en_IN")
		if method.startswith("_") or method in FAKER_BLOCKED or not callable(getattr(faker, method, None)):
			raise SpecError(f"faker has no method {method!r}")

	def compile_table(self, spec, df, draws):
		if df.fieldtype not in table_fields:
			raise SpecError(f"table needs a Table field; this one is {df.fieldtype}")
		rows = spec.get("rows", [1, 3])
		spec["row_range"] = (cint(rows), cint(rows)) if isinstance(rows, int) else (cint(rows[0]), cint(rows[1]))
		spec["fields"] = self.compile(frappe.get_meta(df.options), spec.get("fields"), f"{spec['where']}.", None)

	# generate

	def faker(self, locale: str):
		if locale not in self.fakers:
			from faker import Faker

			fake = Faker(locale)
			fake.seed_instance(self.rng.random())
			self.fakers[locale] = fake
		return self.fakers[locale]

	def new_person(self) -> Person:
		india, woman = self.india.draw(), self.women.draw()
		tries = TRIES if self.persons_unique else 5
		for _ in range(tries):
			if india:
				men, women, surnames, _w = INDIA[self.regions.draw()]
				person = Person(self.rng.choice(women if woman else men), self.rng.choice(surnames), woman, "India")
			else:
				locale = self.locales.draw()
				fake = self.faker(locale)
				first = fake.first_name_female() if woman else fake.first_name_male()
				person = Person(first, fake.last_name(), woman, ABROAD[locale][0])
			if person.full_name not in self.persons_taken:
				break
		else:
			if self.persons_unique:
				raise SpecError("ran out of unique names; generate fewer records per call")
		self.persons_taken.add(person.full_name)
		return person

	def rows(self) -> list[dict]:
		return [Row(self, self.specs, i, self.given[i] if self.given else {}).values() for i in range(self.count)]

	def linked(self, doctype: str, name: str, field: str) -> Any:
		if not name:
			return None
		key = (doctype, name)
		if key not in self.link_values:
			self.link_values[key] = frappe.get_doc(doctype, name).as_dict()
		return self.link_values[key].get(field)


class Row:
	def __init__(self, gen: Generator, specs: dict, index: int, given: dict | None = None):
		self.gen, self.specs, self.index, self.rng = gen, specs, index, gen.rng
		self.given = given or {}
		self.cache: dict[str, Any] = {}
		self.slots: dict[str, Any] = {}
		self.pending: set[str] = set()
		self._person: Person | None = None

	@property
	def person(self) -> Person:
		if self._person is None:
			self._person = self.given_person() or self.gen.new_person()
		return self._person

	def given_person(self) -> Person | None:
		names = {kind: str(self.given[f]) for f, kind in self.gen.person_fields.items() if self.given.get(f)}
		if not names:
			return None
		first, _, last = names.get("name", "").partition(" ")
		first, last = names.get("first_name", first), names.get("last_name", last)
		return Person(first, last, self.gen.women.draw(), str(self.given.get("country") or ""))

	def values(self) -> dict:
		fieldnames = [*self.specs, *(f for f in self.given if f not in self.specs and self.gen.meta.has_field(f))]
		# unique fields first, so their retries can redraw slots no other field has used yet
		for fieldname in sorted(fieldnames, key=lambda f: not self.specs.get(f, {}).get("unique")):
			self.get(fieldname)
		return {fieldname: self.cache[fieldname] for fieldname in fieldnames}

	def df(self, fieldname: str):
		return self.specs[fieldname]["df"] if fieldname in self.specs else self.gen.meta.get_field(fieldname)

	def get(self, fieldname: str) -> Any:
		if fieldname in self.cache:
			return self.cache[fieldname]
		if fieldname in self.given:
			df = self.df(fieldname)
			self.cache[fieldname] = cast(self.given[fieldname], df) if df else self.given[fieldname]
			return self.cache[fieldname]
		if fieldname not in self.specs:
			raise SpecError(f"given record {self.index + 1} has no {fieldname}; give it in every record or add a spec")
		if fieldname in self.pending:
			raise SpecError(f"{fieldname} refers to itself through other fields")
		self.pending.add(fieldname)
		spec = self.specs[fieldname]
		unique = spec.get("unique") and spec["kind"] not in PERSON_KINDS | {"email", "link", "table"}
		if spec.get("empty") and self.rng.random() < flt(spec["empty"]):
			value = None
		elif unique or spec.get("words"):
			counts = []
			for _ in range(TRIES):
				slots, cached = set(self.slots), set(self.cache)
				value = self.make(spec)
				counts.append(len(str(value).split()))
				low, high = spec.get("words") or (0, counts[-1])
				if low <= counts[-1] <= high and not (unique and str(value) in spec["taken"]):
					break
				for name in set(self.slots) - slots:
					del self.slots[name]
				for name in set(self.cache) - cached:
					del self.cache[name]
			else:
				if not any(low <= n <= high for n in counts):
					raise SpecError(
						f"{spec['where']} made {min(counts)} to {max(counts)} words in {TRIES} tries, outside {low} to {high}; fit its templates and slots to the range"
					)
				raise SpecError(f"{spec['where']} ran out of unique values; widen its spec")
			if unique:
				spec["taken"].add(str(value))
		else:
			value = self.make(spec)
		self.pending.discard(fieldname)
		self.cache[fieldname] = value
		return value

	def make(self, spec: dict) -> Any:
		return cast(getattr(self, f"make_{spec['kind']}")(spec), spec["df"])

	def make_name(self, spec):
		return self.person.full_name

	def make_first_name(self, spec):
		return self.person.first_name

	def make_last_name(self, spec):
		return self.person.last_name

	def make_company(self, spec):
		return spec["bag"].draw()

	def make_email(self, spec):
		gen, person = self.gen, self.person
		if spec.get("domain"):
			domain = spec["domain"]
		elif not spec["free_bag"].draw() and (company := self.company_for_email(spec)):
			domain = company_domain(company)
		else:
			domain = spec["mail_bag"].draw()
		local = ".".join(p for p in (ascii_slug(person.first_name), ascii_slug(person.last_name)) if p) or "user"
		email, n = f"{local}@{domain}", 1
		while email in gen.emails_taken:
			n += 1
			email = f"{local}{n}@{domain}"
		gen.emails_taken.add(email)
		return email

	def company_for_email(self, spec) -> str | None:
		field = spec.get("company") or ("company" if "company" in self.specs or "company" in self.given else None)
		return field and self.get(field)

	def make_phone(self, spec):
		digits = cint(spec["digits"])
		head = self.rng.choice(str(spec["first"])) if spec["first"] else str(self.rng.randint(1, 9))
		return f"{spec['prefix']}{head}{''.join(str(self.rng.randint(0, 9)) for _ in range(digits - 1))}"

	def make_date(self, spec):
		start, end = spec["range_bag"].draw()
		weekdays = spec.get("weekdays")
		days = (end - start).days
		for _ in range(100):
			day = start + timedelta(days=min(days, int(skewed(self.rng, spec["skew_value"]) * (days + 1))))
			if not weekdays or self.rng.random() * max(weekdays) < flt(weekdays[day.weekday()]):
				return day
		return day

	def make_datetime(self, spec):
		day = self.make_date(spec)
		start, end = spec["time_bag"].draw()
		seconds = self.rng.randrange(start * 60, end * 60)
		return datetime.combine(day, datetime.min.time()) + timedelta(seconds=seconds)

	def make_int(self, spec):
		low, high = flt(spec["min"]), flt(spec["max"])
		t = skewed(self.rng, spec["skew_value"])
		if spec["kind"] == "int":
			return min(int(high), int(low + t * (high - low + 1)))
		return round(low + t * (high - low), cint(spec.get("precision", 2)))

	make_float = make_int

	def make_choice(self, spec):
		if "options_from" in spec:
			name, key = spec["options_from"]
			outcomes = list(self.slot(name, spec, 0)[key])
			weights = [1.0] * len(outcomes)
			if "pick_range" not in spec:
				return self.rng.choice(outcomes)
		elif "pick_range" in spec:
			outcomes, weights = list(spec["bag"].outcomes), list(spec["bag"].weights)
		else:
			return spec["bag"].draw()
		picked = []
		for _ in range(self.rng.randint(*spec["pick_range"])):
			i = self.rng.choices(range(len(outcomes)), weights)[0]
			picked.append(str(outcomes.pop(i)))
			weights.pop(i)
		return ", ".join(picked)

	def make_link(self, spec):
		return spec["queue"].pop() if "queue" in spec else spec["bag"].draw()

	def make_text(self, spec):
		text = self.render(spec["bag"].draw(), spec, 0)
		spec["counter"] += 1
		return text

	def render(self, template: str, spec: dict, depth: int) -> str:
		def fill(match: re.Match) -> str:
			token = match.group(1)
			head, _, attr = token.partition(".")
			if head in spec["slot_bags"]:
				value = self.slot(head, spec, depth)
				return str(value[attr] if attr else value)
			if re.fullmatch(r"0+", token):
				return str(spec["counter"]).zfill(len(token))
			if m := re.fullmatch(r"(\d+)\.\.(\d+)", token):
				return str(self.rng.randint(int(m.group(1)), int(m.group(2))))
			if m := re.fullmatch(r"code:(\d+)", token):
				return "".join(self.rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(int(m.group(1))))
			if head == "person":
				return getattr(self.person, attr)
			value = self.get(head)
			if attr:
				value = self.gen.linked(self.df(head).options, value, attr)
			return "" if value is None else str(value)

		return PLACEHOLDER.sub(fill, str(template))

	def slot(self, name: str, spec: dict, depth: int) -> Any:
		"""A slot is drawn once per record, so every field of the record reads the same value."""
		if name not in self.slots:
			value = spec["slot_bags"][name].draw()
			if depth < 5:
				if isinstance(value, dict):
					value = {
						k: [self.render(str(x), spec, depth + 1) for x in v] if isinstance(v, list) else self.render(str(v), spec, depth + 1)
						for k, v in value.items()
					}
				else:
					value = self.render(str(value), spec, depth + 1)
			self.slots[name] = value
		return self.slots[name]

	def make_constant(self, spec):
		return spec["value"]

	def make_fake(self, spec):
		return getattr(self.gen.faker(spec.get("locale") or "en_IN"), spec["method"])(**(spec.get("args") or {}))

	def make_table(self, spec):
		low, high = spec["row_range"]
		return [Row(self.gen, spec["fields"], i).values() for i in range(self.rng.randint(low, high))]


def value_fields(meta) -> dict:
	return {f.fieldname: f for f in meta.fields if f.fieldtype not in no_value_fields or f.fieldtype in table_fields}


def cast(value: Any, df) -> Any:
	if value is None:
		return None
	fieldtype = df.fieldtype
	if fieldtype in ("Int", "Check"):
		return cint(flt(value)) if not isinstance(value, bool) else int(value)
	if fieldtype in ("Float", "Currency", "Percent"):
		return flt(value)
	if fieldtype == "Date":
		return str(value)[:10]
	if fieldtype == "Datetime":
		return str(value)[:19]
	if fieldtype in table_fields:
		return value
	return str(value)
