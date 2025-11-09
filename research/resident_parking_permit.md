# Boston Resident Parking Permit (RPP) - Research Notes

**Citation Notation**: Throughout this document, citations to Boston.gov appear with numerical suffixes (+1, +2, +3) to indicate:
- Base URL = primary source page
- +1 = same source, different section or related page
- +2 = secondary supporting document (e.g., PDF, form)
- +3 = tertiary reference or detailed regulation

All citations should be converted to structured YAML with full URLs in `/docs/facts/boston_rpp.yaml`.

---

## 0) Outcome (what the graph should answer)

"Am I eligible right now?"

"Which documents must I upload, exactly?"

"What step is next and where do I do it (URL/office)?"

"What changed the scope (e.g., rental car, leased/corporate) and why?"

"What's the governing rule text behind that requirement?"

1) End‑to‑end process (canonical steps)

A. Determine applicability

Confirm the address is in Boston and on/near streets posted “Resident Permit Parking Only.” (Most neighborhoods have RPP; program is neighborhood‑scoped.) 
Boston.gov

B. Check hard gates (eligibility)
2) Vehicle class: passenger or commercial < 1 ton. 
Boston.gov

3) Registration: valid Massachusetts registration in the applicant’s name at the Boston address (principal garaging & insurance at that address). Exception: active‑duty military may use current non‑MA registration with MA orders. 
Boston.gov
+1

4) No unpaid Boston parking tickets on the registration. 
Boston.gov

C. Gather exactly one of the accepted proofs of Boston residency (dated ≤30 days; name matches registration)

Utility (gas/electric/telephone), cable bill, bank statement, mortgage, credit card, water/sewer, or lease (move‑in ≤30 days; for online, apply within 10 days of move‑in). 
Boston.gov

D. Choose path

New resident, replace, renew: online portal or City Hall (same‑day if in person). Permit is free; sticker placement = rear passenger‑side window. Auto‑renew is handled via neighborhood compliance cycles (no printed expiry). 
Boston.gov
+1

Rental car: 30‑day max; weekend online submission not available; if you picked up after 3 p.m., apply next business day; print e‑permit. 
Boston.gov

Leased/corporate vehicle: MA reg in leasing company/corp name + resident proof; one permit per person. Some cases require a company letter attesting principal insurance/garaging. 
Boston.gov
+1

Boston‑based business vehicle: MA reg in business name at neighborhood address; one per business; present Articles of Organization or a City Business Certificate. 
Boston.gov
+1

Taxi (hackney): hackney docs + MA reg in taxi corp name + resident proof; no outstanding violations. 
Boston.gov

Military: current state registration + resident proof + MA orders showing stationed in MA. 
Boston.gov

E. Results and enforcement

If you park in an RPP zone without a valid neighborhood sticker: ticket (“No Valid Resident Parking Permit” = $100 base fine). 
Boston.gov

Sticker misuse/duplication or bounced ticket payments → revocation and up to 2‑year denial. Address changes must be reported to the Parking Clerk (failure can also trigger revocation). 
Boston.gov

There are no visitor permits; visitor spaces are signed 2‑hour or 2‑hour except resident sticker. 
Boston.gov
+1

2) Graph: core node types (labels) & key properties

Person

person_id, name, email, phone

Residence

res_id, street, unit, zip, neighborhood (RPP neighborhood), geocode

RPPNeighborhood

nbrhd_id, name, auto_renew_cycle (date or window), notes
Example cycles: Back Bay ~ May 31, 2026; South Boston ~ Dec 31, 2025 (table changes over time, store as events). 
Boston.gov

Vehicle

veh_id, plate, year, make, type (passenger / commercial_lt_1_ton / taxi / motorcycle), is_rental, is_leased, is_corporate

Registration

reg_id, state (expect “MA” except military), address, principal_garaging_address, insured_at_address, status (valid/expired), has_unpaid_boston_tickets (bool) 
Boston.gov

Permit

permit_id, type (resident / rental / business / corporate/leased / taxi / military), neighborhood, status (active/suspended/expired), sticker_serial, display_location_rule (rear passenger‑side), issued_on, valid_through (optional when auto‑renew cycles are in force) 
Boston.gov

