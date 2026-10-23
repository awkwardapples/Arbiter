---
vars: [brief, corpus]
untrusted: []
schema: null
response: json
---
You rewrite an analyst brief that a deterministic template already wrote. Change only the headline and the wording of each why point. Keep the same number of why points, in the same order. Every number and every name you write must already appear in the allowed corpus.

Brief JSON:
{brief}

Allowed corpus:
{corpus}

Return only this JSON object, with no prose and no code fence:
{"headline": "<one sentence>", "why": ["<point>"]}
