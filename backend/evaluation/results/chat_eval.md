# End-to-end chat evaluation

Cases: 26

## Automated issue counts


Automated checks do not prove semantic correctness. Inspect each answer below against the expected answer and PDF.

## Cases

### Q01 (exact_fact)

Question: What is the minimum password length required by the IT policy?

Expected: 12 characters

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, doc2_ecoboiler_x200_manual.pdf, 104 Memory Management - Partitioning.pdf, 103 Virtual Memory.pdf

Actual: The minimum password length required by the IT policy is 12 characters.

Source: [1] doc1_it_security_policy.pdf page 1

### Q02 (exact_fact)

Question: How often must employees change their password?

Expected: Every 90 days

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf

Actual: Employees must change their password every 90 days.  

Source: [1] doc1_it_security_policy.pdf page 1

### Q03 (exact_fact)

Question: How many of an employee's previous passwords are blocked from reuse?

Expected: The last 5 previous passwords

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 102 The Memory Hierarchy.pdf, 103 Virtual Memory.pdf, 104 Memory Management - Partitioning.pdf, 103 Virtual Memory.pdf

Actual: An employee's last 5 previous passwords are blocked from reuse.

Source: [1] doc1_it_security_policy.pdf page 1

### Q04 (exact_fact)

Question: After how many minutes of inactivity does a VPN session time out?

Expected: 30 minutes

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 103 Virtual Memory.pdf, 105 Memory Management - Paging.pdf, 102 The Memory Hierarchy.pdf, 104 Memory Management - Partitioning.pdf

Actual: A VPN session times out after **30 minutes** of inactivity.

Source: [1] doc1_it_security_policy.pdf page 1, Section 2. Remote Work and VPN Access.

### Q05 (exact_fact)

Question: What is the maximum number of days per week an employee can work remotely without special approval?

Expected: 3 days per week

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 104 Memory Management - Partitioning.pdf, doc3_basil_light_study.pdf, doc2_ecoboiler_x200_manual.pdf, 105 Memory Management - Paging.pdf

Actual: The maximum number of days per week an employee can work remotely without special approval is **3 days**.

This is stated in source [1] doc1_it_security_policy.pdf page 1 under the "Remote Work and VPN Access" section: "Employees may work remotely a maximum of 3 days per week unless approved otherwise by their manager."

**Source:** [1]

### Q06 (exact_fact)

Question: Within how many business days will a new hire be issued a laptop?

Expected: 5 business days

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 105 Memory Management - Paging.pdf, 103 Virtual Memory.pdf

Actual: A new hire will be issued a laptop within 5 business days of their start date.

Source: [1] doc1_it_security_policy.pdf page 1

### Q07 (paraphrase_semantic)

Question: How long does a departing employee have to return company equipment?

Expected: 7 days after their last working day

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 103 Virtual Memory.pdf, 102 The Memory Hierarchy.pdf, 105 Memory Management - Paging.pdf, 105 Memory Management - Paging.pdf

Actual: A departing employee must return all company equipment to the IT department within 7 days of their last working day.  

**Source:** [1] doc1_it_security_policy.pdf page 1, Section 3. Equipment Issuance and Return.

### Q08 (paraphrase_semantic)

Question: If my work laptop is stolen, how quickly am I required to notify the company?

Expected: Within 2 hours of discovery, report to it-security@meridianrobotics.com

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 103 Virtual Memory.pdf, 105 Memory Management - Paging.pdf, 105 Memory Management - Paging.pdf, 105 Memory Management - Paging.pdf

Actual: If your work laptop is stolen, you are required to notify the company within **2 hours of discovery**.

This requirement is specified in the **Security Incident Reporting** section of the IT & Security Policy (Source [1], doc1_it_security_policy.pdf page 1). The policy states that any suspected security incident — including lost devices — must be reported to it-security@meridianrobotics.com within 2 hours of discovery. Delayed reporting is treated as a policy violation regardless of the outcome.

**Citation:** [1] doc1_it_security_policy.pdf page 1

### Q09 (list_fact)

Question: What are the four data classification levels used by the company?

Expected: Public, Internal, Confidential, and Restricted

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 106 Memory Management - Segmentation.pdf, 101 Memory.pdf

Actual: The four data classification levels used by the company are: Public, Internal, Confidential, and Restricted.  

Source: [1] doc1_it_security_policy.pdf page 1

### Q10 (exact_fact)

Question: Can Restricted data be printed and taken off company premises?

Expected: No — restricted data may not be copied to personal devices, printed, or transmitted outside company premises under any circumstances

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 103 Virtual Memory.pdf, doc2_ecoboiler_x200_manual.pdf, 103 Virtual Memory.pdf, 102 The Memory Hierarchy.pdf