Application

app_id, path (online / in_person), category (new / renewal / replacement / rental / business / corporate/leased / taxi / military), submitted_on, decision (approved/denied/pending), reason_if_denied

DocumentType

doc_type_id, name (e.g., utility_bill, bank_statement, mortgage, credit_card, water_sewer, lease, rental_contract, company_letter, hackney_card, hackney_shift_lease, military_orders), freshness_days (e.g., 30) 
Boston.gov
+3
Boston.gov
+3
Boston.gov
+3

Document (UserProvidedDoc)

doc_id, doc_type_id, issuer, issue_date, name_on_doc, address_on_doc, file_ref, verified (bool)

Rule (atomic, citable)

rule_id (e.g., RPP-15-4A), text, source_url, effective_date, scope (general/rental/business/leased/military/display/enforcement) 
Boston.gov
+2
Boston.gov
+2

WebResource

res_id, title, url, last_seen, owner (Parking Clerk/BTD), type (how_to, program, portal, pdf_form) 
Boston.gov
+2
Boston.gov
+2

Office

office_id, name (Parking Clerk), address, room (224), hours (M–F 9–4:30), phone, email (parking@boston.gov
) 
Boston.gov

Ticket

ticket_id, status, fine_code (e.g., “No Valid Resident Parking Permit”), amount (base), jurisdiction (Boston) 
Boston.gov

Status/Event

event_id, kind (neighborhood_audit, revocation, change_of_address_notice), date, details 
Boston.gov
+1

3) Relationships (edge types)

PERSON_RESIDES_AT (Person → Residence)

RESIDENCE_WITHIN (Residence → RPPNeighborhood)

PERSON_OWNS / PERSON_LEASES / PERSON_DRIVES_FOR (→ Vehicle)

VEHICLE_HAS_REGISTRATION (Vehicle → Registration)

REGISTRATION_GARAGED_AT (Registration → Residence)

PERSON_SUBMITTED (Person → Application)

APPLICATION_REQUESTS (Application → Permit)

APPLICATION_REQUIRES (Application → DocumentType)

PERSON_PROVIDED (Person → Document)

DOCUMENT_SATISFIES (Document → DocumentType)

PERMIT_APPLIES_IN (Permit → RPPNeighborhood)

APPLICATION_BLOCKED_BY (Application → Ticket)

RULE_GOVERNS (Rule → Application/Permit/Registration/etc.)

APPLICATION_USES_RESOURCE (Application → WebResource)

APPLICATION_HANDLED_AT (Application → Office)

NEIGHBORHOOD_AUDITED_BY (RPPNeighborhood → Event)

EXCEPTION_FOR (Rule → Category, e.g., Military)

This keeps both the procedural graph (what to do next) and the normative graph (why it’s required) in one place.

4) Decision logic (branching questions your chatbot should ask)

Gate 0: Address

Is your residential address in Boston?

Is your street posted “Resident Permit Parking Only”? (If unsure, show neighborhood info and explain that most neighborhoods have RPP.) 
Boston.gov

Gate 1: Vehicle class

Is your vehicle passenger or commercial under 1 ton? If not → ineligible. 
Boston.gov

Gate 2: Registration

Is your registration MA at your current Boston address, with principal garaging & insurance at that address?

No, but I’m active‑duty military stationed in MA → collect orders and proceed under military path.

No (and not military) → show RMV path to transfer/retitle and change garaging; block permit until complete. 
Boston.gov
+1

Gate 3: Outstanding tickets

Any unpaid Boston tickets on this registration? If yes → pay first (link). 
Boston.gov

Gate 4: Special category

Rental? (≤30 days; upload rental agreement; weekend online limitation; after‑3pm next business day.) 
Boston.gov

Leased/Corporate? (MA reg in company name + resident proof; often requires company letter.) 
Boston.gov
+1

Business vehicle? (MA reg in business name + Articles or Business Certificate; one per business.) 
Boston.gov

Taxi? (hackney docs + MA reg in taxi corp). 
Boston.gov

Gate 5: Proof of residency

Provide one current doc (≤30 days; name/address match registration). If lease, ensure move‑in window met (≤30 days; online within 10 days). 
Boston.gov

