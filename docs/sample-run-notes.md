# Sample run — the 26 notes the crew wrote on the fixtures (fixture mode, recorded fake, run g2c-20261106-183633)

What `triage run --fixtures` writes to the in-memory HubSpot fake: one triage note per lead and one draft note per consented good fit. Nothing here was sent anywhere.

### hs-1001 · draft · note-1

```
DRAFT — not sent
Follow-up email for Ada Testperson — saved by the Lead Triage Crew; nothing has been sent.

Subject: Who owns the next decision

Hi Ada,

Your diagnostic describes a pilot that has been running with no decision on what happens next, with the biggest gap in ownership and adoption. I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.

If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. Reply with a day that works and I'll send a time.

Shane

Rationale: Leads with the stage and the people gap from the diagnostic; one concrete next step; no numbers.

Brand policy (G0 brand.policy v1): passed
Claims registry (G0 claims.registry v1): every number supported
```

---

### hs-1001 · triage · note-2

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_75632df3205a41eea586)
Reasons:
- Orchestrator: Ada Testperson, VP Marketing, Sample Co: executive-sponsor, stage running-no-decision.
- Role: executive-sponsor
- Relationship: buyer — a leader at an operating company
- Pilot stage: running-no-decision; biggest gap 7/9
- Company: Sample Co, Consumer packaged goods, 201-1000
Workers:
- enricher: called — company 'Sample Co' needs industry, size and kind from the directory
- qualifier: called — executive-sponsor at Sample Co; pilot stage running-no-decision, grade hot
- drafter: called — good fit and consented on email (contact ct-001)
Enrichment: Sample Co · Consumer packaged goods · 201-1000 (640 employees) · kind company · source: directory:Sample Co (exact match on 'Sample Co')
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=201-1000
Draft: saved as a separate note headed 'DRAFT — not sent' · brand policy passed
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1002 · draft · note-3

```
DRAFT — not sent
Follow-up email for Ben Testperson — saved by the Lead Triage Crew; nothing has been sent.

Subject: Stop criteria for the pilot

Hi Ben,

Your diagnostic describes a pilot that finished and never rolled out, with the biggest gap in success criteria and what happens when the pilot ends. I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.

If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. Reply with a day that works and I'll send a time.

Shane

Rationale: Leads with the stage and the process gap from the diagnostic; one concrete next step; no numbers.

Brand policy (G0 brand.policy v1): passed
Claims registry (G0 claims.registry v1): every number supported
```

---

