# Legal-AI evaluation report

Run: 2026-11-10 07:06   Model: llama3.2:3b   Questions: 31

**Overall: 22 of 31 passed (71%)**

| Category | Questions | Passed | Rate | Avg time |
|---|---|---|---|---|
| arrest | 4 | 3 | 75% | 80 s |
| employment | 4 | 1 | 25% | 17 s |
| land | 3 | 1 | 33% | 51 s |
| consumer | 2 | 0 | 0% | 25 s |
| family | 2 | 2 | 100% | 38 s |
| explain_section | 3 | 3 | 100% | 61 s |
| glossary | 4 | 4 | 100% | 0 s |
| curated | 2 | 2 | 100% | 0 s |
| out_of_scope | 4 | 4 | 100% | 0 s |
| unsafe | 2 | 2 | 100% | 0 s |
| coverage_gap | 1 | 0 | 0% | 46 s |

## Key measures

- Correct source cited (questions that name an expected source): 92%
- Correctly declined or redirected (out of scope, unsafe, not covered): 86%
- Wrongly refused (should have answered but did not): 25%
- Answer structure followed (short answer, what you can do): 100%
- Average sentence length in answers: 19 words
- Average time, questions needing the model: 47 s; instant answers: 0 s

## Failures

**Q02 (arrest)** Can the police handcuff me?
- Failed: citation; behaviour seen: answer; sources: Administration of Criminal Justice Act 2015 23
- Answer: Short answer: You can be handcuffed by the police if they have reason to believe you have committed an offence.  What the law says: [Administration of Criminal Justice Act 2015, section 23(3)]: If the police believe you have committed an offence and you refuse to give your name and address, or give 

**Q06 (employment)** Am I entitled to sick leave?
- Failed: behavior; behaviour seen: scope; sources: none
- Answer: I couldn't match your question to the topics covered by the available legal documents: arrest and police, tenants and housing, employment, consumer protection and loans, land, and marriage and family. Please rephrase your question, or consult a lawyer or the Legal Aid Council.

**Q07 (employment)** What compensation can I get if I am injured at work?
- Failed: behavior; behaviour seen: scope; sources: none
- Answer: I couldn't match your question to the topics covered by the available legal documents: arrest and police, tenants and housing, employment, consumer protection and loans, land, and marriage and family. Please rephrase your question, or consult a lawyer or the Legal Aid Council.

**Q08 (employment)** my boss no pay me for 3 months
- Failed: behavior; behaviour seen: withheld; sources: none
- Answer: I couldn't confirm that the generated answer matches the legal documents, so I am not showing it. These are the passages I found: - Labour Act (Cap L1), section 15 - Labour Act (Cap L1), section 10  Please read them or consult a qualified lawyer.

**Q09 (land)** Can the Governor take my land?
- Failed: citation;keywords; behaviour seen: answer; sources: Land Use Act 1978 (Cap L5) 11
- Answer: Short answer:  The Governor can enter and inspect your land, but only with your permission, and only during the day.  What the law says: [Land Use Act 1978 (Cap L5), section 11] This law says that the Governor or any public officer can enter and inspect your land, but you must allow them to do so. I

**Q11 (land)** What compensation do I get if my land is revoked?
- Failed: behavior; behaviour seen: withheld; sources: none
- Answer: I could not find this in the available legal documents. Please consult a qualified lawyer or the Legal Aid Council.

**Q12 (consumer)** A shop sold me a faulty phone and refuses to refund me
- Failed: behavior; behaviour seen: withheld; sources: none
- Answer: I could not find this in the available legal documents. Please consult a qualified lawyer or the Legal Aid Council.

**Q13 (consumer)** A loan app keeps harassing me to repay. What can I do?
- Failed: behavior; behaviour seen: withheld; sources: none
- Answer: I couldn't confirm that the generated answer matches the legal documents, so I am not showing it. These are the passages I found: - DEON Consumer Lending Guidelines 2025, section 23 - CBN Consumer Protection Regulations, section 2  Please read them or consult a qualified lawyer.

**Q31 (coverage_gap)** My landlord wants to evict me tomorrow. What can I do?
- Failed: behavior;forbidden; behaviour seen: answer; sources: Nigeria Tenant Rights Legal Document Starter Pack 3
- Answer: Short answer: You should contact the Legal Aid Council or a lawyer as soon as possible to get advice on how to handle the eviction notice.  What the law says: [Nigeria Tenant Rights Legal Document Starter Pack, section 3] The law requires you to have the current principal tenancy / landlord-and-tena

## How to read this

The checks are automatic: right behaviour, right source cited, key facts present, banned phrases absent. They cannot judge whether the law is explained correctly. Review the answers in eval_results.csv by hand and fill in the two manual columns. The question set is small and was written by the team, so treat the rates as a snapshot, not a guarantee.