Gate 6: Channel & fulfillment

Online (mail/print timing per path) vs in person (same‑day at City Hall Room 224). Sticker placement reminder; permit is free. Auto‑renew cycles table for the neighborhood. 
Boston.gov
+1

Enforcement & compliance

Show the fine risk for parking without a valid neighborhood sticker and revocation/denial conditions. Capture address‑change obligations. 
Boston.gov
+1

5) Document requirements by path (minimal set)

New resident (standard): MA registration (name/address match; principal garaging/insurance at same address) + 1 current proof of residency. 
Boston.gov
+1

Renewal/Replacement: same as above; replacements required for plate, vehicle, or neighborhood change. 
Boston.gov

Rental: rental agreement + proof of residency (if you don’t already have a sticker); 30‑day max. 
Boston.gov

Leased/Corporate: MA reg in corp/lessor name + proof of residency; one per person; often a company letter (vehicle details; principal insurance/garaging at resident’s Boston address). 
Boston.gov
+1

Business vehicle: MA reg in business name + Articles of Organization or City Business Certificate; one per business. 
Boston.gov

Taxi: hackney shift lease + hackney card + MA reg in taxi corp + proof of residency; no outstanding violations. 
Boston.gov

Military: current state registration + proof of residency + MA orders. 
Boston.gov

6) Why the rules look this way (causal frame)

Neighborhood scope protects curb space for locals; the sticker is neighborhood‑specific and only valid where signed. 
Boston.gov

MA registration + principal garaging at the Boston address links the permit to where the car actually lives (insurance & excise), and blocks long‑term street storage by non‑residents. 
Boston.gov

Ticket gate enforces compliance before granting curb access. 
Boston.gov

Auto‑renew audits reduce yearly friction while letting the City re‑verify eligibility by neighborhood. 
Boston.gov

Special paths (rental, corporate/leased, taxi, military) reflect real‑world use cases while limiting scope abuse (e.g., caps like “one per business/person”). 
Boston.gov
+1

7) Minimal property‑graph schema (Neo4j-ish)

Constraints

(:Person {person_id}) unique

(:Vehicle {veh_id}) unique

(:Registration {reg_id}) unique

(:Permit {permit_id}) unique

(:Rule {rule_id}) unique

(:DocumentType {doc_type_id}) unique

(:WebResource {url}) unique

Examples of atomic Rule nodes (tie your UI tooltips directly to these):

RPP-15-4A “MA registration in person’s name at current Boston address; principal garaged & insured at same address” (effective 2025‑03‑01). 
Boston.gov

RPP-15-5D “Rental permit up to 30 days.” 
Boston.gov

RPP-Display-6 “Sticker location: rear passenger‑side / front passenger window if needed.” 
Boston.gov

RPP-Revocation-7 “Duplication/alteration or returned‑check → revocation; up to 2‑year denial.” 
Boston.gov

RPP-AddrChange-8 “Must report change of address to Parking Clerk; failure may cause revocation/denial.” 
Boston.gov

RPP-Business-10D “One permit per business.” / RPP-Leased-11D “One permit per person (leased/corp).” 
Boston.gov
+1

RPP-Military-EXC “Military may use current non‑MA registration with MA orders.” 
Boston.gov

8) Seed data (small, illustrative)

DocumentTypes

[
  {"doc_type_id":"proof.utility_bill","name":"Utility bill","freshness_days":30},
  {"doc_type_id":"proof.bank_statement","name":"Bank statement","freshness_days":30},
  {"doc_type_id":"proof.lease","name":"Signed lease (≤30d; online ≤10d after move-in)","freshness_days":30},
  {"doc_type_id":"proof.rental_contract","name":"Rental car agreement","freshness_days":30},
  {"doc_type_id":"proof.company_letter","name":"Company letter (corporate vehicle)","freshness_days":90},
  {"doc_type_id":"proof.hackney_card","name":"Hackney carriage card","freshness_days":365},
  {"doc_type_id":"proof.military_orders","name":"MA military orders","freshness_days":365}
]


WebResources (URLs are the stable anchors your bot should quote)

