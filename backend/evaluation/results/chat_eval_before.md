# End-to-end chat evaluation

Cases: 26

## Automated issue counts

- expected_numbers_missing: 9
- expected_source_missing: 8
- false_refusal: 9
- incomplete_stream: 16
- sources_event_missing: 15
- stream_error: 16
- unexpected_route: 9

Automated checks do not prove semantic correctness. Inspect each answer below against the expected answer and PDF.

## Cases

### Q01 (exact_fact)

Question: What is the minimum password length required by the IT policy?

Expected: 12 characters

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The minimum password length required by the IT policy is 12 characters.

Source: [1] doc1_it_security_policy.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q02 (exact_fact)

Question: How often must employees change their password?

Expected: Every 90 days

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q03 (exact_fact)

Question: How many of an employee's previous passwords are blocked from reuse?

Expected: The last 5 previous passwords

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: An employee's last 5 previous passwords are blocked from reuse.

Source: [1] doc1_it_security_policy.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q04 (exact_fact)

Question: After how many minutes of inactivity does a VPN session time out?

Expected: 30 minutes

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: A VPN session times out after 30 minutes of inactivity.  

Source: [1] doc1_it_security_policy.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q05 (exact_fact)

Question: What is the maximum number of days per week an employee can work remotely without special approval?

Expected: 3 days per week

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing, expected_numbers_missing

Sources: none

Actual: The maximum number of days per week an employee can work remotely without special approval is three days.

Source: [1] doc1_it_security_policy.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q06 (exact_fact)

Question: Within how many business days will a new hire be issued a laptop?

Expected: 5 business days

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: A new hire will be issued a laptop within 5 business days of their start date.

Source: [1] doc1_it_security_policy.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q07 (paraphrase_semantic)

Question: How long does a departing employee have to return company equipment?

Expected: 7 days after their last working day

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q08 (paraphrase_semantic)

Question: If my work laptop is stolen, how quickly am I required to notify the company?

Expected: Within 2 hours of discovery, report to it-security@meridianrobotics.com

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q09 (list_fact)

Question: What are the four data classification levels used by the company?

Expected: Public, Internal, Confidential, and Restricted

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, false_refusal, sources_event_missing

Sources: none

Actual: The provided context does not mention or describe any data classification levels used by the company. Therefore, the four data classification levels cannot be determined from the given information.

Answer: Not specified in the context.

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q10 (exact_fact)

Question: Can Restricted data be printed and taken off company premises?

Expected: No — restricted data may not be copied to personal devices, printed, or transmitted outside company premises under any circumstances

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The provided context does not address whether restricted data can be printed and taken off company premises. Therefore, this information is not available in the given sources.

Answer: No relevant information is provided in the context to determine if restricted data can be printed and taken off company premises.

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q11 (out_of_scope_trap)

Question: What does the company's IT policy say about annual leave entitlement?

Expected: NOT ANSWERABLE — the document does not mention annual leave at all.

Route: CHAT; source hit: True; done: True; issues: none detected

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q12 (table_lookup)

Question: What is the power rating of the EcoBoiler X200?

Expected: 3000 W

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The power rating of the EcoBoiler X200 is 3000 W.  
Source: [1]

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q13 (table_lookup)

Question: What is the tank capacity of the EcoBoiler X200 in litres?

Expected: 50 litres

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The tank capacity of the EcoBoiler X200 is 50 litres.  
Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q14 (table_lookup)

Question: How much does the EcoBoiler X200 weigh when empty?

Expected: 18 kg

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q15 (table_lookup)

Question: What is the tank warranty period versus the parts warranty period?

Expected: 5 years on the tank, 2 years on parts

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The tank warranty period is 5 years, and the parts warranty period is 2 years.  

Source: [1] doc2_ecoboiler_x200_manual.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q16 (table_lookup)

Question: What does error code E2 mean on the EcoBoiler X200, and what should I do?

Expected: E2 means overheat protection was triggered; power off immediately and allow to cool for 1 hour

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q17 (exact_fact)

Question: How much clearance space is required around the EcoBoiler X200 during installation?