Actual: No, Restricted data may not be printed or taken off company premises. According to the policy in source [1] doc1_it_security_policy.pdf page 1, Restricted data — such as customer payment details and unreleased product designs — may not be copied to personal devices, printed, or transmitted outside company premises under any circumstances.

**Source:** [1] doc1_it_security_policy.pdf page 1

### Q11 (out_of_scope_trap)

Question: What does the company's IT policy say about annual leave entitlement?

Expected: NOT ANSWERABLE — the document does not mention annual leave at all.

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc1_it_security_policy.pdf, 105 Memory Management - Paging.pdf, 103 Virtual Memory.pdf, 104 Memory Management - Partitioning.pdf, 105 Memory Management - Paging.pdf

Actual: The company's IT policy does not mention anything about annual leave entitlement.  

Source: [1] doc1_it_security_policy.pdf — This document covers topics such as password policy, remote work, equipment issuance, security incident reporting, and data classification, but it does not include information on employee leave entitlements.  

Therefore, based on the provided context, annual leave entitlement is not specified.

### Q12 (table_lookup)

Question: What is the power rating of the EcoBoiler X200?

Expected: 3000 W

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, doc3_basil_light_study.pdf, 105 Memory Management - Paging.pdf, doc2_ecoboiler_x200_manual.pdf

Actual: The power rating of the EcoBoiler X200 is 3000 W.  
Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

### Q13 (table_lookup)

Question: What is the tank capacity of the EcoBoiler X200 in litres?

Expected: 50 litres

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, 104 Memory Management - Partitioning.pdf, doc3_basil_light_study.pdf, 105 Memory Management - Paging.pdf, doc2_ecoboiler_x200_manual.pdf

Actual: The tank capacity of the EcoBoiler X200 is 50 litres.  
Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

### Q14 (table_lookup)

Question: How much does the EcoBoiler X200 weigh when empty?

Expected: 18 kg

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, 105 Memory Management - Paging.pdf, 101 Memory.pdf, doc3_basil_light_study.pdf, ai_internship_requirements.pdf

Actual: The EcoBoiler X200 weighs 18 kg when empty.  

Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

### Q15 (table_lookup)

Question: What is the tank warranty period versus the parts warranty period?

Expected: 5 years on the tank, 2 years on parts

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, doc3_basil_light_study.pdf, 105 Memory Management - Paging.pdf, 104 Memory Management - Partitioning.pdf, doc2_ecoboiler_x200_manual.pdf

Actual: The tank warranty period is 5 years, and the parts warranty period is 2 years.  

This information is found in source [1], page 1 of the *EcoBoiler X200 Technical Manual and Installation Guide*.

### Q16 (table_lookup)

Question: What does error code E2 mean on the EcoBoiler X200, and what should I do?

Expected: E2 means overheat protection was triggered; power off immediately and allow to cool for 1 hour

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, doc2_ecoboiler_x200_manual.pdf, ai_internship_requirements.pdf, 103 Virtual Memory.pdf

Actual: Error code E2 on the EcoBoiler X200 means "Overheat protection triggered."  

You should power off the unit immediately and allow it to cool for one hour before attempting to restart it.  

**Source:** [2] doc2_ecoboiler_x200_manual.pdf page 2

### Q17 (exact_fact)

Question: How much clearance space is required around the EcoBoiler X200 during installation?

Expected: A minimum of 30 cm clearance on all sides

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, 105 Memory Management - Paging.pdf, 104 Memory Management - Partitioning.pdf, 105 Memory Management - Paging.pdf, 103 Virtual Memory.pdf

Actual: A minimum clearance of 30 cm must be maintained on all sides of the unit to allow for servicing and airflow.

Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

### Q18 (exact_fact)

Question: How often should the pressure relief valve be tested?

Expected: Every month (manually, by lifting the test lever)

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, doc2_ecoboiler_x200_manual.pdf, ai_internship_requirements.pdf, doc1_it_security_policy.pdf, 102 The Memory Hierarchy.pdf

Actual: The pressure relief valve should be manually tested every month by lifting the test lever and confirming that water discharges freely.  

**Source:** [1] doc2_ecoboiler_x200_manual.pdf page 2

### Q19 (out_of_scope_trap)

Question: Does the EcoBoiler X200 come with a money-back guarantee if I'm not satisfied?

Expected: NOT ANSWERABLE — the manual only states warranty terms (5 years tank / 2 years parts); it says nothing about a money-back or satisfaction guarantee.

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, 103 Virtual Memory.pdf, doc1_it_security_policy.pdf, ai_internship_requirements.pdf, 105 Memory Management - Paging.pdf

Actual: The provided document context does not mention any money-back guarantee for the EcoBoiler X200. Therefore, such a guarantee is not specified.  

Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

### Q20 (exact_fact)

Question: How many basil plants were used in total, and how were they divided?