[
  {"res_id":"howto","title":"How To Get A Resident Parking Permit (updated 2025-10-30)","url":"https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit"},
  {"res_id":"program","title":"Resident Parking Permits (updated 2025-10-30)","url":"https://www.boston.gov/departments/parking-clerk/resident-parking-permits"},
  {"res_id":"rules2025","title":"Traffic Rules & Regulations – Section 15 Resident Permit Parking (effective 2025-03-01)","url":"https://www.boston.gov/sites/default/files/file/2025/01/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations%203.1.2025.pdf"},
  {"res_id":"portal","title":"Parking Permit Portal","url":"https://www.boston.gov/parkingpermits"},
  {"res_id":"corp_pdf","title":"Corporate Vehicle RPP requirements (PDF, 2025-06)","url":"https://www.boston.gov/sites/default/files/file/2025/06/Corporate%20Veh%20RPP%20Applicants.pdf"},
  {"res_id":"mil_pdf","title":"Military Personnel RPP requirements (PDF, 2025-06)","url":"https://www.boston.gov/sites/default/files/file/2025/06/Miltary%20Personnel%20RPP.pdf"}
]


Rules (sample)

[
  {"rule_id":"RPP-15-4A","text":"MA registration in person’s name at current Boston address; principal garaged & insured at same address.","source":"rules2025","scope":"general","effective_date":"2025-03-01"},
  {"rule_id":"RPP-15-4C","text":"No unpaid parking tickets on the registration.","source":"rules2025","scope":"general","effective_date":"2025-03-01"},
  {"rule_id":"RPP-15-5D","text":"Rental sticker length ≤ rental contract, max 30 days.","source":"rules2025","scope":"rental","effective_date":"2025-03-01"},
  {"rule_id":"RPP-Display-6","text":"Sticker must be on rear passenger-side window or front passenger window if needed.","source":"rules2025","scope":"display","effective_date":"2025-03-01"},
  {"rule_id":"RPP-Revocation-7","text":"Duplication/alteration/returned check → immediate revocation and denial up to 2 years.","source":"rules2025","scope":"enforcement","effective_date":"2025-03-01"},
  {"rule_id":"RPP-Leased-11D","text":"Leased/corporate: one permit per person.","source":"rules2025","scope":"leased_corporate","effective_date":"2025-03-01"},
  {"rule_id":"RPP-Business-10D","text":"Business vehicles: one permit per business.","source":"rules2025","scope":"business","effective_date":"2025-03-01"},
  {"rule_id":"RPP-Military-EXC","text":"Military may use non‑MA registration with MA orders.","source":"mil_pdf","scope":"military","effective_date":"2025-06-01"}
]


Office

[{"office_id":"parking_clerk","name":"Office of the Parking Clerk","address":"1 City Hall Sq, Room 224, Boston MA 02201","hours":"Mon–Fri, 9:00–4:30","phone":"617-635-4410","email":"parking@boston.gov"}]


You can then attach APPLICATION_REQUIRES edges per path, e.g., standard new resident → {proof.utility_bill OR proof.bank_statement OR …}; rental → proof.rental_contract (+ proof.utility_bill if no existing sticker); corporate → proof.company_letter, etc., with RULE_GOVERNS edges to the controlling rule(s).