Expected: A minimum of 30 cm clearance on all sides

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q18 (exact_fact)

Question: How often should the pressure relief valve be tested?

Expected: Every month (manually, by lifting the test lever)

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The pressure relief valve should be manually tested every month.  

Source: [1] doc2_ecoboiler_x200_manual.pdf page 2

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q19 (out_of_scope_trap)

Question: Does the EcoBoiler X200 come with a money-back guarantee if I'm not satisfied?

Expected: NOT ANSWERABLE — the manual only states warranty terms (5 years tank / 2 years parts); it says nothing about a money-back or satisfaction guarantee.

Route: CHAT; source hit: True; done: True; issues: none detected

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q20 (exact_fact)

Question: How many basil plants were used in total, and how were they divided?

Expected: 120 plants total, divided into 4 groups of 30 plants each

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q21 (exact_fact)

Question: Which lighting group had the fastest germination time, and what was the average?

Expected: Group B (red/blue LED only), averaging 4.2 days

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The lighting group that had the fastest germination time was Group B (red and blue wavelength LED only). The average germination time was 4.2 days.  

Source: [1] doc3_basil_light_study.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q22 (exact_fact)

Question: How much more leaf mass did the full-spectrum LED group produce compared to the control group?

Expected: 34 percent more leaf mass by dry weight

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: The full-spectrum LED group (Group A) produced 34 percent more leaf mass by dry weight than the control group (Group D) by the end of the 8-week period.

Source: [1] doc3_basil_light_study.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q23 (multi_hop)

Question: Which group performed worse than the control, and by how much?

Expected: Group C (standard fluorescent lighting), yielding 12 percent less leaf mass than the control

Route: CHAT; source hit: False; done: True; issues: false_refusal, expected_source_missing, expected_numbers_missing, unexpected_route

Sources: none

Actual: I can't answer that from the uploaded or seeded PDFs in this chat. Upload a relevant PDF or enable Web Search Mode if you want me to use online information.

### Q24 (multi_hop)

Question: Based on the study, which light type should I use if I mainly care about getting seeds to sprout quickly rather than maximum leaf yield?

Expected: Red/blue LED lighting (Group B) — recommended for minimising germination time

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: If you mainly care about getting seeds to sprout quickly rather than maximum leaf yield, you should use **red and blue wavelength LED lighting**.

This is because Group B (red/blue LED) showed the fastest germination, averaging 4.2 days to sprout, compared to 6.1 days for the control group grown under natural sunlight. While this group had similar final leaf mass to the control, its germination speed was significantly faster, making it ideal for minimizing time to sprout.

**Source:** [1] doc3_basil_light_study.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q25 (negative_fact)

Question: Did the basil study test how soil pH affects growth?

Expected: No — the study explicitly states it did not test soil pH or fertiliser type; these are noted as open questions for future research.

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, sources_event_missing

Sources: none

Actual: No, the basil study did not test how soil pH affects growth. The provided context focuses solely on the effects of light spectrum on basil growth and does not mention soil pH or any related variables. 

Source: [1] doc3_basil_light_study.pdf page 1

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'

### Q26 (out_of_scope_trap)

Question: Compare the tank capacity of the EcoBoiler X200 to the password rotation period in the IT policy.

Expected: NOT ANSWERABLE / nonsensical cross-domain comparison — these are unrelated facts from unrelated documents (50 litres vs. 90 days) with no meaningful relationship.

Route: RAG; source hit: None; done: False; issues: stream_error, incomplete_stream, unexpected_route

Sources: none

Actual: The provided context does not contain information about the password rotation period in the IT policy. Therefore, a comparison between the tank capacity of the EcoBoiler X200 (50 litres) and the password rotation period cannot be made.

Source [1] (EcoBoiler X200 Technical Manual) provides the tank capacity of 50 litres.  
Source [2] (IT Security Policy) is referenced in the memory context but does not specify a password rotation period.

No evidence is available to support a comparison between these two metrics.

Answer: Cannot be determined from the provided sources.

Errors: verify_grounded_answer() got an unexpected keyword argument 'memory_context'