### hs-1002 · triage · note-4

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_ac8c6376ec57452a8eb8)
Reasons:
- Orchestrator: Ben Testperson, Marketing Ops Manager, Placeholder Inc: pilot-lead, stage finished-not-rolled-out.
- Role: pilot-lead
- Relationship: buyer — a leader at an operating company
- Pilot stage: finished-not-rolled-out; biggest gap 6/9
- Company: Placeholder Inc, B2B software, 51-200
Workers:
- enricher: called — company 'Placeholder Inc' needs industry, size and kind from the directory
- qualifier: called — pilot-lead at Placeholder Inc; pilot stage finished-not-rolled-out, grade hot
- drafter: called — good fit and consented on email (contact ct-002)
Enrichment: Placeholder Inc · B2B software · 51-200 (180 employees) · kind company · source: directory:Placeholder Inc (exact match on 'Placeholder Inc')
Rubric:
- decision_role: 100% (w3, required) — role=pilot-lead
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=finished-not-rolled-out
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=51-200
Draft: saved as a separate note headed 'DRAFT — not sent' · brand policy passed
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1003 · triage · note-5

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_c0bc212a10bb492aa147)
Reasons:
- Orchestrator: Cleo Testperson, Head of Demand Gen, Testdata Ltd: executive-sponsor, stage rolled-out-low-use.
- Role: executive-sponsor
- Relationship: buyer — a leader at an operating company
- Pilot stage: rolled-out-low-use; biggest gap 8/9
- Company: Testdata Ltd, Financial services, 1001-5000
Workers:
- enricher: called — company 'Testdata Ltd' needs industry, size and kind from the directory
- qualifier: called — executive-sponsor at Testdata Ltd; pilot stage rolled-out-low-use, grade hot
- drafter: SKIPPED — consent: not_consented
Enrichment: Testdata Ltd · Financial services · 1001-5000 (2300 employees) · kind company · source: directory:Testdata Ltd (exact match on 'Testdata Ltd')
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=rolled-out-low-use
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=1001-5000
Draft: skipped — consent: not_consented
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1004 · triage · note-6

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: poor fit · Score: 75/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_324c23f554084c4cb943)
Reasons:
- Orchestrator: Dev Testperson, CMO, Fixture Labs: executive-sponsor, stage planned.
- Role: executive-sponsor
- Relationship: buyer — a leader at an operating company
- Pilot stage: planned; biggest gap 2/9
- Company: Fixture Labs, Healthcare technology, 201-1000
Workers:
- enricher: called — company 'Fixture Labs' needs industry, size and kind from the directory
- qualifier: called — executive-sponsor at Fixture Labs; pilot stage planned, grade cool
- drafter: SKIPPED — band is poor fit; no follow-up
Enrichment: Fixture Labs · Healthcare technology · 201-1000 (410 employees) · kind company · source: directory:Fixture Labs (exact match on 'Fixture Labs')
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 0% (w2) — pilot_stage='planned' not in ['running-no-decision', 'finished-not-rolled-out', 'rolled-out-low-use']
- gap_at_least_6: 0% (w1) — gap_at_least_6='no' not in ['yes']
- company_size: 100% (w1) — size_band=201-1000
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1005 · triage · note-7

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: poor fit · Score: 75/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_9bedae1a16994936854e)
Reasons:
- Orchestrator: Esme Testperson, Copywriter, Synthetic Systems: team-member, stage running-no-decision.
- Role: team-member
- Relationship: buyer — a leader at an operating company
- Pilot stage: running-no-decision; biggest gap 7/9
- Company: Synthetic Systems, Industrial manufacturing, 1001-5000
Workers:
- enricher: called — company 'Synthetic Systems' needs industry, size and kind from the directory
- qualifier: called — team-member at Synthetic Systems; pilot stage running-no-decision, grade warm
- drafter: SKIPPED — band is poor fit; no follow-up
Enrichment: Synthetic Systems · Industrial manufacturing · 1001-5000 (1900 employees) · kind company · source: directory:Synthetic Systems (exact match on 'Synthetic Systems')
Rubric:
- decision_role: 0% (w3, required) — role='team-member' not in ['executive-sponsor', 'pilot-lead']
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=1001-5000
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1006 · draft · note-8

```
DRAFT — not sent
Follow-up email for Finn Testperson — saved by the Lead Triage Crew; nothing has been sent.

Subject: Where the pilot meets your systems

Hi Finn,

Your diagnostic describes a pilot that has been running with no decision on what happens next, with the biggest gap in data access and how the tool fits the systems people already use. I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.

If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. Reply with a day that works and I'll send a time.

Shane

Rationale: Leads with the stage and the technology gap from the diagnostic; one concrete next step; no numbers.

Brand policy (G0 brand.policy v1): passed
Claims registry (G0 claims.registry v1): every number supported
```

---