9) One small, runnable eligibility function (decision core)
def rpp_required_documents(app):
    """
    app: dict with keys:
      category: one of ["new","renewal","replacement","rental","business","leased_corporate","taxi","military"]
      registration: dict {"state":"MA"/..., "address_match":bool, "principal_garaging_match":bool, "no_unpaid_tickets":bool}
      vehicle: dict {"type":"passenger"|"commercial_lt_1_ton"|"taxi", "is_rental":bool}
      is_active_duty_military: bool
    Returns: {"eligible": bool, "missing": [doc_type_id...], "blocks": [reason...]}
    """
    blocks, missing = [], []

    # Vehicle class
    if app["vehicle"]["type"] not in ("passenger","commercial_lt_1_ton","taxi"):
        blocks.append("vehicle_class_ineligible")

    # Tickets
    if not app["registration"]["no_unpaid_tickets"]:
        blocks.append("unpaid_tickets")

    # Registration & address (military exception)
    reg = app["registration"]
    if app["category"] != "military":
        if reg["state"] != "MA":
            blocks.append("registration_not_MA")
        if not reg["address_match"] or not reg["principal_garaging_match"]:
            blocks.append("registration_address_or_garaging_mismatch")

    # Per-path docs
    cat = app["category"]
    if cat in ("new","renewal","replacement"):
        missing.append("proof.(utility_bill|bank_statement|mortgage|credit_card|water_sewer|lease)")
    elif cat == "rental":
        missing.append("proof.rental_contract")
        # If no prior sticker in graph history → also proof of residency
        missing.append("proof.(utility_bill|bank_statement|mortgage|credit_card|water_sewer|lease)")
    elif cat == "leased_corporate":
        missing.append("proof.company_letter")
        missing.append("proof.(utility_bill|bank_statement|... )")
    elif cat == "business":
        missing.append("proof.(articles_of_organization|city_business_certificate)")
    elif cat == "taxi":
        missing.extend(["proof.hackney_card","proof.hackney_shift_lease","proof.(utility_bill|...)"])
    elif cat == "military":
        missing.extend(["proof.military_orders","proof.(utility_bill|...)"])

    eligible = (not blocks)
    return {"eligible": eligible, "missing": sorted(set(missing)), "blocks": blocks}


Hook this function to your graph by substituting the doc sets with actual DocumentType IDs and checking history (e.g., whether the person already holds a valid sticker).

10) UX copy your bot can reuse (atomic, rule‑linked)

“Your registration must be a Massachusetts certificate at your current Boston address and show the vehicle is principally garaged and insured at that address.” (Rule RPP-15-4A → link to rule PDF) 
Boston.gov

“If this is a rental car, the resident permit lasts up to 30 days and you’ll upload your rental agreement.” (Rule RPP-15-5D) 
Boston.gov

“We can’t issue a permit while there are unpaid tickets on the registration.” (Rule RPP-15-4C) 
Boston.gov

“No visitor permits exist; visitor spaces (where posted) are 2‑hour or 2‑hour except resident sticker.” (Program page) 
Boston.gov

“Sticker placement: rear passenger‑side window (front passenger window if tint obstructs).” (Display Rule) 
Boston.gov

11) Data ingestion & provenance

Treat Traffic Rules §15 as the source of truth for issuance rules; map each clause to a Rule node with a precise quote + page screenshot reference (you have pages 26–28 captured). 
Boston.gov
+2
Boston.gov
+2

Use How‑To for process specifics (proof lists, timing, office hours, rental weekend limitation). 
Boston.gov

Use Program page for auto‑renew cycles, “no fee,” and “no visitor permits.” 
Boston.gov

Keep PDF one‑pagers (Corporate / Business / Taxi / Military) as additional Rule or DocumentType sources. 
Boston.gov
+3
Boston.gov
+3
Boston.gov
+3

Portal login is your operational node for online applications. 
Boston.gov

12) Open edges / known nuances

Neighborhood coverage: Not every block is posted RPP; model the presence of signs (or neighborhood policy) as a boolean per address. The City’s page frames this broadly; exact sign data isn’t centrally published—your bot should ask or show “how to read signs” guidance. 
Boston.gov

Renewal: The “How‑To” page still mentions renewing 4–6 weeks before expiration, while the Program page emphasizes auto‑renew audits and no printed expiration. Store both; prefer the Program page for current policy and use audits to trigger re‑verification tasks. 
Boston.gov
+1

Address changes: Model as a compliance obligation with a deadline and enforcement rule link. 
Boston.gov

13) What the bot should do next (logic → actions)

Collect: address → neighborhood → vehicle type → registration state/address/garaging → ticket status (pull if user authorizes) → special category flag → pick channel (online vs in person).

Explain each requirement with a one‑line “why” + rule link.

Assemble exact doc checklist (by path), flag freshness/name/address mismatches, and short‑circuit on blockers (unpaid tickets; wrong registration).

Route to the portal or City Hall; show sticker placement + enforcement note.

Persist: write back Status/Event nodes (e.g., “pending RMV address change”) so you can proactively re‑prompt.