Expected: 120 plants total, divided into 4 groups of 30 plants each

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc3_basil_light_study.pdf, 106 Memory Management - Segmentation.pdf, 105 Memory Management - Paging.pdf, 105 Memory Management - Paging.pdf, 104 Memory Management - Partitioning.pdf

Actual: A total of 120 basil plants were used in the study. They were divided into 4 groups of 30 plants each:

- Group A: 30 plants under full-spectrum LED lighting  
- Group B: 30 plants under red and blue wavelength LED lighting  
- Group C: 30 plants under standard fluorescent lighting  
- Group D: 30 plants as the control group grown under natural sunlight  

**Source:** [1] doc3_basil_light_study.pdf page 1

### Q21 (exact_fact)

Question: Which lighting group had the fastest germination time, and what was the average?

Expected: Group B (red/blue LED only), averaging 4.2 days

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc3_basil_light_study.pdf, 105 Memory Management - Paging.pdf, 104 Memory Management - Partitioning.pdf, ai_internship_requirements.pdf

Actual: The lighting group that had the fastest germination time was Group B (red and blue wavelength LED only). The average germination time for this group was 4.2 days.

Source: [1] doc3_basil_light_study.pdf page 1

### Q22 (exact_fact)

Question: How much more leaf mass did the full-spectrum LED group produce compared to the control group?

Expected: 34 percent more leaf mass by dry weight

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc3_basil_light_study.pdf, 104 Memory Management - Partitioning.pdf

Actual: The full-spectrum LED group produced 34 percent more leaf mass by dry weight compared to the control group.  

Source: [1] doc3_basil_light_study.pdf page 1

### Q23 (multi_hop)

Question: Which group performed worse than the control, and by how much?

Expected: Group C (standard fluorescent lighting), yielding 12 percent less leaf mass than the control

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc3_basil_light_study.pdf, 104 Memory Management - Partitioning.pdf, 105 Memory Management - Paging.pdf, doc2_ecoboiler_x200_manual.pdf, 105 Memory Management - Paging.pdf

Actual: Group C (standard fluorescent lighting) performed worse than the control group. It yielded 12 percent less leaf mass by dry weight compared to the control group. 

Source: [1] doc3_basil_light_study.pdf page 1

### Q24 (multi_hop)

Question: Based on the study, which light type should I use if I mainly care about getting seeds to sprout quickly rather than maximum leaf yield?

Expected: Red/blue LED lighting (Group B) — recommended for minimising germination time

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc3_basil_light_study.pdf, doc2_ecoboiler_x200_manual.pdf, 105 Memory Management - Paging.pdf

Actual: If you mainly care about getting seeds to sprout quickly rather than maximum leaf yield, you should use **red and blue wavelength LED lighting**.

This is because, according to the study (source [1]), Group B (red/blue LED) showed the fastest germination, averaging 4.2 days to sprout, compared to 6.1 days for the control group grown under natural sunlight. While this group had similar final leaf mass to the control, it outperformed others in germination speed, making it ideal for minimizing time to germination—such as in nursery propagation settings.

**Source:** [1] doc3_basil_light_study.pdf page 1

### Q25 (negative_fact)

Question: Did the basil study test how soil pH affects growth?

Expected: No — the study explicitly states it did not test soil pH or fertiliser type; these are noted as open questions for future research.

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc3_basil_light_study.pdf

Actual: No, the basil study did not test how soil pH affects growth. This is explicitly stated in the research summary: "This study did not test the effect of soil pH or fertiliser type, which remain open questions for future research."  

Source: [1] doc3_basil_light_study.pdf page 1

### Q26 (out_of_scope_trap)

Question: Compare the tank capacity of the EcoBoiler X200 to the password rotation period in the IT policy.

Expected: NOT ANSWERABLE / nonsensical cross-domain comparison — these are unrelated facts from unrelated documents (50 litres vs. 90 days) with no meaningful relationship.

Route: RAG; source hit: True; done: True; issues: none detected

Sources: doc2_ecoboiler_x200_manual.pdf, doc1_it_security_policy.pdf, doc3_basil_light_study.pdf, 105 Memory Management - Paging.pdf, doc2_ecoboiler_x200_manual.pdf

Actual: The tank capacity of the EcoBoiler X200 is 50 litres (as specified in source [1], page 1), while the password rotation period in the IT policy is every 90 days (as specified in source [2], page 1).

There is no direct comparison or relationship between the tank capacity (a physical measure of water storage) and the password rotation period (a security policy duration). These are unrelated attributes from different domains (appliance specifications vs. cybersecurity policy).

Therefore, a comparison in terms of value or significance is not meaningful or supported by the provided context.

**Answer:** The tank capacity of the EcoBoiler X200 (50 litres) and the password rotation period (every 90 days) are unrelated attributes from different domains and cannot be meaningfully compared.
