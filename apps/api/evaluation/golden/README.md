# Golden set

Ground truth. Every accuracy number the project reports is measured against
what is in this directory and nothing else.

## Files

`transcriptions.jsonl` — one line of handwriting per record:

```json
{"booklet_id":"...","page_no":1,"line_index":3,"text":"Deadlock occurs when four conditions hold.","question_number":"1(a)"}
```

Type **exactly what is written**, including the student's own spelling
mistakes. Correcting them measures the OCR against text that was never on the
page. Set `"illegible": true` where a human genuinely cannot read it either —
those lines are excluded from CER, because measuring a machine against
something no person could read says nothing about the machine.

`marks.jsonl` — one dual-marked answer per record:

```json
{"booklet_id":"...","question_number":"1(a)","max_marks":6,"marker_a":4,"marker_b":5}
```

Two markers, independently, without seeing each other's marks. Add
`"adjudicated": 4.5` where a third marker resolved a disagreement.

## Why two markers

One marker's marks are an opinion. Two allow disagreement to be measured,
which is the only way to answer the question that matters: not "is the system
accurate" but "does the system agree with a marker about as well as two
markers agree with each other". Human markers do not agree perfectly, and
holding a machine to a standard no human meets is the wrong bar.

## No identities

Records key on booklet UUID. Never an index number — this directory is
committed, shared and discussed.