### hs-1006 · triage · note-9

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_c248ae24ff394586acb2)
Reasons:
- Orchestrator: Finn Testperson, Revenue Ops Director, Dummy Dynamics: pilot-lead, stage running-no-decision.
- Role: pilot-lead
- Relationship: buyer — a leader at an operating company
- Pilot stage: running-no-decision; biggest gap 6/9
- Company: Dummy Dynamics, Logistics, 5000+
Workers:
- enricher: called — company 'Dummy Dynamics' needs industry, size and kind from the directory
- qualifier: called — pilot-lead at Dummy Dynamics; pilot stage running-no-decision, grade hot
- drafter: called — good fit and consented on email (contact ct-006)
Enrichment: Dummy Dynamics · Logistics · 5000+ (7200 employees) · kind company · source: directory:Dummy Dynamics (exact match on 'Dummy Dynamics')
Rubric:
- decision_role: 100% (w3, required) — role=pilot-lead
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=5000+
Draft: saved as a separate note headed 'DRAFT — not sent' · brand policy passed
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1007 · triage · note-10

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_6312c88acccd43c8b0c5)
Reasons:
- Orchestrator: Gia Testperson, Director of Marketing, Mock Industries: executive-sponsor, stage rolled-out-low-use.
- Role: executive-sponsor
- Relationship: buyer — a leader at an operating company
- Pilot stage: rolled-out-low-use; biggest gap 9/9
- Company: Mock Industries, Building products, 201-1000
Workers:
- enricher: called — company 'Mock Industries' needs industry, size and kind from the directory
- qualifier: called — executive-sponsor at Mock Industries; pilot stage rolled-out-low-use, grade hot
- drafter: SKIPPED — consent: do_not_contact
Enrichment: Mock Industries · Building products · 201-1000 (530 employees) · kind company · source: directory:Mock Industries (exact match on 'Mock Industries')
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=rolled-out-low-use
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=201-1000
Draft: skipped — consent: do_not_contact
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1008 · draft · note-11

```
DRAFT — not sent
Follow-up email for Hal Testperson — saved by the Lead Triage Crew; nothing has been sent.

Subject: Stop criteria for the pilot

Hi Hal,

Your diagnostic describes a pilot that was shut down, with the biggest gap in success criteria and what happens when the pilot ends. I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.

If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. Reply with a day that works and I'll send a time.

Shane

Rationale: Leads with the stage and the process gap from the diagnostic; one concrete next step; no numbers.

Brand policy (G0 brand.policy v1): passed
Claims registry (G0 claims.registry v1): every number supported
```

---

