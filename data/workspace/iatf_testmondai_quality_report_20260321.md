# IATF Testmondai Quality Audit

- Scanned Quiz CSV Files: 116
- Skipped Non-Quiz CSV Files: 29
- Total Quiz Rows: 2558
- Total Issues: 2742

## Issue Type Summary

- missing_rev: 2246
- mojibake_suspected: 231
- invalid_seikai: 89
- blank_explanation: 85
- blank_question: 78
- short_question: 10
- short_explanation: 3

## Worst Files

### db/record/6.1.2.1_additional_testmondai.csv
- Rows: 66
- Issues: 138
- Row 3 [blank_question] Question text is blank
- Row 3 [blank_explanation] Explanation is blank
- Row 3 [invalid_seikai] Invalid seikai: ""
- Row 5 [blank_question] Question text is blank
- Row 5 [blank_explanation] Explanation is blank

### db/record/additional_testmondai.csv
- Rows: 33
- Issues: 66
- Row 3 [blank_question] Question text is blank
- Row 3 [blank_explanation] Explanation is blank
- Row 3 [invalid_seikai] Invalid seikai: ""
- Row 5 [blank_question] Question text is blank
- Row 5 [blank_explanation] Explanation is blank

### db/record/chatGPT作成/kajyou_8.1.1.csv
- Rows: 30
- Issues: 46
- Row 2 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 2 [missing_rev] Revision is placeholder "-"
- Row 3 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 3 [missing_rev] Revision is placeholder "-"
- Row 4 [short_question] Question text is too short

### db/record/bing/kajyou_Bing 8.3.1.1 .csv
- Rows: 21
- Issues: 42
- Row 2 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 2 [missing_rev] Revision is placeholder "-"
- Row 3 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 3 [missing_rev] Revision is placeholder "-"
- Row 4 [mojibake_suspected] Text appears mojibake or wrongly encoded

### db/record/chatGPT作成/kajyou_8.4.2.4.1.csv
- Rows: 32
- Issues: 40
- Row 2 [missing_rev] Revision is placeholder "-"
- Row 3 [missing_rev] Revision is placeholder "-"
- Row 4 [missing_rev] Revision is placeholder "-"
- Row 5 [missing_rev] Revision is placeholder "-"
- Row 6 [missing_rev] Revision is placeholder "-"

### db/record/bing/kajyou_Bing 8.3.4.2 .csv
- Rows: 20
- Issues: 39
- Row 2 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 2 [missing_rev] Revision is placeholder "-"
- Row 3 [missing_rev] Revision is placeholder "-"
- Row 4 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 4 [missing_rev] Revision is placeholder "-"

### db/record/chatGPT作成/kajyou_8.6.6.csv
- Rows: 20
- Issues: 36
- Row 2 [missing_rev] Revision is placeholder "-"
- Row 3 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 3 [missing_rev] Revision is placeholder "-"
- Row 4 [mojibake_suspected] Text appears mojibake or wrongly encoded
- Row 4 [missing_rev] Revision is placeholder "-"

### db/record/chatGPT作成/kajyou_7.2.2.csv
- Rows: 35
- Issues: 35
- Row 2 [missing_rev] Revision is placeholder "-"
- Row 3 [missing_rev] Revision is placeholder "-"
- Row 4 [missing_rev] Revision is placeholder "-"
- Row 5 [missing_rev] Revision is placeholder "-"
- Row 6 [missing_rev] Revision is placeholder "-"

## Skipped Files

- db/record/attachedfile.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_7.1.5.3.1.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_7.2.1.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_7.2.3.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_8.3.5.1.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_8.3.5.2.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_8.3.6.1.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_8.4.2.1.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_8.4.2.2.csv: not_quiz_csv
- db/record/chatGPT作成/kajyou_8.4.2.4.csv: not_quiz_csv