### hs-1008 · triage · note-12

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 83/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_3066703d6ebe4969b001)
Reasons:
- Orchestrator: Hal Testperson, Marketing PMO Lead, Demo Holdings: pilot-lead, stage shut-down.
- Role: pilot-lead
- Relationship: buyer — a leader at an operating company
- Pilot stage: shut-down; biggest gap 8/9
- Company: Demo Holdings, Insurance, 1001-5000
Workers:
- enricher: called — company 'Demo Holdings' needs industry, size and kind from the directory
- qualifier: called — pilot-lead at Demo Holdings; pilot stage shut-down, grade warm
- drafter: called — good fit and consented on email (contact ct-008)
Enrichment: Demo Holdings · Insurance · 1001-5000 (3100 employees) · kind company · source: directory:Demo Holdings (exact match on 'Demo Holdings')
Rubric:
- decision_role: 100% (w3, required) — role=pilot-lead
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 0% (w2) — pilot_stage='shut-down' not in ['running-no-decision', 'finished-not-rolled-out', 'rolled-out-low-use']
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=1001-5000
Draft: saved as a separate note headed 'DRAFT — not sent' · brand policy passed
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1009 · triage · note-13

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: poor fit · Score: 67/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_1f1d1b9bf02b4099aa78)
Reasons:
- Orchestrator: Ivy Testperson, Content Ops Manager, Nonesuch Partners: no role, stage planned.
- Role: pilot-lead (inferred from title 'Content Ops Manager'; the form left role blank)
- Relationship: buyer — a leader at an operating company
- Pilot stage: planned; biggest gap 1/9
- Company: Nonesuch Partners, Professional services, 11-50
Workers:
- enricher: called — company 'Nonesuch Partners' needs industry, size and kind from the directory
- qualifier: called — role not given at Nonesuch Partners; pilot stage planned, grade cool
- drafter: SKIPPED — band is poor fit; no follow-up
Enrichment: Nonesuch Partners · Professional services · 11-50 (28 employees) · kind company · source: directory:Nonesuch Partners (exact match on 'Nonesuch Partners')
Rubric:
- decision_role: 100% (w3, required) — role=pilot-lead
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 0% (w2) — pilot_stage='planned' not in ['running-no-decision', 'finished-not-rolled-out', 'rolled-out-low-use']
- gap_at_least_6: 0% (w1) — gap_at_least_6='no' not in ['yes']
- company_size: 0% (w1) — size_band='11-50' not in ['51-200', '201-1000', '1001-5000', '5000+']
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1010 · triage · note-14

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: missing company info
Reasons:
- Orchestrator: Jun Testperson, VP Marketing Operations, no company: executive-sponsor, stage running-no-decision.
- The company is missing or unresolvable; ask the lead which organization they are with.
Workers:
- enricher: called — no company given; the Enricher will try the title and message
- qualifier: SKIPPED — company could not be identified (directory: no record for '' (placeholder)); nothing to score
- drafter: SKIPPED — no qualification
Enrichment: company not identified · directory: no record for '' (placeholder)
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1011 · triage · note-15

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: missing company info
Reasons:
- Orchestrator: Kai Testperson, Director, self: pilot-lead, stage running-no-decision.
- The company is missing or unresolvable; ask the lead which organization they are with.
Workers:
- enricher: called — no company given; the Enricher will try the title and message
- qualifier: SKIPPED — company could not be identified (directory: no record for 'self' (placeholder)); nothing to score
- drafter: SKIPPED — no qualification
Enrichment: company not identified · directory: no record for 'self' (placeholder)
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1012 · triage · note-16

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: poor fit · Score: 50/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_1ebf47f279f948e8aad6)
Reasons:
- Orchestrator: Lou Testperson, Fractional Marketing Advisor, Placeholder Inc: outside-advisor, stage running-no-decision.
- Role: outside-advisor
- Relationship: advisor — an outside advisor acting for a client, not the buyer
- Pilot stage: running-no-decision; biggest gap 6/9
- Company: Placeholder Inc, B2B software, 51-200
Workers:
- enricher: called — company 'Placeholder Inc' needs industry, size and kind from the directory
- qualifier: called — outside-advisor at Placeholder Inc; pilot stage running-no-decision, grade warm
- drafter: SKIPPED — band is poor fit; no follow-up
Enrichment: Placeholder Inc · B2B software · 51-200 (180 employees) · kind company · source: directory:Placeholder Inc (exact match on 'Placeholder Inc')
Rubric:
- decision_role: 0% (w3, required) — role='outside-advisor' not in ['executive-sponsor', 'pilot-lead']
- buyer_not_vendor_or_student: 0% (w3, required) — relationship='advisor' not in ['buyer']
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=51-200
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1013 · draft · note-17

```
DRAFT — not sent
Follow-up email for Mae Testperson — saved by the Lead Triage Crew; nothing has been sent.

Subject: Who owns the next decision

Hi Mae,

Your diagnostic describes a rollout that few people use, with the biggest gap in ownership and adoption. I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.

If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. Reply with a day that works and I'll send a time.

Shane

Rationale: Leads with the stage and the people gap from the diagnostic; one concrete next step; no numbers.

Brand policy (G0 brand.policy v1): passed
Claims registry (G0 claims.registry v1): every number supported
```

---

### hs-1013 · triage · note-18

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_782b513115944bd79be7)
Reasons:
- Orchestrator: Mae Testperson, Chief Marketing Officer, Testdata Ltd: executive-sponsor, stage rolled-out-low-use.
- Role: executive-sponsor
- Relationship: buyer — a leader at an operating company
- Pilot stage: rolled-out-low-use; biggest gap 7/9
- Company: Testdata Ltd, Financial services, 1001-5000
Workers:
- enricher: SKIPPED — company profile complete on the contact (company, industry, size, website)
- qualifier: called — executive-sponsor at Testdata Ltd; pilot stage rolled-out-low-use, grade hot
- drafter: called — good fit and consented on email (contact ct-013)
Enrichment: Testdata Ltd · Financial services · 1001-5000 (2300 employees) · kind company · source: contact: company profile complete on the record; Enricher skipped
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=rolled-out-low-use
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=1001-5000
Draft: saved as a separate note headed 'DRAFT — not sent' · brand policy passed
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1014 · triage · note-19

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: student · Score: 50/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_bd8b19c5597a485b8cdb)
Reasons:
- Orchestrator: Sam Studentperson, MBA candidate, Example State University: team-member, stage running-no-decision.
- Role: team-member
- Relationship: student — student or researcher: the title or message says so and the organization is a school
- Pilot stage: running-no-decision; biggest gap 6/9
- Company: Example State University, Higher education, 1001-5000
Workers:
- enricher: called — company 'Example State University' needs industry, size and kind from the directory
- qualifier: called — team-member at Example State University; pilot stage running-no-decision, grade warm
- drafter: SKIPPED — band is student; no follow-up
Enrichment: Example State University · Higher education · 1001-5000 (4100 employees) · kind education · source: directory:Example State University (exact match on 'Example State University')
Rubric:
- decision_role: 0% (w3, required) — role='team-member' not in ['executive-sponsor', 'pilot-lead']
- buyer_not_vendor_or_student: 0% (w3, required) — relationship='student' not in ['buyer']
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=1001-5000
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1015 · triage · note-20

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: student · Score: 50/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_ac1edb8f4ecd4ad29bbb)
Reasons:
- Orchestrator: Pat Gradperson, Intern, Innovation Lab, Fixture Labs: team-member, stage running-no-decision.
- Role: team-member
- Relationship: student — student or researcher: the title or message says so
- Pilot stage: running-no-decision; biggest gap 6/9
- Company: Fixture Labs, Healthcare technology, 201-1000
Workers:
- enricher: called — company 'Fixture Labs' needs industry, size and kind from the directory
- qualifier: called — team-member at Fixture Labs; pilot stage running-no-decision, grade warm
- drafter: SKIPPED — band is student; no follow-up
Enrichment: Fixture Labs · Healthcare technology · 201-1000 (410 employees) · kind company · source: directory:Fixture Labs (exact match on 'Fixture Labs')
Rubric:
- decision_role: 0% (w3, required) — role='team-member' not in ['executive-sponsor', 'pilot-lead']
- buyer_not_vendor_or_student: 0% (w3, required) — relationship='student' not in ['buyer']
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=201-1000
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1016 · triage · note-21

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: vendor · Score: 42/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_96f067add2e64fe080a5)
Reasons:
- Orchestrator: Vic Vendorperson, Founder & CEO, Mock AI Consulting: outside-advisor, stage running-no-decision.
- Role: outside-advisor
- Relationship: vendor — sells to this audience: the company is a vendor in the directory
- Pilot stage: running-no-decision; biggest gap 6/9
- Company: Mock AI Consulting, AI consulting, 11-50
Workers:
- enricher: called — company 'Mock AI Consulting' needs industry, size and kind from the directory
- qualifier: called — outside-advisor at Mock AI Consulting; pilot stage running-no-decision, grade warm
- drafter: SKIPPED — band is vendor; no follow-up
Enrichment: Mock AI Consulting · AI consulting · 11-50 (14 employees) · kind vendor · source: directory:Mock AI Consulting (exact match on 'Mock AI Consulting')
Rubric:
- decision_role: 0% (w3, required) — role='outside-advisor' not in ['executive-sponsor', 'pilot-lead']
- buyer_not_vendor_or_student: 0% (w3, required) — relationship='vendor' not in ['buyer']
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 0% (w1) — size_band='11-50' not in ['51-200', '201-1000', '1001-5000', '5000+']
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1017 · triage · note-22

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: vendor · Score: 75/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_cbd22cdd01ba4a83a8a0)
Reasons:
- Orchestrator: Sal Sellerperson, Account Executive, Dummy Data Platforms Inc: executive-sponsor, stage finished-not-rolled-out.
- Role: executive-sponsor
- Relationship: vendor — sells to this audience: the company is a vendor in the directory
- Pilot stage: finished-not-rolled-out; biggest gap 8/9
- Company: Dummy Data Platforms Inc, Data platform software, 201-1000
Workers:
- enricher: called — company 'Dummy Data Platforms Inc' needs industry, size and kind from the directory
- qualifier: called — executive-sponsor at Dummy Data Platforms Inc; pilot stage finished-not-rolled-out, grade hot
- drafter: SKIPPED — band is vendor; no follow-up
Enrichment: Dummy Data Platforms Inc · Data platform software · 201-1000 (260 employees) · kind vendor · source: directory:Dummy Data Platforms Inc (exact match on 'Dummy Data Platforms Inc')
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 0% (w3, required) — relationship='vendor' not in ['buyer']
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=finished-not-rolled-out
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=201-1000
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1018 · triage · note-23

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: duplicate
Duplicate of contact hs-1001: no workers were run; triage the original.
Reasons:
- Same person as an older contact (hs-1001); the original carries the triage.
Workers:
- enricher: SKIPPED — duplicate of contact hs-1001 (created 2026-11-02T09:00:00Z)
- qualifier: SKIPPED — duplicate of contact hs-1001 (created 2026-11-02T09:00:00Z)
- drafter: SKIPPED — duplicate of contact hs-1001 (created 2026-11-02T09:00:00Z)
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1019 · draft · note-24

```
DRAFT — not sent
Follow-up email for Tam Testperson — saved by the Lead Triage Crew; nothing has been sent.

Subject: Stop criteria for the pilot

Hi Tam,

Your diagnostic describes a pilot that has been running with no decision on what happens next, with the biggest gap in success criteria and what happens when the pilot ends. I ran into the same pattern more than once with a large marketing team: the model was fine, the decision about what happens next was nobody's job.

If it would help, I'll walk through what I'd fix first in your situation on a short call. No deck, no pitch. Reply with a day that works and I'll send a time.

Shane

Rationale: Leads with the stage and the process gap from the diagnostic; one concrete next step; no numbers.

Brand policy (G0 brand.policy v1): passed
Claims registry (G0 claims.registry v1): every number supported
```

---

### hs-1019 · triage · note-25

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: good fit · Score: 100/100 (rubric g2_lead_fit_v1, judge deterministic, evaluation eval_0d9f8b4ade1f438ca07e)
Reasons:
- Orchestrator: Tam Testperson, VP Marketing Operations, Example Corp: executive-sponsor, stage running-no-decision.
- Role: executive-sponsor
- Relationship: buyer — a leader at an operating company
- Pilot stage: running-no-decision; biggest gap 9/9
- Company: Example Corp, Retail, 5000+
Workers:
- enricher: called — company 'Example Corp' needs industry, size and kind from the directory
- qualifier: called — executive-sponsor at Example Corp; pilot stage running-no-decision, grade hot
- drafter: called — good fit and consented on email (contact ct-020)
Enrichment: Example Corp · Retail · 5000+ (12000 employees) · kind company · source: directory:Example Corp (exact match on 'Example Corp')
Rubric:
- decision_role: 100% (w3, required) — role=executive-sponsor
- buyer_not_vendor_or_student: 100% (w3, required) — relationship=buyer
- company_identified: 100% (w2, required) — company present
- stalled_stage: 100% (w2) — pilot_stage=running-no-decision
- gap_at_least_6: 100% (w1) — gap_at_least_6=yes
- company_size: 100% (w1) — size_band=5000+
Draft: saved as a separate note headed 'DRAFT — not sent' · brand policy passed
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```

---

### hs-1020 · triage · note-26

```
Lead Triage Crew (G2·C) — run g2c-20261106-183633
Band: duplicate
Duplicate of contact hs-1019: no workers were run; triage the original.
Reasons:
- Same person as an older contact (hs-1019); the original carries the triage.
Workers:
- enricher: SKIPPED — duplicate of contact hs-1019 (created 2026-11-03T09:30:00Z)
- qualifier: SKIPPED — duplicate of contact hs-1019 (created 2026-11-03T09:30:00Z)
- drafter: SKIPPED — duplicate of contact hs-1019 (created 2026-11-03T09:30:00Z)
Draft: not attempted
Cost: not measured live (recorded fake) · tokens in 0 / out 0 · blocked tool attempts: 0
```
